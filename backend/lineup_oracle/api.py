from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from typing import Literal

import fastapi
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from pydantic import Field
from pydantic import BaseModel

from .checks import failed_rules
from .explain import explain
from .ingest import Feed, merge
from .optimizer import POSITIONS
from .picking import LIFTS_SUSPENSION, eligible, overlay, pick, statuses
from .pipeline import NewsRejected, Pipeline
from .roster import Club
from .state import State
from .telemetry import setup_telemetry

Mode = Literal["analyst", "fan"]
Language = Literal["en", "es", "zh-Hant"]
Kind = Literal["injury", "suspension", "doubt"]

POST_INTERVAL = 10  # seconds a session must wait between posted lines

tracer = trace.get_tracer(__name__)  # no-op unless the Azure Monitor distro set a provider


class PredictRequest(BaseModel):
    match_id: str
    club: str
    mode: Mode = "analyst"
    language: Language = "en"
    session_id: str = Field("default", max_length=64)  # news is kept per session, so visitors do not see each other's


class TeamNewsRequest(PredictRequest):
    player_id: str | None = None
    kind: Kind | None = None
    text: str | None = Field(None, max_length=100)


class AlternativeRequest(PredictRequest):
    player_id: str
    included: bool


class PlayerOut(BaseModel):
    id: str
    name: str
    number: int
    position: str
    p_start: float
    status: Literal["available", "doubt", "out"]
    explanation: str


class NewsOut(BaseModel):
    outcome: Literal["applied", "posted"]
    club: str
    player_name: str | None = None
    kind: str | None = None


class CandidateOut(BaseModel):
    id: str
    name: str
    number: int
    position: str
    kind: Kind
    included: bool


class LineupOut(BaseModel):
    match_id: str
    club: str
    formation: str
    players: list[PlayerOut]
    alternatives: dict[str, list[PlayerOut]]
    candidates: list[CandidateOut]
    llm_used: bool
    mode: Mode
    language: Language
    news: NewsOut | None = None


def _match(state: State, match_id: str):
    if match_id not in state.metadata:
        raise HTTPException(404, f"Unknown match {match_id!r}")
    return state.metadata[match_id].payload


def _http(fn, *args):
    """Call fn, turning `pick`'s errors into the HTTP ones."""
    try:
        return fn(*args)
    except LookupError as err:
        raise HTTPException(404, str(err)) from err
    except ValueError as err:
        raise HTTPException(422, str(err)) from err


def _render(pipeline: Pipeline, req: PredictRequest, xi, facts: list[dict], candidates: list[dict], club: Club) -> LineupOut:
    """Explanations from the model (slow), or the templates if it is off or fails."""
    texts = pipeline.explain(facts, req.mode, req.language)
    span_attributes = {"formation": xi.formation, "llm_used": texts is not None, "mode": req.mode, "language": req.language}
    if texts:  # observe only: the response is the same whatever the check finds
        names = [p.name for p in club.players]
        failed = [failed_rules(texts[f["id"]], f, req.mode, names) for f in facts]
        span_attributes["explanation.grounded_ratio"] = sum(not rules for rules in failed) / len(failed)
        span_attributes["explanation.failed_rules"] = sorted({rule for rules in failed for rule in rules})
    trace.get_current_span().set_attributes(span_attributes)
    by_id = {f["id"]: f for f in facts}

    def out(player, p_start):
        fact = by_id[player.id]
        text = texts[player.id] if texts else explain(player, p_start, fact["starts"], fact["played"], fact["status"], req.mode)
        return PlayerOut(id=player.id, name=player.name, number=player.number, position=player.position, p_start=p_start, status=fact["status"], explanation=text)

    return LineupOut(
        match_id=req.match_id,
        club=req.club,
        formation=xi.formation,
        players=[out(p, s) for p, s in xi.players],
        alternatives={pos: [out(p, s) for p, s in xi.alternatives[pos]] for pos in POSITIONS},
        candidates=candidates,
        llm_used=texts is not None,
        mode=req.mode,
        language=req.language,
    )


