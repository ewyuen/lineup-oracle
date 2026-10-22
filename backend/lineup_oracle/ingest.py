from __future__ import annotations

import logging
import threading
import time
from collections import deque

from opentelemetry import trace

from .checks import parse_correct
from .picking import STATUS_OF_KIND, pick
from .pipeline import NewsRejected
from .state import State

FEED_INTERVAL = 15  # seconds between items
POLL_INTERVAL = 10  # seconds between browser polls; the UI reads its own copy of this default
FEATURED_MATCHDAY = 1
LOG_SIZE = 50
log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)  # no-op unless the Azure Monitor distro set a provider


class Feed:
    """One shared, looping feed of team news. Each item is interpreted once, folded into the shared availability
    and the club's XI is picked once and stored, however many visitors there are. In memory only.

    The lock guards everything below and is never held across a model call or an optimizer solve."""

    def __init__(self, state: State, pipeline) -> None:
        self.state, self.pipeline = state, pipeline
        featured = {m for m, e in state.metadata.items() if e.payload["matchday"] == FEATURED_MATCHDAY}
        self.items = sorted(
            (e for e in state.events if e.type == "team_news" and e.match_id in featured),
            key=lambda e: (e.minute, e.match_id, e.id),
        )
        self.lock = threading.Lock()
        self.generation = 0  # bumped by every reset, so a model call that started before it is discarded
        self._pos = 0
        self._reanchor = False  # set by restart(): the producer starts its 15 s count again
        self._seq = 0  # never goes back, across resets too
        self._log: deque[dict] = deque(maxlen=LOG_SIZE)
        self._shared: dict[tuple[str, str], dict[str, tuple[str, int]]] = {}  # (match, club) -> {player: (status, seq)}
        self._predictions: dict[tuple[str, str], tuple] = {}  # (match, club) -> (xi, facts, seq)

    @property
    def latest_seq(self) -> int:
        with self.lock:
            return self._seq

    def _append(self, **entry) -> int:  # lock held
        self._seq += 1
        self._log.append({"seq": self._seq, **entry})
        return self._seq

    def post(self, match_id: str, club: str, texts: dict[str, str]) -> int:
        """Add a visitor's line to the log for everyone. Changes no availability or prediction; returns its seq."""
        with self.lock:
            return self._append(kind="info", match_id=match_id, club=club, texts=texts, applied=False)

    def _reset(self) -> None:  # lock held
        self.generation += 1
        self._shared.clear()
        self._predictions.clear()
        self._append(kind="restart", match_id=None, club=None, texts={}, applied=True)

    def step(self) -> None:
        """Deliver the next item; after the last one, reset instead (the lap starts again on the next call)."""
        with self.lock:
            if self._pos >= len(self.items):
                self._reset()
                self._pos = 0
                return
            item = self.items[self._pos]
            self._pos += 1
            generation = self.generation
        # The ticker thread has no request, so this is a root span of its own.
        with tracer.start_as_current_span("news.step") as span:
            span.set_attributes({"match_id": item.match_id, "club": item.club, "news.parse_correct": False, "news.applied": False})
            self._deliver(item, generation, span)

    def _deliver(self, item, generation: int, span) -> None:
        key = (item.match_id, item.club)
        text = item.payload["text"]  # the labels in the payload are compared with the answer after the parse, never given to the parser
        try:
            club = self.state.roster.clubs[item.club]
            player_id, kind = self.pipeline.interpret(text, club)  # model call, no lock held
            span.set_attribute("news.parse_correct", parse_correct(item, club, player_id, kind))
            if player_id not in {p.id for p in club.players}:
                raise NewsRejected(f"Player {player_id!r} does not belong to club {item.club!r}")
            with self.lock:
                before = dict(self._shared.get(key, {}))
            status = STATUS_OF_KIND[kind]
            xi, facts = pick(self.state, *key, {p: s for p, (s, _) in {**before, player_id: (status, 0)}.items()})
            outcome = (player_id, status, before, xi, facts)
        except Exception:  # unreadable, unknown player, no legal XI or a bug: the item is logged and the feed goes on
            outcome = None
        with self.lock:
            if generation != self.generation:
                return  # a reset happened meanwhile; the result belongs to the old lap
            entry = {"kind": "news", "match_id": item.match_id, "club": item.club, "texts": {"en": text, **item.payload["translations"]}}
            if outcome is None:
                self._append(**entry, applied=False)
                return
            player_id, status, before, xi, facts = outcome
            seq = self._append(**entry, applied=True)
            span.set_attribute("news.applied", True)
            self._shared[key] = {**before, player_id: (status, seq)}
            self._predictions[key] = (xi, facts, seq)

    def shared_availability(self, match_id: str, club: str) -> dict[str, tuple[str, int]]:
        with self.lock:
            return dict(self._shared.get((match_id, club), {}))

    def prediction(self, match_id: str, club: str) -> tuple:
        """The stored (xi, facts) for a match and club; picked once from the shared availability if absent.
        Raises what `pick` raises. Two first requests at the same moment may both pick; the first stored wins."""
        key = (match_id, club)
        with self.lock:
            if key in self._predictions:
                return self._predictions[key][:2]
            generation, shared = self.generation, dict(self._shared.get(key, {}))
        xi, facts = pick(self.state, match_id, club, {p: s for p, (s, _) in shared.items()})
        with self.lock:
            if generation == self.generation:
                self._predictions.setdefault(key, (xi, facts, self._seq))
        return xi, facts

    def restart(self) -> int:
        """Reset to the baseline and deliver the first item now; returns the latest sequence number."""
        with self.lock:
            self._reset()
            self._pos = 0
            self._reanchor = True
        self.step()
        return self.latest_seq

    def poll(self, since: int | None, match_id: str | None = None, club: str | None = None, language: str = "en") -> tuple[list[dict], int, bool]:
        """(entries with only `language`'s text, latest seq, whether a new entry changes this match and club). Reads only."""

        def project(e: dict) -> dict:
            return {**{k: v for k, v in e.items() if k != "texts"}, "text": e["texts"].get(language, "")}

        with self.lock:
            latest = self._seq
            if since is None:
                return [project(e) for e in self._log], latest, False
            entries = [project(e) for e in self._log if e["seq"] > since]
        changed = any(e["kind"] == "restart" or (e["kind"] != "info" and e["applied"] and (e["match_id"], e["club"]) == (match_id, club)) for e in entries)
        return entries, latest, changed

    def run(self, stop, clock=time.monotonic) -> None:
        """Producer loop: one step every FEED_INTERVAL from a fixed schedule, so a slow step is followed by one
        step, not a burst. `stop` is a threading.Event (or anything with wait(timeout) and set())."""
        next_at = clock() + FEED_INTERVAL
        while not stop.wait(max(0.0, next_at - clock())):
            with self.lock:
                moved, self._reanchor = self._reanchor, False
            if moved:  # a restart just delivered an item; count a full interval from now
                next_at = clock() + FEED_INTERVAL
                continue
            try:
                self.step()
            except Exception:  # the feed must never die
                log.exception("feed step failed")
            next_at = max(next_at + FEED_INTERVAL, clock())


def merge(shared: dict[str, tuple[str, int]], personal: dict[str, tuple[str, int]]) -> dict[str, str]:
    """Status per player from the shared and the personal availability: the later event (larger seq) wins, a tie goes to the personal one."""
    return {p: (personal[p] if p in personal and (p not in shared or personal[p][1] >= shared[p][1]) else shared[p])[0] for p in shared.keys() | personal.keys()}
