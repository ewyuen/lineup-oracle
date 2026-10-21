from __future__ import annotations

import os
from typing import Literal

import fastapi
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field
from pydantic import BaseModel

from .explain import best_rating, explain
from .optimizer import POSITIONS, pick_xi
from .pipeline import NewsRejected, Pipeline
from .scoring import RECENT_MATCHES, p_start_scores, recent_xis
from .state import State
from .telemetry import setup_telemetry

Mode = Literal["analyst", "fan"]
Language = Literal["en", "es", "zh-Hant"]
Kind = Literal["injury", "suspension", "doubt"]
STATUS_OF_KIND = {"injury": "out", "suspension": "out", "doubt": "doubt"}


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


def _pick(state: State, req: PredictRequest, availability: dict[str, str]):
    """The XI and the facts about each listed player; fast, no model call."""
    meta = _match(state, req.match_id)
    if req.club not in (meta["home_club"], meta["away_club"]):
        raise HTTPException(422, f"Club {req.club!r} does not play in match {req.match_id!r}")
    club = state.roster.clubs[req.club]
    recent = recent_xis(state.metadata.values(), req.club, meta["matchday"])  # earlier matchdays only
    last = recent[-RECENT_MATCHES:]
    try:
        scores = p_start_scores(club, recent, availability)
        xi = pick_xi(club, scores)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
    listed = list(xi.players) + [ps for pos in POSITIONS for ps in xi.alternatives[pos]]
    facts = [
        {
            "id": p.id, "name": p.name, "position": p.position, "p_start": round(s, 2),
            "starts": sum(p.id in x for x in last), "played": len(last),
            "status": availability.get(p.id, "available"), "best_rating": best_rating(p),
        }
        for p, s in listed
    ]
    return xi, facts


def _render(pipeline: Pipeline, req: PredictRequest, xi, facts: list[dict]) -> LineupOut:
    """Explanations from the model (slow), or the templates if it is off or fails."""
    texts = pipeline.explain(facts, req.mode, req.language)
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
    app = fastapi.FastAPI(title="Lineup Oracle")
    app.state.lineup = state or State.load()
    app.state.pipeline = pipeline or Pipeline.from_env()

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
        s: State = app.state.lineup
        xi, facts = _pick(s, req, s.availability.get((req.session_id, req.match_id, req.club), {}))
        return _render(app.state.pipeline, req, xi, facts)

    @app.post("/team_news", response_model=LineupOut)
    def team_news(req: TeamNewsRequest) -> LineupOut:
        s: State = app.state.lineup
        player_id, kind = req.player_id, req.kind
        if player_id is None or kind is None:
            if req.text is None:
                raise HTTPException(422, "A player_id and a kind, or a text, are required")
            meta = _match(s, req.match_id)
            club = s.roster.clubs.get(req.club)
            if club is None or req.club not in (meta["home_club"], meta["away_club"]):
                raise HTTPException(422, f"Club {req.club!r} does not play in match {req.match_id!r}")
            try:
                player_id, kind = app.state.pipeline.interpret(req.text, club)  # model call, before the lock
            except NewsRejected as err:
                raise HTTPException(422, str(err)) from err
        with s.lock:  # one writer at a time, so two submits cannot overwrite each other
            _match(s, req.match_id)
            club = s.roster.clubs.get(req.club)
            if club is None or player_id not in {p.id for p in club.players}:
                raise HTTPException(422, f"Player {player_id!r} does not belong to club {req.club!r}")
            updated = {**s.availability.get((req.session_id, req.match_id, req.club), {}), player_id: STATUS_OF_KIND[kind]}
            xi, facts = _pick(s, req, updated)  # raises before any state changes
            s.availability[(req.session_id, req.match_id, req.club)] = updated
        return _render(app.state.pipeline, req, xi, facts)  # model call, after the lock

    return app
