from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from lineup_oracle.api import create_app
from lineup_oracle.pipeline import NewsRead, NewsRejected, Pipeline  # Pipeline() has no model, whatever LINEUP_LLM_* is set to
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
    return TestClient(create_app(state, Pipeline()))


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
    client = TestClient(create_app(state, Pipeline()))
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
    assert state.availability[("default", match["match_id"], match["home_club"])][starter] == ("injury", 0)


def test_doubt_is_explained(client):
    match = _match(client)
    keepers = [p for p in ROSTER.clubs[match["home_club"]].players if p.position == "GK"]
    _news(client, match, keepers[1].id, "injury")
    body = _news(client, match, keepers[0].id, "doubt").json()  # the only fit keeper must still start
    shown = next(p for p in body["players"] if p["id"] == keepers[0].id)
    assert "Fitness doubt" in shown["explanation"]


def test_free_text_rejected_when_model_off(client):
    match = _match(client)
    before = _predict(client, match).json()
    response = client.post("/team_news", json={"match_id": match["match_id"], "club": match["home_club"], "text": "Hugo Ash is out"})
    assert response.status_code == 422 and "unavailable" in response.json()["detail"]
    assert _predict(client, match).json() == before
    assert before["llm_used"] is False


# --- review fixes -----------------------------------------------------


def test_validation_errors_are_one_text_message(client):
    match = _match(client)
    body = _predict(client, match, mode="coach")
    assert body.status_code == 422
    detail = body.json()["detail"]
    assert isinstance(detail, str) and "mode" in detail


def test_stale_or_mismatched_events_fail_at_startup():
    stale = copy.deepcopy(EVENTS)
    next(e for e in stale if e.type == "match_metadata").payload.pop("matchday")
    with pytest.raises(ValueError, match="out of date"):
        State(ROSTER, stale)
    other = copy.deepcopy(EVENTS)
    next(e for e in other if e.type == "match_metadata").payload["home_xi"][0] = "ghost-1"
    with pytest.raises(ValueError, match="does not match the roster"):
        State(ROSTER, other)


def test_concurrent_news_is_not_lost(state):
    from concurrent.futures import ThreadPoolExecutor

    client = TestClient(create_app(state, Pipeline()))
    match = _match(client)
    club = ROSTER.clubs[match["home_club"]]
    victims = [p.id for p in club.players if p.position in ("DEF", "MID")][:8]
    with ThreadPoolExecutor(8) as pool:
        codes = list(pool.map(lambda pid: _news(client, match, pid, "doubt").status_code, victims))
    assert codes == [200] * 8
    assert set(state.availability[("default", match["match_id"], match["home_club"])]) == set(victims)


def test_sessions_do_not_see_each_others_news(client):
    match = _match(client)
    body = {"match_id": match["match_id"], "club": match["home_club"]}
    starter = client.post("/predict_lineup", json=body).json()["players"][3]["id"]
    client.post("/team_news", json={**body, "player_id": starter, "kind": "injury", "session_id": "judge-1"})
    mine = client.post("/predict_lineup", json={**body, "session_id": "judge-1"}).json()
    theirs = client.post("/predict_lineup", json={**body, "session_id": "judge-2"}).json()
    default = client.post("/predict_lineup", json=body).json()
    assert starter not in {p["id"] for p in mine["players"]}
    assert starter in {p["id"] for p in theirs["players"]} and theirs == default


# --- shared news feed --------------------------------------------------


@pytest.fixture
def feed_client(state):
    from test_ingest import FakePipeline
    from lineup_oracle.ingest import Feed

    app = create_app(state, Pipeline())
    app.state.feed = Feed(state, FakePipeline(state))
    return TestClient(app), app.state.feed


def _feed_match(feed):
    item = feed.items[0]
    return {"match_id": item.match_id, "home_club": item.club}


def _first_starter(client, match):
    return _predict(client, match).json()["players"][3]["id"]


