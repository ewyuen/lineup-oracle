from __future__ import annotations

import copy
import threading
import time

import pytest
from fastapi.testclient import TestClient

from lineup_oracle.api import create_app
from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.explain import explain
from lineup_oracle.picking import STATUS_OF_KIND
from lineup_oracle.llm import DEFAULT_TIMEOUT, LlmSettings
from lineup_oracle.pipeline import UNAVAILABLE, NewsRejected, Pipeline
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster
from lineup_oracle.state import State

from fake_llm import FakeClient, explain_all

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)
CLUB = ROSTER.clubs["Harbor City"]
STAR = CLUB.players[8]
FACTS = [{"id": p.id, "name": p.name, "position": p.position, "p_start": 0.7, "starts": 3, "played": 5, "status": "available", "best_rating": "passing"} for p in CLUB.players[:3]]


def parser_says(**answer):
    return lambda payload: answer if "roster" in payload else explain_all(payload)


def pipeline_for(handler, timeout=5.0, delay=0.0):
    client = FakeClient(handler, delay)
    return Pipeline(client, timeout), client


# --- settings ---------------------------------------------------------


def test_settings_off_unless_endpoint_and_deployment():
    assert LlmSettings.from_env({}) is None
    assert LlmSettings.from_env({"LINEUP_LLM_ENDPOINT": "https://x"}) is None
    assert LlmSettings.from_env({"LINEUP_LLM_DEPLOYMENT": "gpt"}) is None


def test_settings_on_with_defaults_and_overrides():
    on = LlmSettings.from_env({"LINEUP_LLM_ENDPOINT": "https://x", "LINEUP_LLM_DEPLOYMENT": "gpt"})
    assert on == LlmSettings("https://x", "gpt", None, DEFAULT_TIMEOUT)
    more = LlmSettings.from_env({"LINEUP_LLM_ENDPOINT": "https://x", "LINEUP_LLM_DEPLOYMENT": "gpt", "LINEUP_LLM_API_KEY": "k", "LINEUP_LLM_TIMEOUT": "3"})
    assert more.api_key == "k" and more.timeout == 3.0


# --- parser -----------------------------------------------------------


def test_parser_accepts_a_valid_answer_and_ignores_extras():
    pipeline, client = pipeline_for(parser_says(club="Harbor City", player_id=STAR.id, kind="injury", xi=["a", "b"], note="x"))
    assert pipeline.interpret(f"{STAR.name} is out", CLUB) == (STAR.id, "injury")
    assert {p["id"] for p in client.calls[0]["roster"]} == {p.id for p in CLUB.players}


def test_parser_accepts_a_fenced_json_answer():
    pipeline, _ = pipeline_for(lambda p: f'```json\n{{"player_id": "{STAR.id}", "kind": "doubt"}}\n```')
    assert pipeline.interpret("x", CLUB) == (STAR.id, "doubt")


@pytest.mark.parametrize(
    "answer",
    [
        dict(club="Harbor City", player_id="northmere-3", kind="injury"),  # a player of another club
        dict(club="Harbor City", player_id="nobody-1", kind="injury"),  # an id that does not exist
        dict(club="Northmere", player_id=STAR.id, kind="injury"),  # news about the other club
        dict(club="Harbor City", player_id=None, kind="injury"),  # no player named
        dict(club="Harbor City", player_id=STAR.id, kind=None),  # no kind
        dict(club="Harbor City", player_id=STAR.id, kind="retired"),  # not a kind
    ],
)
def test_parser_rejects_untrustworthy_answers(answer):
    pipeline, _ = pipeline_for(parser_says(**answer))
    with pytest.raises(NewsRejected):
        pipeline.interpret("some text", CLUB)


def test_parser_rejects_malformed_output():
    pipeline, _ = pipeline_for(lambda p: "I think it is Hugo")
    with pytest.raises(NewsRejected):
        pipeline.interpret("some text", CLUB)


def test_parser_model_error_and_timeout_are_unavailable():
    failing, _ = pipeline_for(lambda p: RuntimeError("boom"))
    with pytest.raises(NewsRejected, match="unavailable"):
        failing.interpret("x", CLUB)
    slow, _ = pipeline_for(parser_says(player_id=STAR.id, kind="injury"), timeout=0.2, delay=1.0)
    with pytest.raises(NewsRejected, match="unavailable"):
        slow.interpret("x", CLUB)


def test_parser_off_is_unavailable():
    with pytest.raises(NewsRejected) as err:
        Pipeline().interpret("x", CLUB)
    assert str(err.value) == UNAVAILABLE


# --- free-text read ---------------------------------------------------

