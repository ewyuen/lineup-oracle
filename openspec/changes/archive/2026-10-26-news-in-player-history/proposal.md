# Proposal

## Why

Player history is built only from the seeded events, so team news that arrives while the service runs (the shared feed, a visitor's free-text line, a status button) never shows up in it, and the seeded copy of a feed item sits at a made-up August time. History should say that news happened when it arrived, once, however many times the feed loops.

## What Changes

- **Feed news:** when the shared feed delivers an item, that item's history entry moves from its synthetic kickoff-based time to the delivery time. One entry per event id; later laps, the loop reset and `POST /news/restart` neither re-stamp nor duplicate it. Undelivered news keeps its synthetic time.
- **Manual news (per session):** a free-text line or a status button (injury, suspension, doubt, recovered, cleared, fit) that is applied adds an entry dated when it was first submitted, seen only in that session's history. Entries are deduplicated by (session, player, kind); a different kind for the same player is a new entry. Posted info lines stay out of history.
- **Memory only:** the delivered times and the session entries live in API memory and are lost on restart (accepted). The Postgres + Apache AGE graph stays an optional, read-only derived store (and is no longer deployed).
- **Retrieval:** the overlay is applied after the rows come back from the graph or from memory, and the time filter runs after it, so both paths return the same rows.
- **API:** `POST /player_history` gains an optional `session_id` (default `default`, at most 64 characters), and the UI sends its session id.
- **Today:** the history question parser is told the current UTC time so "today" and "this week" become a time range.

Contracts and components touched (ARCHITECTURE.md): the `player_history` contract (request field, times, "reads memory only" wording), the "what is history" and "times" notes, the persistence note, and the Feed and State components. The UI's history call.

## Capabilities

### New Capabilities
- `player-history-news`: news that arrives during a run becomes history, dated on arrival and added once; the feed's entries are shared, a visitor's own are private to the session.

### Modified Capabilities

None. The player-history requirements (graph, retrieval, `POST /player_history`, question parsing) are still in the in-flight `player-history-graph-rag` change, not in `openspec/specs/`, so there is nothing to modify yet. This change branches off that branch, builds on its code, and merges after it.

## Impact

- `backend/lineup_oracle/state.py`: delivered-time map and per-session news entries.
- `backend/lineup_oracle/ingest.py`: stamp an item when it is delivered.
- `backend/lineup_oracle/history.py`: apply the overlay and do the time filtering after it.
- `backend/lineup_oracle/api.py`, `pipeline.py`, `agents.py`: record applied manual news, `session_id` on the history request, the current time for the parser.
- `ui/LineupOracle.Ui`: send the session id with the history question.
- Tests: backend unit tests, one UI client test; ARCHITECTURE.md and `backend/README.md` if it describes history.
