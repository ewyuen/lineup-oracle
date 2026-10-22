# Tasks

## 1. Branch and in-memory history

- [x] 1.1 Create branch `feature/player-history-graph-rag` from main (bringing this change folder with it); verify `git branch --show-current` prints it and the change files are tracked there.
- [x] 1.2 Add `history.py` with the season-start/kickoff rule, `occurred_at` (team-news offsets in hours, others in minutes), the player resolver (id or exact name, ambiguity and unknown errors), and `retrieve_player_history(state, filters)` over the in-memory events (shot, tackle, team news, plus `started` items from match metadata); verify with unit tests for kickoff spacing, 48-hour team news, type/time/match filters, time-then-id ordering, ambiguous and unknown players, and the `started` exclusion rule.
- [x] 1.3 Link team news to players by `payload.player_name` within the club, failing with the event id on a miss; verify with a unit test for a linked event and one for an unknown name.

## 2. Template answer and API

- [x] 2.1 Add the deterministic template summary (counts by type, matches started, dated team-news items, cited ids, "nothing found" case); verify with unit tests for a normal, an empty and a team-news-only history.
- [x] 2.2 Add `POST /player_history` (exactly one of `question` or `filters`, else 422; the `{filters, events, answer, cited_event_ids, llm_used}` shape; 422 for an unknown player) using the memory path and template answer; verify with API tests for filters, neither/both, unknown player, a question with no LLM configured (422 asking for filters), and that `/predict_lineup` is unchanged.
- [x] 2.3 Add the `ask_player_history` MCP tool as a pass-through that forwards the API's error message; verify with MCP tests for the tool list (five tools), forwarding, and an error case.

## 3. LLM question parsing and answering

- [x] 3.1 Add the history-parser and history-answer agents to `agents.py` and the `Pipeline` methods that call them (existing `LINEUP_LLM_*` settings and timeout, off when unset); verify with unit tests using `fake_llm.FakeClient` for success, timeout and an unreadable answer.
- [x] 3.2 Add question-to-filters parsing with strict validation (player resolves, types in the allowed set, times parse and are ordered, otherwise 422) and the cited-answer step (every cited id must be retrieved, else template; any LLM failure falls back to template with `llm_used` false); verify with unit tests using a fake LLM for a good parse, an invalid type, a missing player, a hallucinated citation, and an LLM error on an explicit-filters request.
- [x] 3.3 Wire the LLM into `/player_history`; verify with an API test using a fake LLM where a question returns events, cited ids and `llm_used` true.

## 4. Graph store (Postgres + Apache AGE)

- [ ] 4.1 Add `docker-compose.yml` for Postgres + AGE and add `psycopg` to the dependencies; verify `docker compose up -d` starts and a `SELECT * FROM ag_catalog.ag_graph` query runs.
- [ ] 4.2 Spike: confirm that one `UNWIND` with agtype parameters works through psycopg; record the result in design.md and choose batched or per-row loading; verify with a short script run against the container.
- [ ] 4.3 Add `graph.py` with the connect helper (`LOAD 'age'`, search path), `--load` (drop and rebuild in one transaction with the design's vertices and edges, no pass events) and the fixed parameterised retrieval query; verify with DB tests (skipped when `LINEUP_PG_URL` is unset) for the seeded counts (6 clubs, 120 players, 30 matches, shots, tackles and team news only) and for loading twice.
- [ ] 4.4 Route `/player_history` retrieval through the graph when `LINEUP_PG_URL` is set, falling back to memory on any `psycopg.Error` or when unset; verify with tests for unset, an unreachable URL (same result as memory), and a hostile player name like `}) DETACH DELETE` that matches nobody and leaves the graph intact.
- [ ] 4.5 Add the parity test running a set of filters through both the graph and the memory path and asserting identical results; verify it passes against the container and skips without one.

## 5. Contracts and docs

- [ ] 5.1 Update ARCHITECTURE.md in the same PR: system-context diagram, the `player_history` contract, the MCP tool list, the kickoff-time rule, and the "Persistence" open decision (record the reversal of the Oct 20 cut); verify by reading the file against the specs.
- [ ] 5.2 Update `backend/README.md` and CLAUDE.md with the new env vars (`LINEUP_PG_URL`), `docker compose up`, `python -m lineup_oracle.graph --load` and the new endpoint; verify the documented commands run as written.

## 6. Azure (cuttable)

- [ ] 6.1 Check that AGE is available in the target region and SKU; if it is not, drop this group and record that the demo is local-only with the memory path.
- [ ] 6.2 Add the Postgres Flexible Server (`azure.extensions` and `shared_preload_libraries` set to AGE) and the `LINEUP_PG_URL` secret to the Bicep; verify with `az bicep build` and a deployment of the loader against it.

## 7. Verify and approve

- [ ] 7.1 Run the full suite (`python -m pytest -q` from `backend/`, with and without `LINEUP_PG_URL`) and `openspec validate player-history-graph-rag --strict`; verify both are green, and run one question through the API end to end.
- [ ] 7.2 Human approval gate: summarize results, then stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR from `feature/player-history-graph-rag` and merge it.
