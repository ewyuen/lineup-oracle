# Tasks

## 1. Branch

- [x] 1.1 Create the feature branch `feature/news-in-player-history` from `feature/player-history-graph-rag` (the trunk) and verify `git branch --show-current` shows it

## 2. Overlay in retrieval

- [x] 2.1 Add `delivered` and `session_news` (with `NewsEntry`) to `State` in `state.py`, not cleared by `reset()`, and verify with a unit test that `reset()` leaves both intact
- [x] 2.2 In `history.py`, fetch the player's rows from the graph or memory with only the type and match filters, then apply the delivered times, add the session's entries (same type and match filters), filter by `from`/`to` and sort by (time, id); add a `session_id` argument (default `default`). Verify with unit tests: a delivered item is re-timed, an undelivered one is not, another session's entry is absent, the time range includes a delivered item only when it covers now
- [x] 2.3 Extend the graph parity test (`test_graph.py`) so the graph and memory paths return the same rows with delivered items and session entries present, and verify `python -m pytest -q -k "graph or history"` passes (graph tests skip without `LINEUP_PG_URL`)

## 3. Recording the news

- [x] 3.1 Add the `now` callable to `create_app` and `Feed`; in `Feed.step` stamp the item with `state.delivered.setdefault(item.id, now())` before it is interpreted. Verify with unit tests: first delivery stamps, a second lap and `restart()` keep the first time, an unapplied item is stamped too
- [x] 3.2 In `POST /team_news`, when the status is applied (button or free text), add `manual-<player_id>-<kind>` with `setdefault`; add nothing for a rejection, a posted line or a line with no status. Verify with API tests: button, free text, repeat, a later kind adds a second entry, rejected and posted add none, another session does not see it

## 4. API, parser and UI

- [x] 4.1 Add `session_id` to `PlayerHistoryRequest` and pass it to the retrieval; verify an API test for the default, another session, and a 65-character id returning 422
- [x] 4.2 Give the history parser the current UTC time (payload `now`, one sentence in `HISTORY_PARSER_INSTRUCTIONS`, `now` argument on `Pipeline.parse_history_question`); verify a unit test that the payload carries `now`, that the prompt mentions it, and that the existing range validation is unchanged
- [x] 4.3 The UI history handler calls `EnsureSessionCookie()` and sends `GetSessionId()`; verify with a client test that the request body has `session_id`
- [x] 4.4 Check by hand with the dev servers and the `.env` model: let the feed deliver an item, ask about that player "what happened today?", press a status button, ask again; report what the history showed

## 5. Docs and full run

- [x] 5.1 Update ARCHITECTURE.md (the `player_history` contract and its `session_id`, "what is history" and times, "reads memory only", the persistence note, Feed and State) and `backend/README.md` if it describes history; verify the text matches the behavior
- [x] 5.2 Run the full backend suite (`python -m pytest -q` in `backend/`) and the UI tests (`dotnet test ui`) and verify both pass

## 6. Approval

- [x] 6.1 Human approval gate: stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR and merge it after `feature/player-history-graph-rag` (the PR targets that branch, or main once it has merged)
