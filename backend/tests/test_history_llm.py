from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from lineup_oracle.api import create_app
from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.history import kickoff
from lineup_oracle.pipeline import HISTORY_UNAVAILABLE, HISTORY_UNREADABLE, Pipeline
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster
from lineup_oracle.state import State

from fake_llm import FakeClient

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)
QUESTION = "What happened to Pia Ash before matchday 3?"


def model(parse=None, answer=None):
    """Fake model: `parse` / `answer` are dicts, strings, exceptions or callables of the payload for the two steps."""

    def handler(payload):
        step = parse if "matchday_kickoffs" in payload else answer
        return step(payload) if callable(step) else step

    return handler


def app_with(handler):
    client = FakeClient(handler)
    return TestClient(create_app(State(ROSTER, copy.deepcopy(EVENTS)), Pipeline(client, 5.0))), client


def good_parse(payload):
    return {"player": "Pia Ash", "types": None, "from": None, "to": payload["matchday_kickoffs"]["3"], "match": None}


def cite_all(payload):
    ids = [e["id"] for e in payload["events"]]
    return {"answer": f"Pia Ash had {len(ids)} events.", "cited_event_ids": ids[:2]}


def ask(client, **body):
    return client.post("/player_history", json=body)


def test_question_is_parsed_and_answered_with_citations():
    client, fake = app_with(model(good_parse, cite_all))
    response = ask(client, question=QUESTION)
    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["player"] == "harbor-city-20" and body["filters"]["to"] == "2026-08-29T15:00:00.000Z"
    assert body["llm_used"] is True and body["answer"].startswith("Pia Ash had ")
    assert body["cited_event_ids"] == [e["id"] for e in body["events"]][:2]
    assert all(e["occurred_at"] <= body["filters"]["to"] for e in body["events"])
    parse_call = next(c for c in fake.calls if "matchday_kickoffs" in c)
    assert parse_call["question"] == QUESTION and parse_call["matchday_kickoffs"]["1"] == "2026-08-15T15:00:00.000Z"


def test_explicit_filters_make_no_parse_call_but_may_use_the_model_to_answer():
    client, fake = app_with(model(None, cite_all))
    body = ask(client, filters={"player": "harbor-city-20", "types": ["shot"]}).json()
    assert body["llm_used"] is True
    assert not any("matchday_kickoffs" in c for c in fake.calls)


def test_nothing_found_does_not_call_the_model_for_an_answer():
    client, fake = app_with(model(None, cite_all))
    body = ask(client, filters={"player": "Pia Ash", "from": "2030-01-01T00:00:00Z"}).json()
    assert body["llm_used"] is False and body["cited_event_ids"] == [] and fake.calls == []


@pytest.mark.parametrize(
    "parsed, message",
    [
        ({"player": "Pia Ash", "types": ["pass"]}, "event types that do not exist: pass"),
        ({"player": None}, "names no player"),
        ({"player": "Zed Zed"}, "Unknown player 'Zed Zed'"),
        ({"player": "Pia Ash", "from": "next tuesday"}, "time range could not be read"),
        ({"player": "Pia Ash", "from": "2026-09-01T00:00:00Z", "to": "2026-08-01T00:00:00Z"}, "ends before it starts"),
        ({"player": "Pia Ash", "match": "match-999"}, "Unknown match"),
        ("not json at all", HISTORY_UNREADABLE),
        (RuntimeError("model down"), HISTORY_UNAVAILABLE),
    ],
)
def test_invalid_parse_is_rejected_and_nothing_is_made_up(parsed, message):
    client, _ = app_with(model(parsed, cite_all))
    response = ask(client, question=QUESTION)
    assert response.status_code == 422 and message in response.json()["detail"]


@pytest.mark.parametrize(
    "answer",
    [
        lambda p: {"answer": "Invented.", "cited_event_ids": ["no-such-event"]},
        lambda p: {"answer": "Uncited.", "cited_event_ids": []},
        lambda p: {"answer": "  ", "cited_event_ids": [p["events"][0]["id"]]},
        "not json",
        RuntimeError("model down"),
    ],
)
def test_bad_answers_fall_back_to_the_template_and_never_fail_the_request(answer):
    client, _ = app_with(model(good_parse, answer))
    for body in ({"question": QUESTION}, {"filters": {"player": "Pia Ash"}}):
        response = ask(client, **body)
        assert response.status_code == 200
        out = response.json()
        assert out["llm_used"] is False and out["answer"].startswith("Pia Ash (Harbor City):")
        assert out["cited_event_ids"] == [e["id"] for e in out["events"]]


def test_the_model_sees_only_the_newest_hundred_events():
    rows = [{"id": f"e{n}"} for n in range(150)]
    client = FakeClient(model(None, lambda p: {"answer": "ok", "cited_event_ids": [p["events"][0]["id"]]}))
    answer = Pipeline(client, 5.0).answer_history("q", {}, rows)
    assert [r["id"] for r in client.calls[0]["events"]] == [f"e{n}" for n in range(50, 150)]
    assert answer == ("ok", ["e50"])


def test_kickoff_table_matches_the_rule():
    client, fake = app_with(model(good_parse, cite_all))
    ask(client, question=QUESTION)
    table = next(c for c in fake.calls if "matchday_kickoffs" in c)["matchday_kickoffs"]
    assert len(table) == 10 and table["2"] == "2026-08-22T15:00:00.000Z" and kickoff(10).isoformat().startswith("2026-10-17T15:00")
