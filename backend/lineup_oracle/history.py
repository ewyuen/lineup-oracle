from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .events import Event
from .roster import Player
from .state import State

SEASON_START = datetime(2026, 8, 15, 15, 0, tzinfo=timezone.utc)  # matchday 1 kickoff; every matchday follows a week later
MATCHDAY_SPACING = timedelta(days=7)
EVENT_TYPES = ("shot", "tackle", "team_news")  # the events that are player history; passes and the rest are not
HISTORY_TYPES = (*EVENT_TYPES, "started")  # `started` items come from the match metadata, not from an event


class HistoryError(ValueError):
    """The request cannot be answered; the message is shown to the user."""


@dataclass(frozen=True)
class HistoryFilters:
    player: str  # id or exact name
    types: tuple[str, ...] | None = None
    start: datetime | None = None  # inclusive
    end: datetime | None = None  # inclusive
    match: str | None = None


@dataclass(frozen=True)
class HistoryItem:
    id: str
    type: str
    match_id: str
    club: str
    occurred_at: datetime
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "match_id": self.match_id, "club": self.club, "occurred_at": iso(self.occurred_at), "payload": self.payload}


@dataclass(frozen=True)
class History:
    player: Player
    filters: HistoryFilters  # as used: player resolved to its id, times in UTC
    items: list[HistoryItem]

    def filters_dict(self) -> dict[str, Any]:
        f = self.filters
        return {"player": f.player, "types": list(f.types) if f.types is not None else None, "from": iso(f.start) if f.start else None, "to": iso(f.end) if f.end else None, "match": f.match}


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def kickoff(matchday: int) -> datetime:
    return SEASON_START + MATCHDAY_SPACING * (matchday - 1)


def occurred_at(event: Event, matchday: int) -> datetime:
    """Kickoff plus the event's minute; team news counts its offset (48, 24 or 1) as hours before kickoff."""
    if event.type == "team_news":
        return kickoff(matchday) - timedelta(hours=abs(event.minute))
    return kickoff(matchday) + timedelta(minutes=event.minute)


def resolve_player(state: State, ref: str) -> Player:
    if ref in state.players:
        return state.players[ref]
    named = [p for p in state.players.values() if p.name == ref]
    if len(named) > 1:
        raise HistoryError(f"{ref!r} matches more than one player: {', '.join(p.id for p in named)}; use a player id")
    if not named:
        raise HistoryError(f"Unknown player {ref!r}")
    return named[0]


def team_news_players(state: State) -> dict[str, str]:
    """Team news event id -> the id of the player of its club that its payload names (the event's own player is empty)."""
    by_name = {(p.club, p.name): p.id for p in state.players.values()}
    if len(by_name) != len(state.players):
        raise HistoryError("Two players of one club share a name, so team news cannot be linked to a player")
    linked = {}
    for e in state.events:
        if e.type != "team_news":
            continue
        name = e.payload.get("player_name")
        if (e.club, name) not in by_name:
            raise HistoryError(f"Team news {e.id} names {name!r}, who is not a player of {e.club}")
        linked[e.id] = by_name[(e.club, name)]
    return linked


def _utc(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


def retrieve_player_history(state: State, filters: HistoryFilters) -> History:
    """The player's shots, tackles, team news and starts, filtered, in time then id order. Reference implementation of the retrieval."""
    player = resolve_player(state, filters.player)
    types = filters.types
    if types is not None:
        unknown = sorted(set(types) - set(HISTORY_TYPES))
        if unknown:
            raise HistoryError(f"Unknown event type {', '.join(map(repr, unknown))}; use {', '.join(HISTORY_TYPES)}")
    start, end = _utc(filters.start), _utc(filters.end)
    if start and end and start > end:
        raise HistoryError("The time range ends before it starts")
    if filters.match is not None and filters.match not in state.metadata:
        raise HistoryError(f"Unknown match {filters.match!r}")
    used = HistoryFilters(player.id, tuple(types) if types is not None else None, start, end, filters.match)

    def wanted(kind: str, match_id: str, at: datetime) -> bool:
        return (
            (types is None or kind in types)
            and (filters.match is None or match_id == filters.match)
            and (start is None or at >= start)
            and (end is None or at <= end)
        )

    items: list[HistoryItem] = []
    news = team_news_players(state)
    for e in state.events:
        if e.type not in EVENT_TYPES or (e.player or news.get(e.id)) != player.id:
            continue
        at = occurred_at(e, state.metadata[e.match_id].payload["matchday"])
        if wanted(e.type, e.match_id, at):
            items.append(HistoryItem(e.id, e.type, e.match_id, e.club, at, e.payload))
    for match_id, meta in state.metadata.items():
        if player.id in meta.payload["home_xi"] + meta.payload["away_xi"]:
            at = kickoff(meta.payload["matchday"])
            if wanted("started", match_id, at):
                items.append(HistoryItem(f"{match_id}-start-{player.id}", "started", match_id, player.club, at, {"matchday": meta.payload["matchday"]}))
    items.sort(key=lambda i: (i.occurred_at, i.id))
    return History(player, used, items)


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}{'es' if noun.endswith('ch') else 's'}"


def template_answer(history: History) -> str:
    """Plain summary built only from the retrieved items: counts by type, then each team-news line with its date and id."""
    who = f"{history.player.name} ({history.player.club})"
    if not history.items:
        return f"Nothing found for {who} with these filters."
    counts = {kind: sum(i.type == kind for i in history.items) for kind in HISTORY_TYPES}
    parts = [_count(counts[kind], kind) for kind in ("shot", "tackle") if counts[kind]]
    if counts["started"]:
        parts.append(f"started {_count(counts['started'], 'match')}")
    text = f"{who}: {', '.join(parts) or 'no shots, tackles or starts'}."
    news = [f"{i.occurred_at:%Y-%m-%d} {i.payload.get('kind')}: {i.payload.get('text')} [{i.id}]" for i in history.items if i.type == "team_news"]
    return f"{text} Team news: {'; '.join(news)}." if news else text