def test_no_feed_thread_without_lifespan(state):
    import threading

    TestClient(create_app(state, Pipeline())).get("/health")
    assert "news-feed" not in {t.name for t in threading.enumerate()}


def test_feed_injury_shows_in_every_sessions_prediction(feed_client):
    client, feed = feed_client
    match = _feed_match(feed)
    player_id, kind = feed.pipeline.answers[feed.items[0].payload["text"]]
    feed.step()
    for session in ("a", "b"):
        after = _predict(client, match, session_id=session).json()
        assert len(after["players"]) == 11
        if kind != "doubt":
            assert player_id not in {p["id"] for p in after["players"]}


def test_sessions_without_news_share_one_pick(feed_client, monkeypatch):
    client, feed = feed_client
    match = _feed_match(feed)
    picks = []
    import lineup_oracle.ingest as ingest

    real = ingest.pick
    monkeypatch.setattr(ingest, "pick", lambda *a: picks.append(a) or real(*a))
    one = _predict(client, match, session_id="a").json()
    two = _predict(client, match, session_id="b").json()
    assert one == two and len(picks) == 1


def test_later_event_wins_between_personal_and_feed(feed_client):
    client, feed = feed_client
    match = _feed_match(feed)
    victim = feed.pipeline.answers[feed.items[0].payload["text"]][0]
    # personal doubt, then the feed says out (or doubt, if that is what the item says): the feed is later
    _news(client, match, victim, "doubt")
    key = ("default", match["match_id"], match["home_club"])
    feed.step()
    shared = feed._shared[(match["match_id"], match["home_club"])][victim]
    from lineup_oracle.ingest import merge

    assert merge(feed.shared_availability(match["match_id"], match["home_club"]), client.app.state.lineup.availability[key])[victim] == shared
    # feed out first, then a personal doubt: the personal one is later
    feed.restart()
    _news(client, match, victim, "doubt")
    merged = merge(feed.shared_availability(match["match_id"], match["home_club"]), client.app.state.lineup.availability[key])
    assert merged[victim][0] == "doubt"


def test_personal_news_does_not_reach_other_sessions_or_the_feed(feed_client):
    client, feed = feed_client
    match = _feed_match(feed)
    starter = _first_starter(client, match)
    client.post("/team_news", json={"match_id": match["match_id"], "club": match["home_club"], "player_id": starter, "kind": "injury", "session_id": "me"})
    other = _predict(client, match, session_id="other").json()
    assert starter in {p["id"] for p in other["players"]}
    assert feed.shared_availability(match["match_id"], match["home_club"]) == {}


def test_news_poll_and_restart(feed_client):
    client, feed = feed_client
    match = _feed_match(feed)
    first = client.get("/news").json()
    assert first == {"items": [], "latest_seq": 0, "changed": False}
    feed.step()
    mine = client.get("/news", params={"since": 0, "match_id": match["match_id"], "club": match["home_club"]}).json()
    assert mine["latest_seq"] == 1 and len(mine["items"]) == 1 and mine["changed"] is True
    other = client.get("/news", params={"since": 0, "match_id": "match-x", "club": "Nobody"}).json()
    assert len(other["items"]) == 1 and other["changed"] is False
    assert client.get("/news", params={"since": 1}).json()["items"] == []  # polling processes nothing
    assert len(feed.pipeline.calls) == 1
    restarted = client.post("/news/restart").json()
    assert restarted == {"latest_seq": 3}
    assert client.get("/news", params={"since": 1, "match_id": "match-x", "club": "Nobody"}).json()["changed"] is True


def test_not_applied_item_does_not_change_the_club(feed_client):
    client, feed = feed_client
    match = _feed_match(feed)
    from lineup_oracle.pipeline import NewsRejected

    feed.pipeline.override[feed.items[0].payload["text"]] = NewsRejected("no")
    feed.step()
    body = client.get("/news", params={"since": 0, "match_id": match["match_id"], "club": match["home_club"]}).json()
    assert body["items"][0]["applied"] is False and body["changed"] is False


