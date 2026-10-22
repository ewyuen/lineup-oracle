from __future__ import annotations

import copy

from lineup_oracle import evals
from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.pipeline import Pipeline
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster
from lineup_oracle.state import State

from fake_llm import FakeClient

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)


def state() -> State:
    return State(ROSTER, copy.deepcopy(EVENTS))


def test_lineup_scores_are_deterministic_and_cover_48_club_matches():
    first = evals.lineup_scores(state())
    assert first == evals.lineup_scores(state())
    assert first["matches"] == 48 and 0 <= first["baseline"] <= 11 and 0 <= first["pipeline"] <= 11


def test_lineup_scores_use_only_earlier_matchdays(monkeypatch):
    seen = []
    real = evals.recent_xis

    def spy(events, club, matchday):
        xis = real(events, club, matchday)
        seen.append((matchday, len(xis)))
        return xis

    monkeypatch.setattr(evals, "recent_xis", spy)
    evals.lineup_scores(state())
    assert seen and all(count == matchday - 1 for matchday, count in seen)  # one XI per earlier matchday, never the match's own


def test_parser_eval_sends_only_text_and_club_and_scores_answers():
    s = state()
    news = [e for e in s.events if e.type == "team_news"]
    by_text = {e.payload["text"]: e for e in news}  # the same line can repeat across matches
    wrong = news[0].payload["text"]
    wrong_count = sum(e.payload["text"] == wrong for e in news)

    def answer(payload):
        e = by_text[payload["text"]]
        player = next(p for p in ROSTER.clubs[e.club].players if p.name == e.payload["player_name"])
        kind = "doubt" if payload["text"] == wrong else e.payload["kind"]  # one deliberate mistake
        return {"club": payload["club"], "player_id": player.id, "kind": kind}

    client = FakeClient(answer)
    result = evals.parser_accuracy(s, Pipeline(client))
    assert all(set(call) == {"club", "roster", "text"} for call in client.calls)  # no kind or player_name label
    assert result["events"] == len(news) and len(result["failures"]) == wrong_count
    assert result["accuracy"] == (len(news) - wrong_count) / len(news)


def test_parser_eval_is_skipped_without_a_model():
    assert "skipped" in evals.parser_accuracy(state(), Pipeline())
    assert evals.lineup_scores(state())["matches"] == 48


def test_scores_ignore_news_applied_by_the_feed():
    from lineup_oracle.ingest import Feed
    from test_ingest import FakePipeline

    s = state()
    before = evals.lineup_scores(s)
    feed = Feed(s, FakePipeline(s))
    for _ in range(len(feed.items)):
        feed.step()
    assert evals.lineup_scores(s) == before


def _grounded_text(p: dict) -> str:
    return f"Started {p['starts']} of the last {p['played']}." + (" A doubt." if p["status"] == "doubt" else "")


def test_template_explanations_are_all_grounded():
    for mode in ("analyst", "fan"):
        result = evals.template_grounding(state(), mode)
        assert result["grounded"] == 1.0 and result["explanations"] > 0 and not result["failures"]


def test_model_grounding_lists_the_ungrounded_explanation():
    def handler(payload):
        texts = [_grounded_text(p) for p in payload["players"]]
        texts[0] = "Started 9 of the last 9."  # one deliberate wrong count per club-match
        return {"explanations": [{"id": p["id"], "text": t} for p, t in zip(payload["players"], texts)]}

    client = FakeClient(handler)
    result = evals.model_grounding(state(), Pipeline(client), "analyst", "en")
    assert len(client.calls) == 48 and result["fallbacks"] == 0
    assert len(result["failures"]) == 48 and result["grounded"] < 1
    name, text, failed = result["failures"][0]
    assert text == "Started 9 of the last 9." and failed == ["numbers"] and name
    assert all(call["language"] == "en" and call["mode"] == "analyst" for call in client.calls)


def test_model_grounding_all_grounded_and_counts_fallbacks():
    good = FakeClient(lambda payload: {"explanations": [{"id": p["id"], "text": _grounded_text(p)} for p in payload["players"]]})
    assert evals.model_grounding(state(), Pipeline(good), "analyst", "en")["grounded"] == 1.0
    down = evals.model_grounding(state(), Pipeline(FakeClient(lambda payload: RuntimeError("down"))), "analyst", "en")
    assert down["fallbacks"] == 48 and down["explanations"] == 0 and not down["failures"]


def test_model_grounding_skipped_without_a_model_and_the_command_still_scores(monkeypatch, capsys):
    assert "skipped" in evals.model_grounding(state(), Pipeline(), "analyst", "en")
    monkeypatch.setattr(evals.State, "load", staticmethod(state))
    monkeypatch.setattr(evals.Pipeline, "from_env", classmethod(lambda cls: Pipeline()))
    monkeypatch.setattr("sys.argv", ["evals", "--explanations"])
    evals.main()
    out = capsys.readouterr().out
    assert "Lineup: pipeline" in out and "Template explanations (analyst): 100%" in out and "Model explanations: skipped" in out
