from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg

from .events import Event
from .roster import Player
from .state import State

SEASON_START = datetime(2026, 8, 15, 15, 0, tzinfo=timezone.utc)  # matchday 1 kickoff; every matchday follows a week later
MATCHDAY_SPACING = timedelta(days=7)
EVENT_TYPES = ("team_news",)  # the only events that are player history
log = logging.getLogger(__name__)


class HistoryError(ValueError):
    """The request cannot be answered; the message is shown to the user."""


@dataclass(frozen=True)
class HistoryFilters:
    player: str  # id or exact name
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
        return {"player": f.player, "from": iso(f.start) if f.start else None, "to": iso(f.end) if f.end else None, "match": f.match}


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def kickoff(matchday: int) -> datetime:
    return SEASON_START + MATCHDAY_SPACING * (matchday - 1)


def occurred_at(event: Event, matchday: int) -> datetime:
    """Kickoff plus the event's minute; team news counts its offset (48, 24 or 1) as hours before kickoff."""
    if event.type == "team_news":
        moment = kickoff(matchday) - timedelta(hours=abs(event.minute))
    else:
        moment = kickoff(matchday) + timedelta(minutes=event.minute)
    return _floor_ms(moment)


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


def _floor_ms(moment: datetime) -> datetime:
    """Times are kept to the millisecond, as `iso` prints them, so comparing datetimes and comparing their text agree."""
    return moment.replace(microsecond=moment.microsecond // 1000 * 1000)


def _utc(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    return _floor_ms(moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc))


GraphFetch = Callable[[Player, HistoryFilters], list[HistoryItem]]  # raises psycopg.Error when the graph cannot answer


def retrieve_player_history(state: State, filters: HistoryFilters, graph: GraphFetch | None = None, session_id: str = "default") -> History:
    """The player's team news, filtered, in time then id order.

    Filters are validated here. With a `graph` the rows come from it, and any database error falls back to the in-memory scan,
    which is the reference implementation and gives the same rows. Either store is asked without the time range: the news that
    arrived while the service ran is applied to its rows first (`_overlay`), then the range is."""
    player = resolve_player(state, filters.player)
    start, end = _utc(filters.start), _utc(filters.end)
    if start and end and start > end:
        raise HistoryError("The time range ends before it starts")
    if filters.match is not None and filters.match not in state.metadata:
        raise HistoryError(f"Unknown match {filters.match!r}")
    used = HistoryFilters(player.id, start, end, filters.match)
    stored = replace(used, start=None, end=None)
    items = None
    if graph is not None:
        try:
            items = graph(player, stored)
        except psycopg.Error as err:
            log.warning("Graph unavailable, answering player history from memory: %s", err)
    if items is None:
        items = history_from_memory(state, player, stored)
    return History(player, used, _overlay(state, player, used, items, session_id))


def _overlay(state: State, player: Player, used: HistoryFilters, items: list[HistoryItem], session_id: str) -> list[HistoryItem]:
    """Feed items re-timed to their delivery, this session's own submitted news added, then the time range applied."""
    delivered = dict(state.delivered)  # snapshots: the feed and requests write these from other threads
    rows = [replace(i, occurred_at=_floor_ms(delivered[i.id])) if i.id in delivered else i for i in items]
    for (session, player_id, kind), news in list(state.session_news.items()):
        if session == session_id and player_id == player.id and used.match in (None, news.match_id):
            payload = {"kind": kind, "text": news.text, "player_name": player.name}
            rows.append(HistoryItem(f"manual-{player.id}-{kind}", "team_news", news.match_id, news.club, _floor_ms(news.at), payload))
    rows = [i for i in rows if (used.start is None or i.occurred_at >= used.start) and (used.end is None or i.occurred_at <= used.end)]
    return sorted(rows, key=lambda i: (i.occurred_at, i.id))


def history_from_memory(state: State, player: Player, used: HistoryFilters) -> list[HistoryItem]:
    start, end = used.start, used.end

    def wanted(match_id: str, at: datetime) -> bool:
        return (used.match is None or match_id == used.match) and (start is None or at >= start) and (end is None or at <= end)

    items: list[HistoryItem] = []
    news = team_news_players(state)
    for e in state.events:
        if e.type not in EVENT_TYPES or (e.player or news.get(e.id)) != player.id:
            continue
        at = occurred_at(e, state.metadata[e.match_id].payload["matchday"])
        if wanted(e.match_id, at):
            items.append(HistoryItem(e.id, e.type, e.match_id, e.club, at, e.payload))
    return sorted(items, key=lambda i: (i.occurred_at, i.id))


def template_answer(history: History) -> str:
    """Plain summary built only from the retrieved items: how many team news items, each with its date and id."""
    who = f"{history.player.name} ({history.player.club})"
    if not history.items:
        return f"No team news found for {who} with these filters."
    news = [f"{i.occurred_at:%Y-%m-%d} {i.payload.get('kind')}: {i.payload.get('text')} [{i.id}]" for i in history.items]
    noun = "item" if len(news) == 1 else "items"
    return f"{who}: {len(news)} team news {noun}. {'; '.join(news)}."
