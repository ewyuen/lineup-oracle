import copy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from lineup_oracle.api import create_app
from lineup_oracle.pipeline import Pipeline
from lineup_oracle.state import State
from lineup_oracle.telemetry import CONNECTION_STRING, setup_telemetry

AZURE = "azure.monitor.opentelemetry.configure_azure_monitor"
AF = "agent_framework.observability.enable_instrumentation"


def test_skipped_without_connection_string():
    with patch(AZURE) as azure, patch(AF) as af:
        assert setup_telemetry({}) is False
        assert setup_telemetry({CONNECTION_STRING: ""}) is False
    azure.assert_not_called()
    af.assert_not_called()


def test_configured_once_with_connection_string():
    with patch(AZURE) as azure, patch(AF) as af:
        assert setup_telemetry({CONNECTION_STRING: "InstrumentationKey=00000000-0000-0000-0000-000000000000"}) is True
    azure.assert_called_once_with()
    af.assert_called_once_with()


def test_create_app_calls_setup_with_environment(monkeypatch):
    from lineup_oracle.api import create_app

    monkeypatch.delenv(CONNECTION_STRING, raising=False)
    with patch("lineup_oracle.api.setup_telemetry") as setup:
        create_app()
    setup.assert_called_once()


# --- lineup spans ------------------------------------------------------

from fake_llm import FakeClient, explain_all  # noqa: E402
from test_api import EVENTS, ROSTER  # noqa: E402


@pytest.fixture
def spans(monkeypatch) -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()  # private: the global provider can be set only once per process
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr("lineup_oracle.api.tracer", provider.get_tracer("test"))
    monkeypatch.setattr("lineup_oracle.ingest.tracer", provider.get_tracer("test"))
    return exporter


def _client(pipeline: Pipeline) -> TestClient:
    return TestClient(create_app(State(ROSTER, copy.deepcopy(EVENTS)), pipeline))


def _match(client):
    return next(m for m in client.get("/matches").json() if m["matchday"] == 4)


def _only(spans, name):
    found = [s for s in spans.get_finished_spans() if s.name == name]
    assert len(found) == 1
    return found[0]


def _player(client, match):
    return client.get(f"/matches/{match['match_id']}/xi").json()["clubs"][0]["players"][0]["id"]


def test_predict_span_stored_then_personal(spans):
    client = _client(Pipeline())
    match = _match(client)
    body = {"match_id": match["match_id"], "club": match["home_club"], "session_id": "sess-1"}
    assert client.post("/predict_lineup", json=body).status_code == 200
    span = _only(spans, "lineup.predict")
    assert dict(span.attributes) == {
        "match_id": match["match_id"], "club": match["home_club"], "lineup.source": "stored",
        "formation": span.attributes["formation"], "llm_used": False, "mode": "analyst", "language": "en",
    }
    spans.clear()
    news = {**body, "player_id": _player(client, match), "kind": "injury"}
    assert client.post("/team_news", json=news).status_code == 200
    spans.clear()
    client.post("/predict_lineup", json=body)
    assert _only(spans, "lineup.predict").attributes["lineup.source"] == "personal"


def test_team_news_structured_span(spans):
    client = _client(Pipeline())
    match = _match(client)
    body = {"match_id": match["match_id"], "club": match["home_club"], "player_id": _player(client, match), "kind": "doubt"}
    assert client.post("/team_news", json=body).status_code == 200
    span = _only(spans, "lineup.team_news")
    assert span.attributes["news.input"] == "structured"
    assert span.attributes["news.kind"] == "doubt"
    assert span.attributes["match_id"] == match["match_id"] and span.attributes["club"] == match["home_club"]
    assert span.status.status_code != StatusCode.ERROR


def test_team_news_text_span(spans):
    probe = _client(Pipeline())
    match = _match(probe)
    pid = _player(probe, match)

    def handler(payload):
        if "roster" in payload:
            return {"player_id": pid, "kind": "suspension", "club": None}
        return explain_all(payload)

    client = _client(Pipeline(FakeClient(handler)))
    body = {"match_id": match["match_id"], "club": match["home_club"], "text": "He is banned"}
    assert client.post("/team_news", json=body).status_code == 200
    span = _only(spans, "lineup.team_news")
    assert span.attributes["news.input"] == "text"
    assert span.attributes["news.kind"] == "suspension"
    assert span.attributes["llm_used"] is True


def test_rejected_news_marks_span_as_error(spans):
    client = _client(Pipeline(FakeClient(lambda payload: {"player_id": None, "kind": None, "club": None})))
    match = _match(client)
    body = {"match_id": match["match_id"], "club": match["home_club"], "text": "Nobody is hurt"}
    assert client.post("/team_news", json=body).status_code == 422
    span = _only(spans, "lineup.team_news")
    assert span.status.status_code == StatusCode.ERROR
    assert span.attributes["news.input"] == "text"
    assert span.attributes["club"] == match["home_club"]
    for missing in ("news.kind", "formation", "llm_used"):
        assert missing not in span.attributes


def test_model_failure_still_200_with_llm_used_false(spans):
    def handler(payload):
        return RuntimeError("model down")

    client = _client(Pipeline(FakeClient(handler)))
    match = _match(client)
    body = {"match_id": match["match_id"], "club": match["home_club"]}
    assert client.post("/predict_lineup", json=body).status_code == 200
    assert _only(spans, "lineup.predict").attributes["llm_used"] is False