OPPONENT = ROSTER.clubs["Northmere"]
OTHER = ROSTER.clubs[next(c for c in CLUB_NAMES if c not in ("Harbor City", "Northmere"))]
TEXTS = {"en": "English line", "es": "Línea", "zh-Hant": "新聞"}


def read(answer, text="x"):
    pipeline, _ = pipeline_for(lambda p: answer)
    return pipeline.read(text, CLUB, ROSTER.clubs, OPPONENT)


def person(player, with_id=True):
    return {"name": player.name, "player_id": player.id if with_id else None}


def test_read_applies_an_injury_to_the_selected_club():
    got = read(dict(club="Harbor City", kind="injury", persons=[person(STAR)]))
    assert (got.outcome, got.club, got.player, got.kind) == ("applied", "Harbor City", STAR, "injury")


@pytest.mark.parametrize("kind", ["recovered", "cleared", "fit"])
def test_read_accepts_the_clearing_kinds(kind):
    assert read(dict(kind=kind, persons=[person(STAR)])).kind == kind
    assert STATUS_OF_KIND[kind] == "available"


def test_read_finds_a_player_by_full_name_without_an_id():
    assert read(dict(kind="doubt", persons=[person(STAR, with_id=False)])).player == STAR


def test_read_finds_an_opponent_player_and_applies_to_that_club():
    target = OPPONENT.players[2]
    got = read(dict(kind="injury", persons=[{"name": target.name.upper(), "player_id": None}]))
    assert (got.outcome, got.club, got.player) == ("applied", "Northmere", target)


def test_read_status_for_a_club_outside_the_match_is_rejected():
    outsider = OTHER.players[0]
    with pytest.raises(NewsRejected, match=OTHER.name):
        read(dict(kind="injury", persons=[person(outsider, with_id=False)]))


def test_read_player_of_any_club_without_a_status_is_posted():
    got = read(dict(persons=[person(OTHER.players[0], with_id=False)], translations=TEXTS))
    assert (got.outcome, got.player, got.texts) == ("posted", OTHER.players[0], TEXTS)


def test_read_two_players_unknown_person_and_outsider_are_rejected():
    with pytest.raises(NewsRejected, match="One player per line"):
        read(dict(kind="injury", persons=[person(STAR), person(CLUB.players[1])]))
    with pytest.raises(NewsRejected, match="Player not found: Nobody Known"):
        read(dict(kind="injury", persons=[{"name": "Nobody Known", "player_id": None}]))
    with pytest.raises(NewsRejected, match="Player not found: Sam Buyer"):
        read(dict(club="Harbor City", persons=[{"name": "Sam Buyer", "player_id": None}], translations=TEXTS))


def test_read_club_only_line_is_posted_even_with_a_status():
    got = read(dict(club="northmere", kind="injury", translations=TEXTS))
    assert got.outcome == "posted" and got.player is None and got.club == "Harbor City"


def test_read_no_person_and_no_known_club_is_rejected():
    for answer in (dict(), dict(club="Nowhere FC", translations=TEXTS), dict(kind="injury", translations=TEXTS)):
        with pytest.raises(NewsRejected, match="name a player or a team"):
            read(answer)


@pytest.mark.parametrize(
    "translations",
    [None, {"en": "a", "zh-Hant": "c"}, {**TEXTS, "es": "  "}, {**TEXTS, "en": "x" * 201}],
)
def test_read_post_needs_three_usable_texts(translations):
    with pytest.raises(NewsRejected):
        read(dict(club="Harbor City", translations=translations))


def test_read_post_accepts_exactly_the_cap_and_a_status_needs_no_translations():
    assert read(dict(club="Harbor City", translations={**TEXTS, "en": "x" * 200})).outcome == "posted"
    assert read(dict(kind="injury", persons=[person(STAR)])).outcome == "applied"


def test_read_model_off_and_unreadable_answers():
    with pytest.raises(NewsRejected) as err:
        Pipeline().read("x", CLUB, ROSTER.clubs, OPPONENT)
    assert str(err.value) == UNAVAILABLE
    with pytest.raises(NewsRejected, match="could not be read"):
        read("not json")
    with pytest.raises(NewsRejected, match="could not be read"):
        read(dict(persons="Hugo"))
    failing, _ = pipeline_for(lambda p: RuntimeError("boom"))
    with pytest.raises(NewsRejected, match="unavailable"):
        failing.read("x", CLUB, ROSTER.clubs, OPPONENT)


def test_interpret_is_unchanged_by_the_new_fields():
    pipeline, _ = pipeline_for(parser_says(club="Harbor City", player_id=STAR.id, kind="injury", persons=[person(STAR)], translations=TEXTS))
    assert pipeline.interpret("x", CLUB) == (STAR.id, "injury")
    cleared, _ = pipeline_for(parser_says(player_id=STAR.id, kind="fit"))
    assert cleared.interpret("x", CLUB) == (STAR.id, "fit")


