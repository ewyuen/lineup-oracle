from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.history import HistoryFilters, retrieve_player_history, team_news_players
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster
from lineup_oracle.state import NewsEntry, State

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)
NOW = datetime(2026, 10, 26, 12, 0, 30, 123456, tzinfo=timezone.utc)


def fresh() -> State:
    return State(ROSTER, EVENTS)


def a_news_item(state: State):
    """(event id, player id) of one seeded team-news item."""
    news_id, player_id = next(iter(team_news_players(state).items()))
    return news_id, player_id


def news_rows(state: State, player_id: str, session_id: str = "default", **kw):
    items = retrieve_player_history(state, HistoryFilters(player_id, ("team_news",), **kw), session_id=session_id).items
    return {i.id: i for i in items}


def test_reset_keeps_the_overlay():
    state = fresh()
    news_id, player_id = a_news_item(state)
    state.delivered[news_id] = NOW
    state.session_news[("s1", player_id, "injury")] = NewsEntry(NOW, "m", "c", "t")
    state.reset()
    assert state.delivered and state.session_news


def test_a_delivered_item_is_dated_at_its_delivery_and_an_undelivered_one_is_not():
    state = fresh()
    news_id, player_id = a_news_item(state)
    before = news_rows(state, player_id)[news_id].occurred_at
    state.delivered[news_id] = NOW
    rows = news_rows(state, player_id)
    assert rows[news_id].occurred_at == NOW.replace(microsecond=123000)  # to the millisecond, like every history time
    assert before < NOW
    others = {i: r for i, r in rows.items() if i != news_id}
    assert others == {i: r for i, r in news_rows(fresh(), player_id).items() if i != news_id}


def test_a_delivered_item_appears_once():
    state = fresh()
    news_id, player_id = a_news_item(state)
    state.delivered[news_id] = NOW
    ids = [i.id for i in retrieve_player_history(state, HistoryFilters(player_id)).items]
    assert ids.count(news_id) == 1


def test_the_time_range_uses_the_delivery_time():
    state = fresh()
    news_id, player_id = a_news_item(state)
    state.delivered[news_id] = NOW
    today = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    assert news_id in news_rows(state, player_id, start=today)
    assert news_id not in news_rows(state, player_id, end=today - timedelta(seconds=1))
    assert news_id not in news_rows(fresh(), player_id, start=today)  # not delivered: still at its synthetic time


def test_a_sessions_own_news_is_seen_only_by_that_session():
    state = fresh()
    _, player_id = a_news_item(state)
    club = state.players[player_id].club
    state.session_news[("s1", player_id, "injury")] = NewsEntry(NOW, "match-001", club, "Out hurt")
    mine = news_rows(state, player_id, "s1")[f"manual-{player_id}-injury"]
    assert (mine.occurred_at, mine.club, mine.payload["kind"], mine.payload["text"]) == (NOW.replace(microsecond=123000), club, "injury", "Out hurt")
    assert f"manual-{player_id}-injury" not in news_rows(state, player_id, "s2")
    assert f"manual-{player_id}-injury" not in news_rows(state, player_id)


def test_a_sessions_news_follows_the_type_and_match_filters():
    state = fresh()
    _, player_id = a_news_item(state)
    state.session_news[("s1", player_id, "doubt")] = NewsEntry(NOW, "match-001", "c", "t")
    ids = lambda **kw: [i.id for i in retrieve_player_history(state, HistoryFilters(player_id, **kw), session_id="s1").items]
    assert f"manual-{player_id}-doubt" in ids()
    assert f"manual-{player_id}-doubt" not in ids(types=("shot",))
    assert f"manual-{player_id}-doubt" not in ids(match="match-002")


# --- through the API ---------------------------------------------------

import pytest
from fastapi.testclient import TestClient

from lineup_oracle.api import create_app
from lineup_oracle.pipeline import Pipeline


@pytest.fixture
def client():
    return TestClient(create_app(fresh(), Pipeline(), now=lambda: NOW))


def _match(client):
    meta = next(iter(client.app.state.lineup.metadata.values())).payload
    return meta["match_id"] if "match_id" in meta else next(iter(client.app.state.lineup.metadata)), meta["home_club"]


def _history_ids(client, player_id, **extra):
    body = client.post("/player_history", json={"filters": {"player": player_id, "types": ["team_news"]}, **extra})
    assert body.status_code == 200, body.text
    return [e["id"] for e in body.json()["events"]]


def _submit(client, player, kind, session="s1", **extra):
    match_id, _ = _match(client)
    return client.post("/team_news", json={"match_id": match_id, "club": player.club, "player_id": player.id, "kind": kind, "session_id": session, **extra})


def _home_player(client):
    _, home = _match(client)
    return client.app.state.lineup.roster.clubs[home].players[0]


def test_a_button_press_enters_that_sessions_history_once(client):
    player = _home_player(client)
    assert _submit(client, player, "injury").status_code == 200
    assert _submit(client, player, "injury").status_code == 200
    mine = _history_ids(client, player.id, session_id="s1")
    assert mine.count(f"manual-{player.id}-injury") == 1
    assert f"manual-{player.id}-injury" not in _history_ids(client, player.id, session_id="s2")
    assert f"manual-{player.id}-injury" not in _history_ids(client, player.id)


def test_a_later_kind_is_a_new_entry(client):
    player = _home_player(client)
    _submit(client, player, "injury")
    _submit(client, player, "doubt")
    assert {f"manual-{player.id}-injury", f"manual-{player.id}-doubt"} <= set(_history_ids(client, player.id, session_id="s1"))


def test_a_rejected_submit_adds_nothing(client):
    player = _home_player(client)
    _submit(client, player, "suspension")
    assert _submit(client, player, "injury").status_code == 422
    assert f"manual-{player.id}-injury" not in _history_ids(client, player.id, session_id="s1")


def test_a_session_id_over_64_characters_is_rejected(client):
    player = _home_player(client)
    response = client.post("/player_history", json={"filters": {"player": player.id}, "session_id": "x" * 65})
    assert response.status_code == 422
