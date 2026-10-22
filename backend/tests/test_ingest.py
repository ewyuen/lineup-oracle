from __future__ import annotations

import copy
import threading

import pytest

from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.ingest import FEATURED_MATCHDAY, LOG_SIZE, Feed
from lineup_oracle.picking import pick
from lineup_oracle.pipeline import NewsRejected
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster
from lineup_oracle.state import State

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)


class FakePipeline:
    """Reads the labels the generator wrote, the way a perfect model would. `override` maps a text to an answer or an Exception."""

    def __init__(self, state: State) -> None:
        by_name = {p.name: p.id for p in state.players.values()}
        self.answers = {e.payload["text"]: (by_name[e.payload["player_name"]], e.payload["kind"]) for e in state.events if e.type == "team_news"}
        self.override: dict[str, object] = {}
        self.calls: list[str] = []
        self.hook = None

    def interpret(self, text, club):
        self.calls.append(text)
        if self.hook:
            self.hook()
        answer = self.override.get(text, self.answers[text])
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def state() -> State:
    return State(ROSTER, copy.deepcopy(EVENTS))


@pytest.fixture
def pipe(state) -> FakePipeline:
    return FakePipeline(state)


@pytest.fixture
def feed(state, pipe) -> Feed:
    return Feed(state, pipe)


def _first_key(feed):
    item = feed.items[0]
    return item.match_id, item.club


def _entries(feed):
    return feed.poll(None)[0]


def test_feed_holds_only_matchday_one_team_news_in_order(feed, state):
    assert 0 < len(feed.items) <= 18
    assert {e.type for e in feed.items} == {"team_news"}
    assert {state.metadata[e.match_id].payload["matchday"] for e in feed.items} == {FEATURED_MATCHDAY}
    assert [(e.minute, e.match_id, e.id) for e in feed.items] == sorted((e.minute, e.match_id, e.id) for e in feed.items)


def test_sequence_numbers_never_decrease_and_log_is_bounded(feed):
    for _ in range(len(feed.items) * 4):
        feed.step()
    seqs = [e["seq"] for e in _entries(feed)]
    assert len(seqs) == LOG_SIZE and seqs == sorted(seqs) and len(set(seqs)) == LOG_SIZE
    assert feed.latest_seq > LOG_SIZE


def test_injury_removes_player_from_stored_prediction(feed, state, pipe):
    item = feed.items[0]
    player_id, kind = pipe.answers[item.payload["text"]]
    before, _ = pick(state, item.match_id, item.club, {})
    feed.step()
    xi, facts, seq = feed._predictions[(item.match_id, item.club)]
    assert player_id not in {p.id for p, _ in xi.players} or kind == "doubt"
    assert len(xi.players) == 11
    assert feed._shared[(item.match_id, item.club)][player_id] == (kind, seq)
    entry = _entries(feed)[-1]
    assert entry["applied"] and entry["text"] == item.payload["text"]


def test_each_item_is_interpreted_once_however_many_reads(feed, pipe):
    feed.step()
    for _ in range(50):
        feed.poll(0, *_first_key(feed))
    assert pipe.calls == [feed.items[0].payload["text"]]


@pytest.mark.parametrize("bad", [NewsRejected("unreadable"), RuntimeError("boom"), ("ghost-1", "injury")])
def test_unusable_item_is_logged_not_applied_and_changes_nothing(feed, pipe, bad):
    pipe.override[feed.items[0].payload["text"]] = bad
    feed.step()
    assert [e["applied"] for e in _entries(feed)] == [False]
    assert feed._shared == {} and feed._predictions == {}
    feed.step()  # the next item still runs
    assert [e["applied"] for e in _entries(feed)] == [False, True]


def test_item_that_leaves_no_legal_xi_is_not_applied(feed, state, monkeypatch):
    def refuse(*args, **kwargs):
        raise ValueError("no legal XI")

    monkeypatch.setattr("lineup_oracle.ingest.pick", refuse)
    feed.step()
    assert [e["applied"] for e in _entries(feed)] == [False] and feed._predictions == {}


def test_lap_wraps_with_a_marker(feed):
    for _ in range(len(feed.items)):
        feed.step()
    assert all(e["kind"] == "news" for e in _entries(feed))
    feed.step()  # one interval later: reset
    assert _entries(feed)[-1]["kind"] == "restart" and feed._shared == {} and feed._predictions == {}
    feed.step()
    assert [e["kind"] for e in _entries(feed)[-2:]] == ["restart", "news"]
    assert _entries(feed)[-1]["text"] == feed.items[0].payload["text"]


