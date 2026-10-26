## 1. Branch

- [x] 1.1 Create the feature branch `feature/team-news-only-history` from `feature/player-history-graph-rag` and verify `git branch --show-current` shows it

## 2. Memory path and API

- [x] 2.1 In `history.py` keep only team news: `EVENT_TYPES = ("team_news",)`, delete `HISTORY_TYPES`, the `started` branch, the `types` field of `HistoryFilters`, the overlay type check and the type validation; rewrite `template_answer` to the team-news summary. Verify unit tests: shots, tackles and starts never appear, delivered and session news still do
- [x] 2.2 In `api.py` remove `types` from the `player_history` request filters and set `extra="forbid"` on `HistoryFiltersIn`, the response `filters` and the parser validation; verify an API test that `types` returns 422 and that the response filters have no `types`

## 3. Parser and answer prompts

- [x] 3.1 Update `HISTORY_PARSER_INSTRUCTIONS` (no types) and `HISTORY_ANSWER_INSTRUCTIONS` (team news only, say so when asked about other things), and `Pipeline` if it reads `types`; verify prompt tests and that a "shots" question is answered from team news only

## 4. Graph

- [x] 4.1 In `graph.py` load only team-news events, drop the `STARTED` edges, the starts query and the types clause, and filter the fetch to `type = 'team_news'`; verify the counts test and the graph/memory parity tests against local Postgres (`LINEUP_PG_URL`), updated for no `types`

## 5. Docs

- [x] 5.1 Update ARCHITECTURE.md (`player_history` contract without `types`, "what is history", graph schema and a reload note) and `backend/README.md`; verify the text matches the behavior

## 6. Verify

- [x] 6.1 Run the full backend suite (`python -m pytest -q` in `backend/`, plus the DB tests with `LINEUP_PG_URL`) and `dotnet test ui`, and verify all pass
- [x] 6.2 Check by hand with the dev servers: ask about a player's shots and about their team news; report what history showed

## 7. Approval

- [x] 7.1 Human approval gate: stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR (to `feature/player-history-graph-rag`, or main once it has merged) and merge it
