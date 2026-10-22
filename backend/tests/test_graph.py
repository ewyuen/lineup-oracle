from __future__ import annotations

import copy
import itertools
import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from lineup_oracle import graph
from lineup_oracle.api import create_app
from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.history import HistoryFilters, history_from_memory, kickoff, retrieve_player_history
from lineup_oracle.pipeline import Pipeline
from lineup_oracle.roster import CLUB_NAMES, Player, generate_synthetic_roster
from lineup_oracle.state import State

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)
STATE = State(ROSTER, EVENTS)
PG_URL = os.environ.get("LINEUP_PG_URL")
needs_db = pytest.mark.skipif(not PG_URL, reason="LINEUP_PG_URL is not set")
UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:1/none"  # nothing listens on port 1


def client_with(monkeypatch, url):
    if url is None:
        monkeypatch.delenv("LINEUP_PG_URL", raising=False)
    else:
        monkeypatch.setenv("LINEUP_PG_URL", url)
    return TestClient(create_app(State(ROSTER, copy.deepcopy(EVENTS)), Pipeline()))


def history(client, **filters):
    return client.post("/player_history", json={"filters": {"player": "Pia Ash", **filters}})


# --- without a database (no container needed) -------------------------


def test_unset_url_means_memory(monkeypatch):
    client = client_with(monkeypatch, None)
    assert client.app.state.history_graph is None
    assert history(client).json()["events"]


def test_unreachable_database_gives_the_memory_result(monkeypatch):
    expected = history(client_with(monkeypatch, None), types=["shot", "started"]).json()
    client = client_with(monkeypatch, UNREACHABLE)
    assert client.app.state.history_graph is not None
    response = history(client, types=["shot", "started"])
    assert response.status_code == 200 and response.json() == expected


def test_a_hostile_player_name_matches_nobody(monkeypatch):
    response = history(client_with(monkeypatch, UNREACHABLE), player="}) DETACH DELETE")
    assert response.status_code == 422 and "Unknown player" in response.json()["detail"]


# --- against Postgres + AGE (docker compose up -d; python -m lineup_oracle.graph --load) ---


@pytest.fixture(scope="module")
def loaded():
    graph.load(PG_URL, STATE)


@needs_db
def test_seeded_counts(loaded):
    with graph.connect(PG_URL) as conn:
        n = graph.counts(conn)
    shots_tackles_news = sum(e.type in ("shot", "tackle", "team_news") for e in EVENTS)
    assert (n["Club"], n["Player"], n["Match"], n["Event"]) == (6, 120, 30, shots_tackles_news)
    assert n["PLAYS_FOR"] == 120 and n["HOME_IN"] == n["AWAY_IN"] == 30 and n["STARTED"] == 30 * 22
    assert n["HAD"] == n["IN"] == n["Event"]
    with graph.connect(PG_URL) as conn:
        passes = graph._cypher(conn, "MATCH (e:Event) WHERE e.type = 'pass' RETURN count(e)", None, ["n"])
    assert passes == [(0,)]


@needs_db
def test_loading_twice_gives_the_same_graph(loaded):
    first = graph.load(PG_URL, STATE)
    assert graph.load(PG_URL, STATE) == first


@needs_db
def test_a_failed_load_leaves_the_old_graph(loaded):
    with graph.connect(PG_URL) as conn:
        before = graph.counts(conn)
    events = copy.deepcopy(EVENTS)
    next(e for e in events if e.type == "team_news").payload["player_name"] = "Nobody Here"
    with pytest.raises(Exception, match="Nobody Here"):
        graph.load(PG_URL, State(ROSTER, events))
    with graph.connect(PG_URL) as conn:
        assert graph.counts(conn) == before


@needs_db
def test_hostile_values_are_data_and_leave_the_graph_intact(loaded):
    with graph.connect(PG_URL) as conn:
        before = graph.counts(conn)
    hostile = "}) DETACH DELETE p //"
    ghost = Player(hostile, "Harbor City", hostile, 1, "GK", "x")
    assert graph.fetch_history(PG_URL, ghost, HistoryFilters(hostile, match=hostile, types=("shot",))) == []
    with graph.connect(PG_URL) as conn:
        assert graph.counts(conn) == before


def _filter_sets():
    shot_times = [i.occurred_at for i in history_from_memory(STATE, STATE.players["harbor-city-20"], HistoryFilters("harbor-city-20", ("shot",)))]
    match = next(iter(STATE.metadata))
    yield {}
    for types in (("shot",), ("tackle",), ("team_news",), ("started",), ("shot", "started"), ("team_news", "tackle")):
        yield {"types": types}
    yield {"match": match}
    yield {"match": match, "types": ("shot", "tackle")}
    yield {"start": kickoff(3), "end": kickoff(6)}
    yield {"start": shot_times[2], "end": shot_times[4], "types": ("shot",)}  # both ends inclusive, to the millisecond
    yield {"start": kickoff(50)}


@needs_db
def test_graph_and_memory_agree(loaded):
    checked = 0
    for player in itertools.islice(STATE.players.values(), 0, None, 7):  # 18 players across all six clubs
        for filters in _filter_sets():
            asked = HistoryFilters(player.id, **filters)
            from_graph = retrieve_player_history(STATE, asked, lambda p, f: graph.fetch_history(PG_URL, p, f))
            from_memory = retrieve_player_history(STATE, asked)
            assert from_graph.items == from_memory.items, (player.id, filters)
            checked += bool(from_graph.items)
    assert checked > 100  # the comparison was not between empty lists


@needs_db
def test_every_player_agrees_with_no_filters(loaded):
    for player in STATE.players.values():
        asked = HistoryFilters(player.id)
        assert retrieve_player_history(STATE, asked, lambda p, f: graph.fetch_history(PG_URL, p, f)).items == retrieve_player_history(STATE, asked).items, player.id


@needs_db
def test_api_reads_the_graph_when_configured(monkeypatch, loaded):
    client = client_with(monkeypatch, PG_URL)
    calls = []
    real = client.app.state.history_graph
    client.app.state.history_graph = lambda p, f: calls.append(p.id) or real(p, f)
    body = history(client).json()
    assert calls == ["harbor-city-20"]
    assert body == history(client_with(monkeypatch, None)).json()
