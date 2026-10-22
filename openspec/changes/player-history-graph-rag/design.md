# Design

## Context

See proposal.md for motivation. ARCHITECTURE.md currently says "Persistence: none" and the `lineup-api` spec keeps all state in memory; this change adds one optional, read-only dependency and updates both.

Observed in the repo:
- `Event(id, match_id, type, minute, club, player, payload)`; `minute` is match-relative, and team news uses offsets of -48, -24 and -1 with `player` null and the name only in `payload.player_name`.
- The seeded data has 6 clubs, 120 players (no duplicate names), 30 matches and 29,219 events: 25,829 passes, 1,013 tackles, 871 shots, 822 pressure, 474 possession changes, 180 team news, 30 metadata.
- `State` already holds roster, events, `metadata` and `players` in memory; match metadata carries each club's true XI and the matchday.
- No LLM client exists yet (the pipeline change adds it). The only HTTP client dependency is `httpx`.
- The SciPy/HiGHS gotcha (all solves through `optimizer.py`) does not touch this change.

## Goals / Non-Goals

**Goals:**
- One retrieval function with one result shape, backed by the graph or by memory, so both give identical results.
- The XI path and API startup never depend on the database or the LLM.
- Retrieval is deterministic and testable without the LLM.

**Non-Goals:**
- Graph writes from the API (the loader is a separate command).
- Multi-hop analytics, embeddings, or LLM-written queries.
- Wrapping this as a Microsoft Agent Framework agent; the pipeline change can register `retrieve_player_history` as a tool later.

## Decisions

**1. Graph model.** Vertices: `Club{name, formation}`, `Player{id, name, position, number}`, `Match{id, matchday, kickoff_at}`, `Event{id, type, occurred_at, minute, payload}`. Edges: `(Player)-[:PLAYS_FOR]->(Club)`, `(Club)-[:HOME_IN|AWAY_IN]->(Match)`, `(Player)-[:STARTED]->(Match)`, `(Player)-[:HAD]->(Event)`, `(Event)-[:IN]->(Match)`. Event is a vertex, not an edge, so it keeps its own id, time and payload and can be cited. Rejected: events as edges (no stable id to cite, awkward payload).

**2. Load only player history.** Passes are 88% of events and say nothing a user asks about, so the loader keeps shot, tackle and team news (about 2,060 events). The in-memory fallback applies the same type set, so results stay identical. Rejected: loading everything (26k vertices of noise, slower loads, long answers).

**3. Derived index, separate loader.** `python -m lineup_oracle.graph --load` drops and rebuilds the graph from the files, in one transaction. The API only reads. API startup does not connect to the DB, so a down database cannot stop the service. Rejected: loading at startup (couples startup to the DB and slows it).

**4. Times are computed, not stored in the event file.** `kickoff_at = 2026-08-15T15:00Z + 7 days × (matchday - 1)`; `occurred_at = kickoff + minute` minutes, except team news, whose offsets are hours before kickoff (the generator's 48/24/1 mean two days, one day and one hour). No change to `events.jsonl` or the generator, so no regeneration gotcha. The constant lives in one place and is documented in ARCHITECTURE.md. Rejected: adding a timestamp to the event schema (bumps `schema_version`, regenerates data, touches a stable contract).

**5. Retrieval is a fixed template with parameters.** One Cypher template, built once, takes `player`, `types`, `from`, `to` and `match` as parameters; the Python in-memory version is the reference implementation, and a parity test runs both on the same filters. Free text never reaches query text. Player lookup is by id or exact name; the same name-to-player resolver is used for team-news linking (names are unique within a club in the seed, and the loader fails on a miss or a duplicate instead of guessing).

**6. Database access.** `psycopg` with one short-lived connection per request (connect timeout 2 s) and `LINEUP_PG_URL` from the environment; unset means memory. Any `psycopg.Error` falls back to memory for that request, with a log line. AGE needs `LOAD 'age'` and `SET search_path = ag_catalog, "$user", public` per session, done in one connect helper. Rejected: a connection pool (extra dependency, nothing to gain at this traffic). **Spike first:** confirm that bulk loading with `UNWIND` and agtype parameters works through psycopg; if not, load per row, since there are only about 2,300 vertices.

**7. Question handling (RAG).** Two LLM calls, both optional:
- Parse: system prompt plus the question returns JSON `{player, types, from, to, match}`. Code validates it (player resolves, types in the allowed set, times parse and are ordered) and rejects with 422 on any failure. Relative phrases such as "before matchday 3" are mapped to a kickoff time by the prompt using the matchday-to-kickoff rule given in the prompt.
- Answer: the system prompt gets only the retrieved rows (capped at 100, newest last) and must cite event ids. The code checks that every cited id was retrieved; if not, or if the call fails, it uses the template summary.
- The template summary is deterministic: counts by type, matches started, and each team-news item with its date, citing ids.

**8. LLM client.** `llm.py` posts to a Foundry OpenAI-compatible chat-completions endpoint with `httpx`, using `LLM_ENDPOINT`, `LLM_API_KEY` and `LLM_MODEL` from the environment; unset means unconfigured. Timeout 10 s, no retries. Rejected: adding the OpenAI SDK for two calls. The pipeline change may replace this with its own client.

**9. API and MCP.** `POST /player_history` takes either `question` or `filters` (exactly one, else 422) and returns `{filters, events, answer, cited_event_ids, llm_used}`. The MCP tool is the same pass-through as the others.

**10. Local and Azure.** `docker-compose.yml` runs the Apache AGE image; the loader and the DB-backed tests use `LINEUP_PG_URL` and skip when it is unset, so `python -m pytest -q` stays green on a machine without Docker. Azure Bicep (last task, cuttable): Flexible Server with `azure.extensions` and `shared_preload_libraries` set to AGE, URL in a Container Apps secret.

## Risks / Trade-offs

- **AGE and psycopg friction (agtype parameters, result parsing)** → spike task first; fall back to per-row loads and string-free templates; the memory path means nothing user-facing breaks.
- **Two implementations of retrieval can drift** → parity test over a set of filters on the seeded data.
- **LLM filter parsing is wrong or hallucinated** → strict validation and 422; the answer cites only retrieved ids or falls back to the template.
- **Azure AGE availability by region or SKU** → checked at the Bicep task; if unavailable, ship local-only and keep the memory path for the demo.
- **Schedule (5 days to Oct 27)** → order tasks so the memory path, API and tests come before any DB or Azure work; the graph, LLM and Azure groups are each independently cuttable.
- **Reverses the Oct 20 "Postgres was cut" decision** → recorded in ARCHITECTURE.md's open decisions.

## Migration Plan

Additive. No change to existing endpoints, data files or the XI path. Rollback is removing `LINEUP_PG_URL` (history serves from memory) or reverting the PR.