def test_news_language_selects_text_and_rejects_unknown(feed_client):
    client, feed = feed_client
    item = feed.items[0]
    feed.step()
    texts = {"en": item.payload["text"], **item.payload["translations"]}
    for lang, text in texts.items():
        body = client.get("/news", params={"language": lang}).json()
        assert [e["text"] for e in body["items"]] == [text] and body["latest_seq"] == 1
    assert client.get("/news").json()["items"][0]["text"] == texts["en"]
    assert client.get("/news", params={"language": "fr"}).status_code == 422
    restarted = client.post("/news/restart").json()["latest_seq"]
    assert restarted == 3 and client.get("/news", params={"since": 1, "language": "es"}).json()["items"][0]["text"] == ""


def _write_events(tmp_path, mutate):
    import json
    from dataclasses import asdict

    events = copy.deepcopy(EVENTS)
    mutate(next(e for e in events if e.type == "team_news"))
    (tmp_path / "events.jsonl").write_text("\n".join(json.dumps(asdict(e)) for e in events), encoding="utf-8")
    return tmp_path


def test_state_accepts_current_format_events(tmp_path):
    State.load(_write_events(tmp_path, lambda e: None))


@pytest.mark.parametrize("break_it", [
    lambda e: e.payload.pop("translations"),
    lambda e: e.payload["translations"].pop("es"),
    lambda e: e.payload["translations"].update({"zh-Hant": ""}),
    lambda e: e.payload.update({"text": ""}),
])
def test_state_rejects_stale_team_news(tmp_path, break_it):
    with pytest.raises(ValueError, match="regenerate"):
        State.load(_write_events(tmp_path, break_it))


# --- free-text news outcomes ------------------------------------------


class ReadPipeline(Pipeline):
    """No model: `read` returns what `result` says (a NewsRead, or an Exception to raise)."""

    def __init__(self, state: State) -> None:
        super().__init__()
        self.state, self.result = state, None

    @property
    def enabled(self) -> bool:
        return True

    def read(self, text, club, clubs, opponent):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


TEXTS = {"en": "English", "es": "Español", "zh-Hant": "中文"}


class Clock:
    now = 100.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def text_client(state):
    pipeline, clock = ReadPipeline(state), Clock()
    client = TestClient(create_app(state, pipeline, clock))
    match = _match(client)
    return client, pipeline, clock, match


def _text(client, match, text="x", club=None, **extra):
    return client.post("/team_news", json={"match_id": match["match_id"], "club": club or match["home_club"], "text": text, **extra})


def _applied(state, match, club, kind, index=3):
    player = state.roster.clubs[club].players[index]
    return NewsRead("applied", club, player, kind)


def _log(client):
    return client.get("/news", params={"since": 0}).json()["items"]


def test_text_length_limit(text_client):
    client, pipeline, _, match = text_client
    pipeline.result = NewsRead("posted", match["home_club"], None, None, TEXTS)
    assert _text(client, match, "x" * 100).status_code == 200
    long = _text(client, match, "x" * 101, session_id="other")
    assert long.status_code == 422 and len(_log(client)) == 1


def test_applied_text_returns_news_and_is_private_to_the_session(text_client, state):
    client, pipeline, _, match = text_client
    club = match["home_club"]
    read = _applied(state, match, club, "injury", index=0)
    pipeline.result = read
    before = _predict(client, match, session_id="me").json()
    victim = before["players"][0]["id"]
    pipeline.result = NewsRead("applied", club, next(p for p in state.roster.clubs[club].players if p.id == victim), "injury")
    got = _text(client, match, session_id="me").json()
    assert victim not in {p["id"] for p in got["players"]}
    assert got["news"] == {"outcome": "applied", "club": club, "player_name": pipeline.result.player.name, "kind": "injury"}
    assert victim in {p["id"] for p in _predict(client, match, session_id="other").json()["players"]}
    assert _log(client) == []


