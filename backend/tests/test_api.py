from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from lineup_oracle.api import create_app
from lineup_oracle.events import generate_fixtures, generate_match_events, write_events
from lineup_oracle.explain import explain
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster, write_roster
from lineup_oracle.state import State

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)


@pytest.fixture
def state() -> State:
    return State(ROSTER, copy.deepcopy(EVENTS))


@pytest.fixture
def client(state: State) -> TestClient:
    return TestClient(create_app(state))


def _match(client, matchday=4):
    return next(m for m in client.get("/matches").json() if m["matchday"] == matchday)


def _predict(client, match, club=None, **extra):
    body = {"match_id": match["match_id"], "club": club or match["home_club"], **extra}
    return client.post("/predict_lineup", json=body)


def _news(client, match, player_id, kind, club=None):
    return client.post("/team_news", json={"match_id": match["match_id"], "club": club or match["home_club"], "player_id": player_id, "kind": kind})


# --- state and explanations -------------------------------------------


def test_state_generates_when_files_missing(tmp_path):
    state = State.load(tmp_path)
    assert len(state.matches()) == 30


def test_state_loads_files(tmp_path):
    write_roster(tmp_path / "roster.json", ROSTER)
    write_events(tmp_path / "events.jsonl", EVENTS)
    state = State.load(tmp_path)
    assert state.matches() == State(ROSTER, EVENTS).matches()


def test_matches_in_matchday_order():
    matches = State(ROSTER, EVENTS).matches()
    assert [m["matchday"] for m in matches] == sorted(m["matchday"] for m in matches)
    assert all(sum(m["matchday"] == d for m in matches) == 3 for d in range(1, 11))


def test_explanation_doubt_and_deterministic():
    player = ROSTER.clubs["Harbor City"].players[3]
    text = explain(player, 0.4, 2, 5, "doubt")
    assert "Fitness doubt" in text
    assert text == explain(player, 0.4, 2, 5, "doubt")
    assert "no recent matches" in explain(player, 0.4, 0, 0, "available")


# --- matches ----------------------------------------------------------


def test_list_matches_and_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    matches = client.get("/matches").json()
    assert len(matches) == 30
    assert {"match_id", "matchday", "home_club", "away_club"} <= matches[0].keys()


def test_get_match_xi(client):
    match = _match(client)
    body = client.get(f"/matches/{match['match_id']}/xi").json()
    assert [c["club"] for c in body["clubs"]] == [match["home_club"], match["away_club"]]
    assert all(len(c["players"]) == 11 for c in body["clubs"])


def test_get_match_xi_unknown(client):
    response = client.get("/matches/nope/xi")
    assert response.status_code == 404
    assert "nope" in response.json()["detail"]


# --- prediction -------------------------------------------------------


def test_prediction_shape(client):
    match = _match(client)
    body = _predict(client, match, mode="fan", language="es").json()
    assert len({p["id"] for p in body["players"]}) == 11
    assert all(0 <= p["p_start"] <= 1 and p["explanation"] for p in body["players"])
    club_ids = {p.id for p in ROSTER.clubs[match["home_club"]].players}
    assert {p["id"] for p in body["players"]} <= club_ids
    assert all(len(alts) <= 2 for alts in body["alternatives"].values())
    assert body["llm_used"] is False and body["mode"] == "fan" and body["language"] == "es"


def test_prediction_deterministic(client):
    match = _match(client)
    assert _predict(client, match).json() == _predict(client, match).json()


def test_own_xi_is_never_used(state):
    client = TestClient(create_app(state))
    match = _match(client)
    before = _predict(client, match).json()
    meta = state.metadata[match["match_id"]].payload
    meta["home_xi"] = [p.id for p in ROSTER.clubs[match["home_club"]].players[:11]]  # tamper with the match's own XI
    assert _predict(client, match).json() == before


def test_prediction_rejects_bad_requests(client):
    match = _match(client)
    other = next(c for c in CLUB_NAMES if c not in (match["home_club"], match["away_club"]))
    bad_club = _predict(client, match, club=other)
    assert bad_club.status_code == 422 and other in bad_club.json()["detail"]
    assert client.post("/predict_lineup", json={"match_id": "nope", "club": "Harbor City"}).status_code == 404
    assert _predict(client, match, mode="coach").status_code == 422
    assert _predict(client, match, language="fr").status_code == 422


# --- team news --------------------------------------------------------


def test_injury_removes_starter_and_stays_legal(client):
    match = _match(client)
    starter = _predict(client, match).json()["players"][3]["id"]
    body = _news(client, match, starter, "injury").json()
    assert starter not in {p["id"] for p in body["players"]}
    assert len(body["players"]) == 11
    assert _predict(client, match).json() == body  # state persists


def test_news_only_affects_its_match(client):
    first, second = _match(client, 4), _match(client, 5)
    club = second["home_club"]
    before = _predict(client, second, club=club).json()
    starter = _predict(client, first).json()["players"][3]["id"]
    _news(client, first, starter, "injury")
    assert _predict(client, second, club=club).json() == before


def test_bad_news_changes_nothing(client):
    match = _match(client)
    before = _predict(client, match).json()
    foreign = ROSTER.clubs[match["away_club"]].players[0].id
    response = _news(client, match, foreign, "injury")
    assert response.status_code == 422 and foreign in response.json()["detail"]
    assert client.post("/team_news", json={"match_id": match["match_id"], "club": match["home_club"], "player_id": foreign, "kind": "flu"}).status_code == 422
    assert _news(client, {"match_id": "nope"}, foreign, "injury", club="Harbor City").status_code == 404
    assert _predict(client, match).json() == before


def test_latest_news_wins(client, state):
    match = _match(client)
    starter = _predict(client, match).json()["players"][3]["id"]
    _news(client, match, starter, "doubt")
    out = _news(client, match, starter, "injury").json()
    assert starter not in {p["id"] for p in out["players"]}
    assert state.availability[(match["match_id"], match["home_club"])][starter] == "out"


def test_doubt_is_explained(client):
    match = _match(client)
    keepers = [p for p in ROSTER.clubs[match["home_club"]].players if p.position == "GK"]
    _news(client, match, keepers[1].id, "injury")
    body = _news(client, match, keepers[0].id, "doubt").json()  # the only fit keeper must still start
    shown = next(p for p in body["players"] if p["id"] == keepers[0].id)
    assert "Fitness doubt" in shown["explanation"]


def test_free_text_rejected(client):
    match = _match(client)
    before = _predict(client, match).json()
    response = client.post("/team_news", json={"match_id": match["match_id"], "club": match["home_club"], "text": "Hugo Ash is out"})
    assert response.status_code == 422 and "not available yet" in response.json()["detail"]
    assert _predict(client, match).json() == before
