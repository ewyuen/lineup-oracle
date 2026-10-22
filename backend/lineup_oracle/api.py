from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager
from typing import Literal

import fastapi
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from pydantic import Field
from pydantic import BaseModel

from .explain import explain
from .ingest import Feed, merge
from .optimizer import POSITIONS
from .picking import STATUS_OF_KIND, pick
from .pipeline import NewsRejected, Pipeline
from .state import State
from .telemetry import setup_telemetry

Mode = Literal["analyst", "fan"]
Language = Literal["en", "es", "zh-Hant"]
Kind = Literal["injury", "suspension", "doubt"]

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
    text: str | None = None


class PlayerOut(BaseModel):
    id: str
    name: str
    number: int
    position: str
    p_start: float
    explanation: str


class LineupOut(BaseModel):
    match_id: str
    club: str
    formation: str
    players: list[PlayerOut]
    alternatives: dict[str, list[PlayerOut]]
    llm_used: bool
    mode: Mode
    language: Language


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


def _render(pipeline: Pipeline, req: PredictRequest, xi, facts: list[dict]) -> LineupOut:
    """Explanations from the model (slow), or the templates if it is off or fails."""
    texts = pipeline.explain(facts, req.mode, req.language)
    trace.get_current_span().set_attributes({"formation": xi.formation, "llm_used": texts is not None, "mode": req.mode, "language": req.language})
    by_id = {f["id"]: f for f in facts}

    def out(player, p_start):
        fact = by_id[player.id]
        text = texts[player.id] if texts else explain(player, p_start, fact["starts"], fact["played"], fact["status"], req.mode)
        return PlayerOut(id=player.id, name=player.name, number=player.number, position=player.position, p_start=p_start, explanation=text)

    return LineupOut(
        match_id=req.match_id,
        club=req.club,
        formation=xi.formation,
        players=[out(p, s) for p, s in xi.players],
        alternatives={pos: [out(p, s) for p, s in xi.alternatives[pos]] for pos in POSITIONS},
        llm_used=texts is not None,
        mode=req.mode,
        language=req.language,
    )


def create_app(state: State | None = None, pipeline: Pipeline | None = None) -> FastAPI:
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

    @app.post("/predict_lineup", response_model=LineupOut)
    def predict_lineup(req: PredictRequest) -> LineupOut:
        with tracer.start_as_current_span("lineup.predict") as span:
            span.set_attributes({"match_id": req.match_id, "club": req.club})
            s: State = app.state.lineup
            feed: Feed = app.state.feed
            personal = s.availability.get((req.session_id, req.match_id, req.club))
            span.set_attribute("lineup.source", "stored" if personal is None else "personal")
            if personal is None:  # no news of its own: read the stored XI
                xi, facts = _http(feed.prediction, req.match_id, req.club)
            else:
                xi, facts = _http(pick, s, req.match_id, req.club, merge(feed.shared_availability(req.match_id, req.club), personal))
            return _render(app.state.pipeline, req, xi, facts)

    @app.post("/team_news", response_model=LineupOut)
    def team_news(req: TeamNewsRequest) -> LineupOut:
        with tracer.start_as_current_span("lineup.team_news") as span:
            span.set_attributes({"match_id": req.match_id, "club": req.club})
            s: State = app.state.lineup
            player_id, kind = req.player_id, req.kind
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
                try:
                    player_id, kind = app.state.pipeline.interpret(req.text, club)  # model call, before the lock
                except NewsRejected as err:
                    raise HTTPException(422, str(err)) from err
            span.set_attribute("news.kind", kind)
            with s.lock:  # one writer at a time, so two submits cannot overwrite each other
                _match(s, req.match_id)
                club = s.roster.clubs.get(req.club)
                if club is None or player_id not in {p.id for p in club.players}:
                    raise HTTPException(422, f"Player {player_id!r} does not belong to club {req.club!r}")
                feed: Feed = app.state.feed
                updated = {**s.availability.get((req.session_id, req.match_id, req.club), {}), player_id: (STATUS_OF_KIND[kind], feed.latest_seq)}
                xi, facts = _http(pick, s, req.match_id, req.club, merge(feed.shared_availability(req.match_id, req.club), updated))  # raises before any state changes
                s.availability[(req.session_id, req.match_id, req.club)] = updated
            return _render(app.state.pipeline, req, xi, facts)  # model call, after the lock

    @app.get("/news")
    def get_news(since: int | None = None, match_id: str | None = None, club: str | None = None, language: Language = "en") -> dict:
        items, latest, changed = app.state.feed.poll(since, match_id, club, language)
        return {"items": items, "latest_seq": latest, "changed": changed}

    @app.post("/news/restart")
    def restart_news() -> dict:
        return {"latest_seq": app.state.feed.restart()}  # one model call, up to the model timeout

    return app