def create_app(state: State | None = None, pipeline: Pipeline | None = None, clock=time.monotonic) -> FastAPI:
    setup_telemetry(os.environ)
    # Looked up on the module: the FastAPI instrumentation replaces fastapi.FastAPI when it is switched on.
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Only a running server ticks the feed; TestClient without a `with` block never enters this.
        stop = threading.Event()
        threading.Thread(target=app.state.feed.run, args=(stop,), name="news-feed", daemon=True).start()
        yield
        stop.set()

    app = fastapi.FastAPI(title="Lineup Oracle", lifespan=lifespan)
    app.state.lineup = state or State.load()
    app.state.pipeline = pipeline or Pipeline.from_env()
    app.state.feed = Feed(app.state.lineup, app.state.pipeline)
    # shortcut: the map grows with the number of sessions and is lost on restart; use a bounded or shared store if the API runs several replicas
    last_post: dict[str, float] = {}
    post_lock = threading.Lock()

    @app.exception_handler(RequestValidationError)
    def bad_request(_: Request, err: RequestValidationError) -> JSONResponse:
        # One text message, like every other error, instead of FastAPI's list of objects.
        message = "; ".join(f"{e['loc'][-1]}: {e['msg']}" for e in err.errors())
        return JSONResponse({"detail": message}, status_code=422)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/matches")
    def list_matches() -> list[dict]:
        return app.state.lineup.matches()

    @app.get("/matches/{match_id}/xi")
    def get_match_xi(match_id: str) -> dict:
        s: State = app.state.lineup
        meta = _match(s, match_id)
        clubs = []
        for side in ("home", "away"):
            players = [s.players[pid] for pid in meta[f"{side}_xi"]]
            clubs.append({
                "club": meta[f"{side}_club"],
                "formation": meta[f"{side}_formation"],
                "players": [{"id": p.id, "name": p.name, "number": p.number, "position": p.position} for p in players],
            })
        return {"match_id": match_id, "matchday": meta["matchday"], "clubs": clubs}

    def _current(req: PredictRequest, personal):
        """(xi, facts, merged availability) the request would use: the stored prediction without news of its own, else a fresh pick."""
        feed: Feed = app.state.feed
        merged = merge(feed.shared_availability(req.match_id, req.club), personal or {})
        if personal is None:
            xi, facts = _http(feed.prediction, req.match_id, req.club)
        else:
            xi, facts = _http(pick, app.state.lineup, req.match_id, req.club, statuses(merged))
        return xi, facts, merged

    def _view(req: PredictRequest):
        """(xi, facts, candidates) this session sees for the requested club: its own news merged over the shared, and its alternative selections."""
        s: State = app.state.lineup
        key = (req.session_id, req.match_id, req.club)
        xi, facts, merged = _current(req, s.availability.get(key))
        return _http(overlay, s, req.match_id, req.club, xi, facts, merged, s.selections.get(key, ()))


    @app.post("/predict_lineup", response_model=LineupOut)
    def predict_lineup(req: PredictRequest) -> LineupOut:
        with tracer.start_as_current_span("lineup.predict") as span:
            span.set_attributes({"match_id": req.match_id, "club": req.club})
            s: State = app.state.lineup
            feed: Feed = app.state.feed
            personal = s.availability.get((req.session_id, req.match_id, req.club))
            span.set_attribute("lineup.source", "stored" if personal is None else "personal")
            xi, facts, merged = _current(req, personal)
            xi, facts, candidates = _http(overlay, s, req.match_id, req.club, xi, facts, merged, s.selections.get((req.session_id, req.match_id, req.club), ()))
            return _render(app.state.pipeline, req, xi, facts, candidates, s.roster.clubs[req.club])

    @app.post("/team_news", response_model=LineupOut)
    def team_news(req: TeamNewsRequest) -> LineupOut:
        with tracer.start_as_current_span("lineup.team_news") as span:
            span.set_attributes({"match_id": req.match_id, "club": req.club})
            s: State = app.state.lineup
            player_id, kind, club_name = req.player_id, req.kind, req.club
            news: NewsOut | None = None
            if player_id is not None and kind is not None:
                span.set_attribute("news.input", "structured")
            else:
                if req.text is None:
                    raise HTTPException(422, "A player_id and a kind, or a text, are required")
                span.set_attribute("news.input", "text")
                meta = _match(s, req.match_id)
                club = s.roster.clubs.get(req.club)
                if club is None or req.club not in (meta["home_club"], meta["away_club"]):
                    raise HTTPException(422, f"Club {req.club!r} does not play in match {req.match_id!r}")
                opponent = s.roster.clubs[meta["away_club"] if req.club == meta["home_club"] else meta["home_club"]]
                try:
                    read = app.state.pipeline.read(req.text, club, s.roster.clubs, opponent)  # model call, before the lock
                except NewsRejected as err:
                    raise HTTPException(422, str(err)) from err
                span.set_attribute("news.outcome", read.outcome)
                if read.outcome == "posted":
                    with post_lock:  # check and update together, so two simultaneous posts cannot both pass
                        now = clock()
                        if now - last_post.get(req.session_id, -POST_INTERVAL) < POST_INTERVAL:
                            raise HTTPException(429, f"You can post one line every {POST_INTERVAL} seconds; try again shortly.")
                        last_post[req.session_id] = now
                        app.state.feed.post(req.match_id, req.club, read.texts)
                    xi, facts, candidates = _view(req)
                    out = _render(app.state.pipeline, req, xi, facts, candidates, club)
                    out.news = NewsOut(outcome="posted", club=req.club, player_name=read.player.name if read.player else None)
                    return out
                player_id, kind, club_name = read.player.id, read.kind, read.club
                news = NewsOut(outcome="applied", club=club_name, player_name=read.player.name, kind=kind)
            span.set_attribute("news.kind", kind)
            with s.lock:  # one writer at a time, so two submits cannot overwrite each other
                _match(s, req.match_id)
                club = s.roster.clubs.get(club_name)
                if club is None or player_id not in {p.id for p in club.players}:
                    raise HTTPException(422, f"Player {player_id!r} does not belong to club {club_name!r}")
                feed: Feed = app.state.feed
                key = (req.session_id, req.match_id, club_name)
                current = merge(feed.shared_availability(req.match_id, club_name), s.availability.get(key, {})).get(player_id, ("", 0))[0]
                if current == "suspension" and kind not in LIFTS_SUSPENSION:
                    name = next(p.name for p in club.players if p.id == player_id)
                    raise HTTPException(422, f"{name} is suspended; only a cleared status ends a suspension")
                updated = {**s.availability.get(key, {}), player_id: (kind, feed.latest_seq)}
                merged = merge(feed.shared_availability(req.match_id, club_name), updated)
                xi, facts = _http(pick, s, req.match_id, club_name, statuses(merged))  # raises before any state changes
                s.availability[key] = updated
                selections = s.selections.get(key, ())
            if club_name != req.club:  # the status landed on the other club; the response is still the requested club's XI
                xi, facts, candidates = _view(req)
            else:
                xi, facts, candidates = _http(overlay, s, req.match_id, club_name, xi, facts, merged, selections)
            out = _render(app.state.pipeline, req, xi, facts, candidates, s.roster.clubs[req.club])  # model call, after the lock
            out.news = news
            return out

    @app.post("/alternatives", response_model=LineupOut)
    def alternatives(req: AlternativeRequest) -> LineupOut:
        """Put a non-starting injured or doubtful player in the alternatives, or take them out. Changes no availability and no XI."""
        with tracer.start_as_current_span("lineup.alternatives") as span:
            span.set_attributes({"match_id": req.match_id, "club": req.club, "included": req.included})
            s: State = app.state.lineup
            meta = _match(s, req.match_id)
            club = s.roster.clubs.get(req.club)
            if club is None or req.club not in (meta["home_club"], meta["away_club"]):
                raise HTTPException(422, f"Club {req.club!r} does not play in match {req.match_id!r}")
            if req.player_id not in {p.id for p in club.players}:
                raise HTTPException(422, f"Player {req.player_id!r} does not belong to club {req.club!r}")
            key = (req.session_id, req.match_id, req.club)
            personal = s.availability.get(key)
            xi, facts, merged = _current(req, personal)  # no lock: this may run the optimizer
            valid = eligible(club, xi, merged)
            if req.included and req.player_id not in valid:
                raise HTTPException(422, f"Player {req.player_id!r} is a starter or has no injury or doubt news, so cannot be an alternative")
            with s.lock:  # copy on write, like availability; eligibility above is advisory, the read filter enforces it
                kept = [i for i in s.selections.get(key, ()) if i in valid and i != req.player_id]
                if req.included:
                    _, _, view = _http(overlay, s, req.match_id, req.club, xi, facts, merged, s.selections.get(key, ()))
                    if any(c["id"] == req.player_id and c["included"] for c in view):
                        kept = [i for i in s.selections.get(key, ()) if i in valid]  # already shown: nothing moves
                    else:
                        kept.append(req.player_id)
                if kept:
                    s.selections[key] = tuple(kept)
                else:
                    s.selections.pop(key, None)
                selections = s.selections.get(key, ())
            xi, facts, candidates = _http(overlay, s, req.match_id, req.club, xi, facts, merged, selections)
            return _render(app.state.pipeline, req, xi, facts, candidates, s.roster.clubs[req.club])

    @app.get("/news")
    def get_news(since: int | None = None, match_id: str | None = None, club: str | None = None, language: Language = "en") -> dict:
        items, latest, changed = app.state.feed.poll(since, match_id, club, language)
        return {"items": items, "latest_seq": latest, "changed": changed}

    @app.post("/news/restart")
    def restart_news() -> dict:
        return {"latest_seq": app.state.feed.restart()}  # one model call, up to the model timeout

    return app