def test_status_for_the_other_club_lands_there_and_returns_the_requested_lineup(text_client, state):
    client, pipeline, _, match = text_client
    home, away = match["home_club"], match["away_club"]
    victim = _predict(client, match, club=away, session_id="me").json()["players"][0]["id"]
    pipeline.result = NewsRead("applied", away, next(p for p in state.roster.clubs[away].players if p.id == victim), "injury")
    got = _text(client, match, club=home, session_id="me").json()
    assert got["club"] == home and got["news"]["club"] == away
    assert got["players"] == _predict(client, match, club=home, session_id="me").json()["players"]
    assert victim not in {p["id"] for p in _predict(client, match, club=away, session_id="me").json()["players"]}


def test_recovery_overrides_the_feed_out_for_one_session_only(text_client, state):
    client, pipeline, _, match = text_client
    club, key = match["home_club"], (match["match_id"], match["home_club"])
    feed = client.app.state.feed
    victim = _predict(client, match).json()["players"][0]["id"]
    with feed.lock:
        feed._seq += 1
        feed._shared[key] = {victim: ("injury", feed._seq)}
        feed._predictions.pop(key, None)
    assert victim not in {p["id"] for p in _predict(client, match, session_id="b").json()["players"]}
    player = next(p for p in state.roster.clubs[club].players if p.id == victim)
    pipeline.result = NewsRead("applied", club, player, "recovered")
    got = _text(client, match, session_id="a").json()
    assert victim in {p["id"] for p in got["players"]}
    assert victim not in {p["id"] for p in _predict(client, match, session_id="b").json()["players"]}


def test_posted_text_returns_the_unchanged_lineup_and_reaches_other_pollers(text_client):
    client, pipeline, _, match = text_client
    before = _predict(client, match, session_id="me").json()
    pipeline.result = NewsRead("posted", match["home_club"], None, None, TEXTS)
    got = _text(client, match, session_id="me").json()
    assert got["news"] == {"outcome": "posted", "club": match["home_club"], "player_name": None, "kind": None}
    assert {**got, "news": None} == before
    for lang, text in TEXTS.items():
        body = client.get("/news", params={"since": 0, "language": lang, "match_id": match["match_id"], "club": match["home_club"]}).json()
        assert [(e["kind"], e["text"]) for e in body["items"]] == [("info", text)] and body["changed"] is False


def test_rejected_text_changes_nothing(text_client):
    client, pipeline, _, match = text_client
    before = _predict(client, match).json()
    pipeline.result = NewsRejected("Player not found: Sam Buyer.")
    response = _text(client, match)
    assert response.status_code == 422 and response.json()["detail"].startswith("Player not found")
    assert _predict(client, match).json() == before and _log(client) == []


def test_second_post_is_limited_per_session(text_client):
    client, pipeline, clock, match = text_client
    pipeline.result = NewsRead("posted", match["home_club"], None, None, TEXTS)
    assert _text(client, match, session_id="a").status_code == 200
    clock.now += 3
    limited = _text(client, match, session_id="a")
    assert limited.status_code == 429 and len(_log(client)) == 1  # a 429 leaves the log unchanged
    assert _text(client, match, session_id="b").status_code == 200  # another session is not limited
    clock.now += 8  # 11 s after a's first post
    assert _text(client, match, session_id="a").status_code == 200 and len(_log(client)) == 3


def test_status_lines_and_rejections_do_not_count_toward_the_post_limit(text_client, state):
    client, pipeline, _, match = text_client
    pipeline.result = NewsRead("posted", match["home_club"], None, None, TEXTS)
    assert _text(client, match, session_id="a").status_code == 200
    pipeline.result = _applied(state, match, match["home_club"], "doubt")
    assert _text(client, match, session_id="a").status_code == 200
    pipeline.result = NewsRejected("no")
    assert _text(client, match, session_id="a").status_code == 422
    pipeline.result = NewsRead("posted", match["home_club"], None, None, TEXTS)
    assert _text(client, match, session_id="a").status_code == 429


