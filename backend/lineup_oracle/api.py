from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .explain import explain
from .optimizer import POSITIONS, pick_xi
from .scoring import RECENT_MATCHES, p_start_scores, recent_xis
from .state import State

Mode = Literal["analyst", "fan"]
Language = Literal["en", "es", "zh-Hant"]
Kind = Literal["injury", "suspension", "doubt"]
STATUS_OF_KIND = {"injury": "out", "suspension": "out", "doubt": "doubt"}
FREE_TEXT_MESSAGE = "Free-text team news parsing is not available yet; send a player id and a kind."


class PredictRequest(BaseModel):
    match_id: str
    club: str
    mode: Mode = "analyst"
    language: Language = "en"


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


def _lineup(state: State, req: PredictRequest, availability: dict[str, str]) -> LineupOut:
    meta = _match(state, req.match_id)
    if req.club not in (meta["home_club"], meta["away_club"]):
        raise HTTPException(422, f"Club {req.club!r} does not play in match {req.match_id!r}")
    club = state.roster.clubs[req.club]
    recent = recent_xis(state.events, req.club, meta["matchday"])  # earlier matchdays only
    last = recent[-RECENT_MATCHES:]
    try:
        scores = p_start_scores(club, recent, availability)
        xi = pick_xi(club, scores)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err

    def out(player, p_start):
        starts = sum(player.id in x for x in last)
        text = explain(player, p_start, starts, len(last), availability.get(player.id, "available"))
        return PlayerOut(id=player.id, name=player.name, number=player.number, position=player.position, p_start=p_start, explanation=text)

    return LineupOut(
        match_id=req.match_id,
        club=req.club,
        formation=xi.formation,
        players=[out(p, s) for p, s in xi.players],
        alternatives={pos: [out(p, s) for p, s in xi.alternatives[pos]] for pos in POSITIONS},
        llm_used=False,
        mode=req.mode,
        language=req.language,
    )


def create_app(state: State | None = None) -> FastAPI:
    app = FastAPI(title="Lineup Oracle")
    app.state.lineup = state or State.load()

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
        return _lineup(s, req, s.availability.get((req.match_id, req.club), {}))

    @app.post("/team_news", response_model=LineupOut)
    def team_news(req: TeamNewsRequest) -> LineupOut:
        s: State = app.state.lineup
        if req.text is not None and (req.player_id is None or req.kind is None):
            raise HTTPException(422, FREE_TEXT_MESSAGE)
        if req.player_id is None or req.kind is None:
            raise HTTPException(422, "A player_id and a kind are required")
        _match(s, req.match_id)
        club = s.roster.clubs.get(req.club)
        if club is None or req.player_id not in {p.id for p in club.players}:
            raise HTTPException(422, f"Player {req.player_id!r} does not belong to club {req.club!r}")
        updated = {**s.availability.get((req.match_id, req.club), {}), req.player_id: STATUS_OF_KIND[req.kind]}
        lineup = _lineup(s, req, updated)  # raises before any state changes
        s.availability[(req.match_id, req.club)] = updated
        return lineup

    return app