def test_restart_mid_lap_gives_marker_then_item_one(feed):
    for _ in range(3):
        feed.step()
    before = feed.latest_seq
    assert feed.restart() == before + 2
    last = _entries(feed)[-2:]
    assert [e["kind"] for e in last] == ["restart", "news"] and last[1]["text"] == feed.items[0].payload["text"]
    assert list(feed._shared) == [_first_key(feed)]  # only item 1 is applied


def test_restart_during_a_model_call_discards_the_late_result(feed, pipe):
    pipe.hook = lambda: (setattr(pipe, "hook", None), feed.restart())  # the restart happens while step() waits on the model
    feed.step()
    kinds = [(e["kind"], e["text"]) for e in _entries(feed)]
    assert kinds == [("restart", ""), ("news", feed.items[0].payload["text"])]  # the late result of the old lap is gone


def test_poll_changed_rules(feed):
    key = _first_key(feed)
    feed.step()
    items, latest, changed = feed.poll(0, *key)
    assert len(items) == 1 and latest == 1 and changed
    assert not feed.poll(0, "match-x", "nobody")[2]  # other club
    assert not feed.poll(latest, *key)[2] and feed.poll(latest, *key)[0] == []
    assert feed.poll(None, *key)[2] is False  # first poll reports nothing changed
    feed.restart()
    assert feed.poll(latest, "match-x", "nobody")[2]  # a marker concerns every club


def test_step_exception_does_not_break_the_next_step(feed, monkeypatch):
    calls = []
    real = feed.pipeline.interpret

    def flaky(text, club):
        calls.append(text)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return real(text, club)

    monkeypatch.setattr(feed.pipeline, "interpret", flaky)
    feed.step()
    feed.step()
    assert [e["applied"] for e in _entries(feed)] == [False, True]