def test_structured_path_has_no_news_object(client):
    match = _match(client)
    starter = _predict(client, match).json()["players"][3]["id"]
    assert _news(client, match, starter, "injury").json()["news"] is None


def test_only_a_cleared_text_lifts_a_suspension(text_client, state):
    client, pipeline, _, match = text_client
    club = match["home_club"]
    victim = _predict(client, match).json()["players"][0]
    player = next(p for p in state.roster.clubs[club].players if p.id == victim["id"])
    assert client.post("/team_news", json={"match_id": match["match_id"], "club": club, "player_id": player.id, "kind": "suspension", "session_id": "a"}).status_code == 200
    for kind in ("recovered", "fit", "doubt", "injury"):
        pipeline.result = NewsRead("applied", club, player, kind)
        got = _text(client, match, session_id="a")
        assert got.status_code == 422 and player.name in got.json()["detail"], kind
    assert victim["id"] not in {p["id"] for p in _predict(client, match, session_id="a").json()["players"]}
    pipeline.result = NewsRead("applied", club, player, "cleared")
    assert _text(client, match, session_id="a").status_code == 200
    assert victim["id"] in {p["id"] for p in _predict(client, match, session_id="a").json()["players"]}


# --- player history -----------------------------------------------------


def test_history_by_filters(client):
    body = client.post("/player_history", json={"filters": {"player": "harbor-city-20"}}).json()
    assert body["filters"]["player"] == "harbor-city-20" and "types" not in body["filters"]
    assert body["events"] and {e["type"] for e in body["events"]} == {"team_news"}
    times = [e["occurred_at"] for e in body["events"]]
    assert times == sorted(times)
    assert body["llm_used"] is False
    assert body["answer"].startswith("Pia Ash (Harbor City):")
    assert body["cited_event_ids"] == [e["id"] for e in body["events"]]


def test_history_time_range_and_name(client):
    everything = client.post("/player_history", json={"filters": {"player": "Pia Ash"}}).json()
    cut = everything["events"][1]["occurred_at"]
    after = client.post("/player_history", json={"filters": {"player": "Pia Ash", "from": cut}}).json()
    assert [e["id"] for e in after["events"]] == [e["id"] for e in everything["events"][1:]]
    assert after["filters"]["from"] == cut


def test_history_nothing_found(client):
    body = client.post("/player_history", json={"filters": {"player": "Pia Ash", "from": "2030-01-01T00:00:00Z"}}).json()
    assert body["events"] == [] and body["cited_event_ids"] == []
    assert body["answer"].startswith("No team news found")


@pytest.mark.parametrize(
    "body, message",
    [
        ({}, "either a question or filters"),
        ({"question": "q", "filters": {"player": "Pia Ash"}}, "either a question or filters"),
        ({"filters": {"player": "Zed Zed"}}, "Unknown player 'Zed Zed'"),
        ({"filters": {"player": "Pia Ash", "types": ["pass"]}}, "types: Extra inputs are not permitted"),
        ({"filters": {"player": "Pia Ash", "match": "nope"}}, "Unknown match"),
        ({"filters": {"player": "Pia Ash", "from": "2026-09-01T00:00:00Z", "to": "2026-08-01T00:00:00Z"}}, "ends before it starts"),
        ({"question": "What happened to Pia Ash?"}, "explicit filters"),
    ],
)
def test_history_rejections(client, body, message):
    response = client.post("/player_history", json=body)
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_history_does_not_change_predictions(client):
    match = _match(client)
    before = _predict(client, match).json()
    client.post("/player_history", json={"filters": {"player": "Pia Ash"}})
    assert _predict(client, match).json() == before