# --- explainer --------------------------------------------------------


def test_explainer_accepts_a_full_answer():
    pipeline, client = pipeline_for(explain_all)
    texts = pipeline.explain(FACTS, "analyst", "es")
    assert set(texts) == {f["id"] for f in FACTS}
    assert client.calls[0]["language"] == "es" and client.calls[0]["players"] == FACTS


def _bad(payload):
    ids = [p["id"] for p in payload["players"]]
    return {
        "missing": {"explanations": [{"id": i, "text": "ok"} for i in ids[1:]]},
        "extra": {"explanations": [{"id": i, "text": "ok"} for i in ids + ["zzz"]]},
        "duplicate": {"explanations": [{"id": ids[0], "text": "ok"}] * len(ids)},
        "empty": {"explanations": [{"id": i, "text": " "} for i in ids]},
        "long": {"explanations": [{"id": i, "text": "x" * 201} for i in ids]},
    }


@pytest.mark.parametrize("case", ["missing", "extra", "duplicate", "empty", "long"])
def test_explainer_rejects_invalid_answers(case):
    pipeline, _ = pipeline_for(lambda payload: _bad(payload)[case])
    assert pipeline.explain(FACTS, "analyst", "en") is None


def test_explainer_fan_text_must_have_no_numbers():
    pipeline, _ = pipeline_for(lambda p: explain_all(p, "Starts 80% of games."))
    assert pipeline.explain(FACTS, "fan", "en") is None
    assert pipeline.explain(FACTS, "analyst", "en") is not None


def test_explainer_error_timeout_and_off_give_none():
    assert pipeline_for(lambda p: RuntimeError("boom"))[0].explain(FACTS, "fan", "en") is None
    assert pipeline_for(explain_all, timeout=0.2, delay=1.0)[0].explain(FACTS, "fan", "en") is None
    assert Pipeline().explain(FACTS, "fan", "en") is None


def test_explainer_cache_calls_the_model_once_per_input():
    pipeline, client = pipeline_for(explain_all)
    first = pipeline.explain(FACTS, "fan", "en")
    assert pipeline.explain(FACTS, "fan", "en") == first and len(client.calls) == 1
    pipeline.explain(FACTS, "fan", "es")
    pipeline.explain(FACTS[:2], "fan", "en")
    assert len(client.calls) == 3


# --- templates --------------------------------------------------------


def test_fan_template_has_no_p_start_and_analyst_is_unchanged():
    analyst = explain(STAR, 0.77, 4, 5, "available")
    assert analyst.startswith("Likely starter: P(start) 0.77, started 4 of the last 5, strong ")
    fan = explain(STAR, 0.77, 4, 5, "available", "fan")
    assert "P(start)" not in fan and fan.startswith("Likely starter: started 4 of the last 5")


# --- through the API --------------------------------------------------


def make_client(handler, delay=0.0):
    pipeline, client = pipeline_for(handler, delay=delay)
    app = create_app(State(ROSTER, copy.deepcopy(EVENTS)), pipeline)
    return TestClient(app), client


def a_match(client, matchday=4):
    return next(m for m in client.get("/matches").json() if m["matchday"] == matchday)


def body(match, **extra):
    return {"match_id": match["match_id"], "club": match["home_club"], **extra}


def ids(lineup):
    return [p["id"] for p in lineup["players"]]


def news_handler(club_name, player_id, kind="injury"):
    return lambda payload: {"club": club_name, "player_id": player_id, "kind": kind} if "roster" in payload else explain_all(payload)


def test_text_news_equals_button_news():
    probe, _ = make_client(explain_all)
    match = a_match(probe)
    starter = probe.post("/predict_lineup", json=body(match)).json()["players"][3]["id"]
    club = match["home_club"]
    texted, _ = make_client(news_handler(club, starter))
    by_text = texted.post("/team_news", json=body(match, text="out with an injury"))
    button, _ = make_client(explain_all)
    by_button = button.post("/team_news", json=body(match, player_id=starter, kind="injury"))
    assert by_text.status_code == 200 and starter not in ids(by_text.json())
    assert {**by_text.json(), "news": None} == by_button.json()
    assert by_text.json()["news"]["outcome"] == "applied"


@pytest.mark.parametrize(
    "answer",
    [
        lambda c, m: {"club": c, "player_id": "northmere-3", "kind": "injury"},
        lambda c, m: {"club": m["away_club"], "player_id": None, "kind": "injury"},
        lambda c, m: {"club": c, "player_id": None, "kind": None},
        lambda c, m: "not json",
    ],
)
def test_rejected_text_changes_nothing(answer):
    probe, _ = make_client(explain_all)
    match = a_match(probe)
    client, _ = make_client(lambda p: answer(match["home_club"], match) if "roster" in p else explain_all(p))
    before = client.post("/predict_lineup", json=body(match)).json()
    response = client.post("/team_news", json=body(match, text="something"))
    assert response.status_code == 422 and isinstance(response.json()["detail"], str)
    assert client.post("/predict_lineup", json=body(match)).json() == before