def test_concurrent_steps_and_polls_keep_the_log_consistent(feed):
    threads = [threading.Thread(target=feed.step) for _ in range(6)] + [threading.Thread(target=lambda: feed.poll(0)) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [e["seq"] for e in _entries(feed)] == list(range(1, 7))


class FakeStop:
    """Event stand-in with a fake clock: wait() advances time and records each deadline; stops after `limit` waits."""

    def __init__(self, clock, limit):
        self.clock, self.limit, self.waits = clock, limit, []

    def wait(self, timeout):
        self.waits.append(timeout)
        self.clock.now += timeout
        return len(self.waits) > self.limit


class FakeClock:
    now = 0.0

    def __call__(self):
        return self.now


def test_producer_does_not_burst_after_a_slow_step(feed, monkeypatch):
    clock, ticks = FakeClock(), []
    real = feed.step

    def step():
        ticks.append(clock.now)
        if len(ticks) == 1:
            clock.now += 40  # the first item takes 40 s
        real()

    monkeypatch.setattr(feed, "step", step)
    feed.run(FakeStop(clock, 3), clock)
    assert ticks == [15, 55, 70]  # one catch-up step right away, then back on the 15 s schedule


def test_producer_survives_an_error_in_a_tick(feed, monkeypatch):
    clock, ticks = FakeClock(), []

    def step():
        ticks.append(clock.now)
        raise RuntimeError("boom")

    monkeypatch.setattr(feed, "step", step)
    feed.run(FakeStop(clock, 3), clock)
    assert ticks == [15, 30, 45]


def test_restart_moves_the_producer_schedule(feed, monkeypatch):
    clock, ticks = FakeClock(), []
    monkeypatch.setattr(feed, "step", lambda: ticks.append(clock.now))
    stop = FakeStop(clock, 3)
    wait = stop.wait
    stop.wait = lambda t: (feed.restart() if len(stop.waits) == 0 else None, wait(t))[1]
    feed.run(stop, clock)
    assert ticks[0] == 0 and ticks[1:] == [30, 45]  # restart() stepped at 0; the 15 s tick is skipped, then 15 s from there


def test_entries_keep_all_texts_and_poll_projects_one_language(feed, pipe):
    item = feed.items[0]
    pipe.override[feed.items[1].payload["text"]] = NewsRejected("no")  # the second item is not applied
    feed.step()
    feed.step()
    assert set(feed._log[0]["texts"]) == {"en", "es", "zh-Hant"} and feed._log[1]["applied"] is False
    assert feed._log[0]["texts"] == {"en": item.payload["text"], **item.payload["translations"]}
    for lang, expected in [("en", item.payload["text"]), ("es", item.payload["translations"]["es"]), ("zh-Hant", item.payload["translations"]["zh-Hant"])]:
        entries = feed.poll(None, language=lang)[0]
        assert entries[0]["text"] == expected and "texts" not in entries[0]
    assert feed.poll(None)[0][0]["text"] == item.payload["text"]  # English by default
    assert len(pipe.calls) == 2  # polling interpreted nothing


def test_post_appends_an_info_entry_for_every_language_and_changes_nothing(feed):
    key = _first_key(feed)
    feed.step()
    shared, predictions = dict(feed._shared), dict(feed._predictions)
    seq = feed.post(*key, {"en": "Hello", "es": "Hola", "zh-Hant": "你好"})
    assert seq == feed.latest_seq == 2
    assert (feed._shared, feed._predictions) == (shared, predictions)
    for lang, text in {"en": "Hello", "es": "Hola", "zh-Hant": "你好"}.items():
        entry = feed.poll(1, *key, language=lang)[0][0]
        assert (entry["kind"], entry["text"], entry["applied"]) == ("info", text, False)


def test_info_entry_never_makes_the_poll_report_a_change(feed):
    key = _first_key(feed)
    feed.post(*key, {"en": "a", "es": "b", "zh-Hant": "c"})
    items, _, changed = feed.poll(0, *key)
    assert len(items) == 1 and changed is False


def test_posted_line_survives_a_restart(feed):
    key = _first_key(feed)
    feed.post(*key, {"en": "a", "es": "b", "zh-Hant": "c"})
    feed.restart()
    assert [e["kind"] for e in _entries(feed)] == ["info", "restart", "news"]


def test_merge_keeps_the_kind_through_precedence():
    from lineup_oracle.ingest import merge

    shared = {"a": ("suspension", 5), "b": ("injury", 3), "c": ("doubt", 4)}
    personal = {"a": ("doubt", 4), "b": ("suspension", 3), "d": ("injury", 1)}
    merged = merge(shared, personal)
    assert merged["a"] == ("suspension", 5)  # the later feed event wins
    assert merged["b"] == ("suspension", 3)  # same sequence: personal wins
    assert merged["c"] == ("doubt", 4) and merged["d"] == ("injury", 1)
    assert merge(personal, shared)["a"] == ("suspension", 5)


def test_merge_keeps_a_personal_suspension_against_a_later_feed_event():
    from lineup_oracle.ingest import merge

    personal = {"a": ("suspension", 3), "b": ("suspension", 3), "c": ("injury", 8)}
    shared = {"a": ("injury", 5), "b": ("cleared", 5), "c": ("suspension", 2)}
    merged = merge(shared, personal)
    assert merged["a"] == ("suspension", 3)  # a feed injury does not end it
    assert merged["b"] == ("cleared", 5)  # a feed clearing does
    assert merged["c"] == ("injury", 8)  # the session cleared it earlier, so its later injury stands


def test_feed_ignores_news_after_a_shared_suspension(feed, pipe):
    item = feed.items[0]
    key = _first_key(feed)
    player = pipe.answers[item.payload["text"]][0]
    feed._shared[key] = {player: ("suspension", 1)}
    feed.step()
    assert feed.shared_availability(*key)[player][0] == "suspension"


def test_feed_keeps_injury_doubt_and_suspension_apart(feed, pipe):
    item = feed.items[0]
    key = _first_key(feed)
    for kind in ("injury", "doubt", "suspension"):
        pipe.override[item.payload["text"]] = (pipe.answers[item.payload["text"]][0], kind)
        feed.restart()
        assert feed.shared_availability(*key)[pipe.answers[item.payload["text"]][0]][0] == kind


def _personal(state, key, seq=0):
    state.availability[("s", *key)] = {"p": ("injury", seq)}
    state.selections[("s", *key)] = ("p",)


def test_manual_restart_clears_every_sessions_news_and_alternatives(feed, state):
    key = _first_key(feed)
    _personal(state, key)
    state.availability[("other", *key)] = {"q": ("doubt", 0)}
    feed.restart()
    assert state.availability == {} and state.selections == {}
    assert [e["kind"] for e in _entries(feed)[-2:]] == ["restart", "news"]  # first item still delivered at once


def test_automatic_reset_keeps_personal_news(feed, state):
    key = _first_key(feed)
    _personal(state, key)
    for _ in range(len(feed.items) + 1):  # every item, then the reset
        feed.step()
    assert any(e["kind"] == "restart" for e in _entries(feed))
    assert state.availability and state.selections


def test_news_submitted_after_a_restart_is_kept(feed, state):
    key = _first_key(feed)
    _personal(state, key)
    feed.restart()
    _personal(state, key)
    assert ("s", *key) in state.availability


def test_restart_waits_for_the_state_lock(feed, state):
    done = threading.Event()
    with state.lock:
        t = threading.Thread(target=lambda: (feed.restart(), done.set()))
        t.start()
        assert not done.wait(0.2)  # held back by the lock a news submit would hold
    assert done.wait(5)
    t.join()