def test_spans_carry_no_text_or_session_id(spans):
    client = _client(Pipeline(FakeClient(lambda payload: explain_all(payload, "SECRET-EXPLANATION"))))
    match = _match(client)
    body = {"match_id": match["match_id"], "club": match["home_club"], "session_id": "sess-secret"}
    reply = client.post("/predict_lineup", json=body)
    assert "SECRET-EXPLANATION" in reply.text
    for span in spans.get_finished_spans():
        for value in span.attributes.values():
            assert "SECRET-EXPLANATION" not in str(value) and "sess-secret" not in str(value)


def _facts_text(p: dict) -> str:
    return f"Started {p['starts']} of the last {p['played']}." + (" A doubt." if p["status"] == "doubt" else "")


def _explanations(wrong_first: bool):
    def handler(payload):
        texts = [_facts_text(p) for p in payload["players"]]
        if wrong_first:
            texts[0] = "Started 9 of the last 9."
        return {"explanations": [{"id": p["id"], "text": t} for p, t in zip(payload["players"], texts)]}

    return handler


def test_grounded_explanations_give_ratio_one_on_both_spans(spans):
    client = _client(Pipeline(FakeClient(_explanations(wrong_first=False))))
    match = _match(client)
    body = {"match_id": match["match_id"], "club": match["home_club"]}
    assert client.post("/predict_lineup", json=body).status_code == 200
    span = _only(spans, "lineup.predict")
    assert span.attributes["explanation.grounded_ratio"] == 1 and list(span.attributes["explanation.failed_rules"]) == []
    news = {**body, "player_id": _player(client, match), "kind": "doubt"}
    assert client.post("/team_news", json=news).status_code == 200
    assert _only(spans, "lineup.team_news").attributes["explanation.grounded_ratio"] == 1


def test_ungrounded_explanation_is_recorded_but_still_served(spans):
    client = _client(Pipeline(FakeClient(_explanations(wrong_first=True))))
    match = _match(client)
    body = {"match_id": match["match_id"], "club": match["home_club"]}
    reply = client.post("/predict_lineup", json=body)
    assert reply.status_code == 200
    span = _only(spans, "lineup.predict")
    assert span.attributes["explanation.grounded_ratio"] < 1
    assert list(span.attributes["explanation.failed_rules"]) == ["numbers"]
    assert any(p["explanation"] == "Started 9 of the last 9." for p in reply.json()["players"] + [a for alts in reply.json()["alternatives"].values() for a in alts])


def test_template_explanations_carry_no_grounding_attributes(spans):
    client = _client(Pipeline())
    match = _match(client)
    client.post("/predict_lineup", json={"match_id": match["match_id"], "club": match["home_club"]})
    assert not any(k.startswith("explanation.") for k in _only(spans, "lineup.predict").attributes)


# --- news.step span ----------------------------------------------------

from lineup_oracle.ingest import Feed  # noqa: E402
from test_ingest import FakePipeline  # noqa: E402


def _feed():
    state = State(ROSTER, copy.deepcopy(EVENTS))
    pipe = FakePipeline(state)
    return Feed(state, pipe), pipe, state


def test_correct_parse_gives_a_root_step_span(spans):
    feed, _, _ = _feed()
    item = feed.items[0]
    feed.step()
    span = _only(spans, "news.step")
    assert span.parent is None
    assert dict(span.attributes) == {"match_id": item.match_id, "club": item.club, "news.parse_correct": True, "news.applied": True}
    assert all(item.payload["text"] not in str(v) for v in span.attributes.values())


def test_wrong_kind_is_applied_but_not_correct(spans):
    feed, pipe, _ = _feed()
    item = feed.items[0]
    player_id, kind = pipe.answers[item.payload["text"]]
    pipe.override[item.payload["text"]] = (player_id, "doubt" if kind != "doubt" else "injury")
    feed.step()
    span = _only(spans, "news.step")
    assert span.attributes["news.parse_correct"] is False and span.attributes["news.applied"] is True


def test_player_outside_the_club_and_model_error_are_false_and_the_feed_goes_on(spans):
    feed, pipe, state = _feed()
    first, second = feed.items[0], feed.items[1]
    outsider = next(p.id for p in state.players.values() if p.club != first.club)
    pipe.override[first.payload["text"]] = (outsider, "injury")
    pipe.override[second.payload["text"]] = RuntimeError("model down")
    feed.step()
    feed.step()
    steps = [s for s in spans.get_finished_spans() if s.name == "news.step"]
    assert [(s.attributes["news.parse_correct"], s.attributes["news.applied"]) for s in steps] == [(False, False), (False, False)]
    feed.step()  # the third item still goes through
    assert [s.attributes["news.applied"] for s in spans.get_finished_spans() if s.name == "news.step"][-1] is True


def test_the_parser_gets_only_text_and_club_from_the_feed(spans):
    state = State(ROSTER, copy.deepcopy(EVENTS))
    answers = FakePipeline(state).answers

    def handler(payload):
        player_id, kind = answers[payload["text"]]
        return {"club": payload["club"], "player_id": player_id, "kind": kind}

    client = FakeClient(handler)
    Feed(state, Pipeline(client)).step()
    assert client.calls and all(set(call) == {"club", "roster", "text"} for call in client.calls)
    assert _only(spans, "news.step").attributes["news.parse_correct"] is True
