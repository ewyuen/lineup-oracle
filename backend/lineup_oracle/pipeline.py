from __future__ import annotations

import asyncio
import hashlib
import json
import re
import threading
from collections import OrderedDict
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .agents import Explanations, HistoryAnswer, ParsedHistoryQuestion, ParsedNews, Person, explainer_agent, history_answer_agent, history_parser_agent, parser_agent
from .llm import DEFAULT_TIMEOUT, LlmSettings, build_client
from .roster import Club, Player

T = TypeVar("T")
UNAVAILABLE = "Free-text team news parsing is unavailable right now; send a player id and a kind instead."
UNREADABLE = "The news could not be read as a player and a kind (injury, suspension or doubt); send a player id and a kind instead."
HISTORY_UNAVAILABLE = "Free-text questions are unavailable right now; send explicit filters (a player, and optionally event types and a time range) instead."
HISTORY_UNREADABLE = "The question could not be read; name a player and optionally event types and a time range, or send explicit filters."
MAX_HISTORY_ROWS = 100  # events the model sees, the newest
MAX_EXPLANATION_CHARS = 200
MAX_POST_CHARS = 200
POST_LANGUAGES = ("en", "es", "zh-Hant")
CACHE_SIZE = 256


class NewsRejected(Exception):
    """The text was not turned into news; the message is shown to the user and nothing changes."""


@dataclass(frozen=True)
class NewsRead:
    """What a free-text line means: a status for `player` (outcome "applied", `club` is the player's club) or a line
    to post to everyone (outcome "posted", `texts` has the three languages)."""

    outcome: str
    club: str
    player: Player | None = None
    kind: str | None = None
    texts: dict[str, str] | None = None


def _parse_json(model: type[T], text: str) -> T:
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return model.model_validate_json(stripped)  # type: ignore[attr-defined]


