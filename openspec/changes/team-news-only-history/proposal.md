# Proposal

## Why

Player history is for team news: what was reported about a player and when. Shots, tackles and starts add rows nobody asked for, make answers longer and invite questions the product is not about. The user wants history to retrieve only team news.

## What Changes

- Player history holds only team-news items: feed items, and a session's own submitted statuses (`news-in-player-history`). Shots, tackles and `started` rows are no longer returned or searchable.
- **BREAKING** `POST /player_history` loses the `types` filter and the `types` field of the response `filters`. A request that still sends `types` is rejected with 422.
- The history question parser no longer returns event types; the answer prompt and the template answer talk about team news only. A question about shots, tackles or starts is answered from the team news found (usually "nothing found"), never from other events.
- The optional Postgres + Apache AGE graph stops loading Shot and Tackle events and `STARTED` edges; it keeps clubs, players, matches and team-news events. Reload it after the change.
- ARCHITECTURE.md (`player_history` contract, "what is history", graph schema) and `backend/README.md` are updated.

## Capabilities

### New Capabilities

### Modified Capabilities
- `player-history-news`: adds the requirement that history contains only team news.

The `player_history` request and graph requirements still live only in the in-flight `player-history-graph-rag` change, not in `openspec/specs/`, so (as in the pronoun change) their update is a code and docs task, with no delta.

## Impact

- `backend/lineup_oracle/history.py`, `graph.py`, `api.py`, `agents.py` and their tests (`test_history*.py`, `test_graph.py`, `test_news_history.py`, `test_api.py`).
- ARCHITECTURE.md contracts: `player_history`, graph schema. The UI sends only a question, so it needs no change.
- Anyone sending `types` (none in this repo's UI) must stop.