def test_text_for_a_club_not_in_the_match_is_rejected_before_the_model():
    client, fake = make_client(explain_all)
    match = a_match(client)
    other = next(c for c in CLUB_NAMES if c not in (match["home_club"], match["away_club"]))
    response = client.post("/team_news", json={"match_id": match["match_id"], "club": other, "text": "x"})
    assert response.status_code == 422 and fake.calls == []


def test_structured_news_still_works_when_the_model_fails():
    client, _ = make_client(lambda p: RuntimeError("down"))
    match = a_match(client)
    starter = client.post("/predict_lineup", json=body(match)).json()["players"][3]["id"]
    response = client.post("/team_news", json=body(match, player_id=starter, kind="injury"))
    assert response.status_code == 200 and response.json()["llm_used"] is False and starter not in ids(response.json())


def test_llm_explanations_language_and_flag():
    client, fake = make_client(lambda p: explain_all(p, "Titular habitual."))
    match = a_match(client)
    lineup = client.post("/predict_lineup", json=body(match, language="es")).json()
    assert lineup["llm_used"] is True and lineup["language"] == "es"
    shown = lineup["players"] + [a for alts in lineup["alternatives"].values() for a in alts]
    assert shown and all(p["explanation"] == "Titular habitual." for p in shown)
    assert fake.calls[0]["language"] == "es" and fake.calls[0]["mode"] == "analyst"


def test_same_xi_with_and_without_the_model():
    on, _ = make_client(explain_all)
    off = TestClient(create_app(State(ROSTER, copy.deepcopy(EVENTS)), Pipeline()))
    match = a_match(on)
    with_model = on.post("/predict_lineup", json=body(match)).json()
    without = off.post("/predict_lineup", json=body(match)).json()
    strip = lambda lineup: [(p["id"], p["p_start"]) for p in lineup["players"]] + [lineup["formation"]]  # noqa: E731
    assert strip(with_model) == strip(without)
    assert with_model["llm_used"] is True and without["llm_used"] is False


def test_invalid_model_output_falls_back_to_english_templates():
    client, _ = make_client(lambda p: {"explanations": []})
    match = a_match(client)
    lineup = client.post("/predict_lineup", json=body(match, mode="fan", language="es")).json()
    assert lineup["llm_used"] is False
    assert all("P(start)" not in p["explanation"] and p["explanation"].startswith(("Likely starter", "Fitness doubt")) for p in lineup["players"])


def test_repeat_prediction_calls_the_model_once_and_news_calls_it_again():
    client, fake = make_client(explain_all)
    match = a_match(client)
    first = client.post("/predict_lineup", json=body(match)).json()
    assert client.post("/predict_lineup", json=body(match)).json() == first and len(fake.calls) == 1
    client.post("/team_news", json=body(match, player_id=first["players"][3]["id"], kind="injury"))
    assert len(fake.calls) == 2


def test_slow_parse_does_not_block_other_sessions_news():
    probe, _ = make_client(explain_all)
    match = a_match(probe)
    starter = probe.post("/predict_lineup", json=body(match)).json()["players"][3]["id"]
    client, _ = make_client(news_handler(match["home_club"], starter), delay=lambda p: 1.5 if "roster" in p else 0)
    slow = threading.Thread(target=lambda: client.post("/team_news", json=body(match, text="slow", session_id="a")))
    slow.start()
    time.sleep(0.3)
    started = time.monotonic()
    other = client.post("/team_news", json=body(match, player_id=starter, kind="doubt", session_id="b"))
    assert other.status_code == 200 and time.monotonic() - started < 1.0
    slow.join()


def test_settings_read_a_dotenv_file_but_real_variables_win(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("LINEUP_LLM_ENDPOINT=https://e/\nLINEUP_LLM_DEPLOYMENT=from-file\n")
    monkeypatch.chdir(tmp_path)
    for name in ("LINEUP_LLM_ENDPOINT", "LINEUP_LLM_DEPLOYMENT", "LINEUP_LLM_API_KEY", "LINEUP_LLM_TIMEOUT"):
        monkeypatch.setenv(name, "x")  # so the undo removes whatever the .env load adds
        monkeypatch.delenv(name)
    monkeypatch.setenv("LINEUP_LLM_DEPLOYMENT", "from-env")
    settings = LlmSettings.from_env()
    assert settings.endpoint == "https://e/" and settings.deployment == "from-env"