class Pipeline:
    """Interpret and Explain stages: two model agents behind validation. The XI itself never comes from here."""

    def __init__(self, client=None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self._parser = parser_agent(client) if client is not None else None
        self._explainer = explainer_agent(client) if client is not None else None
        self._history_parser = history_parser_agent(client) if client is not None else None
        self._history_answerer = history_answer_agent(client) if client is not None else None
        # shortcut: per-process cache of explanations, lost on restart; use a shared cache if the API runs several replicas
        self._cache: OrderedDict[str, dict[str, str]] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_lock = threading.Lock()

    @classmethod
    def from_env(cls) -> Pipeline:
        settings = LlmSettings.from_env()
        return cls(build_client(settings), settings.timeout) if settings else cls()

    @property
    def enabled(self) -> bool:
        return self._parser is not None

    def _run(self, work: Awaitable[T]) -> T:
        """Run a model call on one long-lived event loop thread, with a time limit."""
        with self._loop_lock:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                threading.Thread(target=self._loop.run_forever, name="llm-loop", daemon=True).start()
        future = asyncio.run_coroutine_threadsafe(work, self._loop)  # type: ignore[arg-type]
        try:
            return future.result(self.timeout)
        except BaseException:
            future.cancel()
            raise

    def _ask(self, agent, payload: dict[str, Any], model: type[BaseModel]):
        async def call():
            response = await agent.run(json.dumps(payload, ensure_ascii=False), options={"response_format": model})
            return _parse_json(model, response.text)

        return self._run(call())

    def interpret(self, text: str, club: Club) -> tuple[str, str]:
        """Free text to (player_id, kind) for this club, or NewsRejected."""
        if not self.enabled:
            raise NewsRejected(UNAVAILABLE)
        roster = [{"id": p.id, "name": p.name, "number": p.number, "position": p.position} for p in club.players]
        try:
            parsed = self._ask(self._parser, {"club": club.name, "roster": roster, "text": text}, ParsedNews)
        except (ValidationError, ValueError):
            raise NewsRejected(UNREADABLE) from None
        except Exception:  # model error or timeout
            raise NewsRejected(UNAVAILABLE) from None
        if parsed.club and parsed.club.strip().casefold() != club.name.casefold():
            raise NewsRejected(f"The news is about {parsed.club}, not {club.name}.")
        if parsed.player_id is None or parsed.kind is None:
            raise NewsRejected("The news names no player of this club or no kind (injury, suspension or doubt); send a player id and a kind instead.")
        if parsed.player_id not in {p.id for p in club.players}:
            raise NewsRejected(f"The news does not name a player of {club.name}.")
        return parsed.player_id, parsed.kind

    def read(self, text: str, club: Club, clubs: dict[str, Club], opponent: Club) -> NewsRead:
        """Free text to a status for a player of this match, or a line to post, or NewsRejected.

        `clubs` are all the clubs; persons are resolved here in code (selected club, opponent, any club), never by the model."""
        if not self.enabled:
            raise NewsRejected(UNAVAILABLE)
        roster = [{"id": p.id, "name": p.name, "number": p.number, "position": p.position} for p in club.players]
        try:
            parsed = self._ask(self._parser, {"club": club.name, "roster": roster, "text": text}, ParsedNews)
        except (ValidationError, ValueError):
            raise NewsRejected(UNREADABLE) from None
        except Exception:  # model error or timeout
            raise NewsRejected(UNAVAILABLE) from None
        mine = {p.id: p for p in club.players}
        by_name = {}
        for group in (club, opponent, *clubs.values()):  # first club listed wins a duplicate name
            for p in group.players:
                by_name.setdefault(p.name.casefold(), p)
        found: dict[str, Player] = {}
        persons = parsed.persons or ([Person(name=mine[parsed.player_id].name, player_id=parsed.player_id)] if parsed.player_id in mine else [])
        for person in persons:
            player = mine.get(person.player_id) if person.player_id else None
            player = player or by_name.get(" ".join(person.name.split()).casefold())
            if player is None:
                raise NewsRejected(f"Player not found: {person.name.strip() or 'unnamed person'}. Name a player of the clubs.")
            found[player.id] = player
        if len(found) > 1:
            raise NewsRejected("One player per line, please.")
        player = next(iter(found.values()), None)
        if player is not None and parsed.kind is not None:
            if player.club not in (club.name, opponent.name):
                raise NewsRejected(f"{player.name} plays for {player.club}, which is not in this match.")
            return NewsRead("applied", player.club, player, parsed.kind)
        if player is None:
            named = parsed.club and next((c for c in clubs if c.casefold() == parsed.club.strip().casefold()), None)
            if not named:
                raise NewsRejected("The news names no player and no team; name a player or a team.")
        texts = {lang: (parsed.translations or {}).get(lang, "").strip() for lang in POST_LANGUAGES}
        if any(not t or len(t) > MAX_POST_CHARS for t in texts.values()):
            raise NewsRejected(UNREADABLE)
        return NewsRead("posted", club.name, player, None, texts)

    def explain(self, facts: list[dict[str, Any]], mode: str, language: str) -> dict[str, str] | None:
        """Explanation text per player id, or None (use the templates) if the model is off or its answer is unusable."""
        if not self.enabled:
            return None
        key = hashlib.sha256(json.dumps([facts, mode, language], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        try:
            answer = self._ask(self._explainer, {"mode": mode, "language": language, "players": facts}, Explanations)
        except Exception:  # model error, timeout or unreadable answer
            return None
        texts = {item.id: item.text.strip() for item in answer.explanations}
        if len(texts) != len(answer.explanations) or set(texts) != {f["id"] for f in facts}:
            return None
        for text in texts.values():
            if not text or len(text) > MAX_EXPLANATION_CHARS or (mode == "fan" and ("%" in text or "p(start)" in text.casefold())):
                return None
        with self._cache_lock:
            self._cache[key] = texts
            if len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
        return texts

    def parse_history_question(self, question: str, kickoffs: dict[int, str]) -> ParsedHistoryQuestion:
        """Free-text question to unvalidated filters; ValueError with a user-facing message if the model is off or fails."""
        if not self.enabled:
            raise ValueError(HISTORY_UNAVAILABLE)
        try:
            return self._ask(self._history_parser, {"question": question, "matchday_kickoffs": {str(k): v for k, v in kickoffs.items()}}, ParsedHistoryQuestion)
        except (ValidationError, ValueError):
            raise ValueError(HISTORY_UNREADABLE) from None
        except Exception:  # model error or timeout
            raise ValueError(HISTORY_UNAVAILABLE) from None

    def answer_history(self, question: str | None, filters: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[str, list[str]] | None:
        """(answer, cited ids) written from the rows, or None (use the template) if the model is off, fails, or cites an event it was not given."""
        if not self.enabled or not rows:
            return None
        shown = rows[-MAX_HISTORY_ROWS:]
        try:
            answer = self._ask(self._history_answerer, {"question": question, "filters": filters, "events": shown}, HistoryAnswer)
        except Exception:  # model error, timeout or unreadable answer
            return None
        cited = list(dict.fromkeys(answer.cited_event_ids))
        if not answer.answer.strip() or not cited or not set(cited) <= {r["id"] for r in shown}:
            return None
        return answer.answer.strip(), cited
