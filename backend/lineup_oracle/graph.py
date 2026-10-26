from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg

from .history import EVENT_TYPES, HistoryFilters, HistoryItem, iso, kickoff, occurred_at, team_news_players
from .roster import Player
from .state import State

GRAPH = "lineup"
CONNECT_TIMEOUT = 2  # seconds; the request falls back to memory when the database is slower than this
STATEMENT_TIMEOUT_MS = 5000
BATCH = 500  # rows per UNWIND

# The type test hides other events in a graph loaded before team news became the only history.
# Free text never reaches these strings: every value travels as an agtype parameter ($player, $match, ...).
EVENTS_QUERY = """
MATCH (p:Player {id: $player})-[:HAD]->(e:Event)-[:IN]->(m:Match)
WHERE e.type = 'team_news'
  AND ($match IS NULL OR m.id = $match)
  AND ($start IS NULL OR e.occurred_at >= $start)
  AND ($end IS NULL OR e.occurred_at <= $end)
RETURN e.id, e.type, m.id, e.occurred_at, e.payload
"""


@contextmanager
def connect(url: str) -> Iterator[psycopg.Connection]:
    """One short-lived connection with AGE loaded and on the search path; the transaction commits on a clean exit."""
    with psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT, options=f"-c statement_timeout={STATEMENT_TIMEOUT_MS}") as conn:
        try:
            conn.execute("LOAD 'age'")
        except psycopg.errors.InsufficientPrivilege:  # Azure preloads AGE via shared_preload_libraries and rejects LOAD
            conn.rollback()
        conn.execute('SET search_path = ag_catalog, "$user", public')
        yield conn


def _cypher(conn: psycopg.Connection, query: str, params: dict | None, columns: list[str]) -> list[tuple]:
    sql = f"SELECT * FROM cypher('{GRAPH}', $q${query}$q$, %s) AS ({', '.join(f'{c} agtype' for c in columns)})"
    rows = conn.execute(sql, (json.dumps(params or {}),)).fetchall()
    return [tuple(json.loads(v) if v is not None else None for v in row) for row in rows]


def _write(conn: psycopg.Connection, query: str, rows: list[dict]) -> None:
    for i in range(0, len(rows), BATCH):
        _cypher(conn, f"UNWIND $rows AS r {query}", {"rows": rows[i : i + BATCH]}, ["v"])


def load(url: str, state: State) -> dict[str, int]:
    """Drop and rebuild the graph from the state in one transaction; returns vertex and edge counts."""
    news = team_news_players(state)
    meta = {m.match_id: m.payload for m in state.metadata.values()}
    clubs = [{"name": c.name, "formation": c.formation} for c in state.roster.clubs.values()]
    players = [{"id": p.id, "name": p.name, "position": p.position, "number": p.number, "club": p.club} for p in state.players.values()]
    matches = [{"id": mid, "matchday": m["matchday"], "kickoff_at": iso(kickoff(m["matchday"])), "home": m["home_club"], "away": m["away_club"]} for mid, m in meta.items()]
    events = [
        {
            "id": e.id, "type": e.type, "minute": e.minute, "payload": e.payload, "mid": e.match_id,
            "player": e.player or news[e.id], "occurred_at": iso(occurred_at(e, meta[e.match_id]["matchday"])),
        }
        for e in state.events
        if e.type in EVENT_TYPES
    ]
    with connect(url) as conn:
        with conn.transaction():
            conn.execute("CREATE EXTENSION IF NOT EXISTS age")  # already there locally; on Azure it must be created once per database
            if conn.execute("SELECT count(*) FROM ag_graph WHERE name = %s", (GRAPH,)).fetchone()[0]:
                conn.execute("SELECT drop_graph(%s, true)", (GRAPH,))
            conn.execute("SELECT create_graph(%s)", (GRAPH,))
            _write(conn, "CREATE (:Club {name: r.name, formation: r.formation})", clubs)
            _write(conn, "CREATE (:Player {id: r.id, name: r.name, position: r.position, number: r.number})", players)
            _write(conn, "CREATE (:Match {id: r.id, matchday: r.matchday, kickoff_at: r.kickoff_at})", matches)
            _write(conn, "CREATE (:Event {id: r.id, type: r.type, minute: r.minute, occurred_at: r.occurred_at, payload: r.payload})", events)
            for label in ("Club", "Player", "Match", "Event"):  # vertex lookups by key would otherwise scan the label
                key = "name" if label == "Club" else "id"
                conn.execute(f'CREATE INDEX ON "{GRAPH}"."{label}" USING btree (ag_catalog.agtype_access_operator(properties, \'"{key}"\'::agtype))')
            _write(conn, "MATCH (p:Player {id: r.id}), (c:Club {name: r.club}) CREATE (p)-[:PLAYS_FOR]->(c)", players)
            _write(conn, "MATCH (c:Club {name: r.home}), (m:Match {id: r.id}) CREATE (c)-[:HOME_IN]->(m)", matches)
            _write(conn, "MATCH (c:Club {name: r.away}), (m:Match {id: r.id}) CREATE (c)-[:AWAY_IN]->(m)", matches)
            _write(conn, "MATCH (p:Player {id: r.player}), (e:Event {id: r.id}) CREATE (p)-[:HAD]->(e)", events)
            _write(conn, "MATCH (e:Event {id: r.id}), (m:Match {id: r.mid}) CREATE (e)-[:IN]->(m)", events)
            return counts(conn)


def counts(conn: psycopg.Connection) -> dict[str, int]:
    out = {}
    for label in ("Club", "Player", "Match", "Event"):
        out[label] = _cypher(conn, f"MATCH (v:{label}) RETURN count(v)", None, ["n"])[0][0]
    for rel in ("PLAYS_FOR", "HOME_IN", "AWAY_IN", "HAD", "IN"):
        out[rel] = _cypher(conn, f"MATCH ()-[r:{rel}]->() RETURN count(r)", None, ["n"])[0][0]
    return out


def fetch_history(url: str, player: Player, filters: HistoryFilters) -> list[HistoryItem]:
    """The graph's answer to the retrieval: items for the resolved player, in time then id order. Raises psycopg.Error when it cannot."""
    params = {
        "player": player.id,
        "match": filters.match,
        "start": iso(filters.start) if filters.start else None,
        "end": iso(filters.end) if filters.end else None,
    }
    with connect(url) as conn:
        events = _cypher(conn, EVENTS_QUERY, params, ["id", "type", "match_id", "occurred_at", "payload"])
    items = [HistoryItem(i, t, m, player.club, _moment(at), payload) for i, t, m, at, payload in events]
    return sorted(items, key=lambda i: (i.occurred_at, i.id))


def _moment(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the player-history graph in Postgres + Apache AGE from the roster and events.")
    parser.add_argument("--load", action="store_true", help="drop and rebuild the graph")
    args = parser.parse_args()
    url = os.environ.get("LINEUP_PG_URL")
    if not url:
        raise SystemExit("Set LINEUP_PG_URL, e.g. postgresql://lineup:lineup@127.0.0.1:5433/lineup (docker compose up -d)")
    if not args.load:
        parser.error("nothing to do: pass --load")
    for name, n in load(url, State.load()).items():
        print(f"{name}: {n}")


if __name__ == "__main__":
    main()
