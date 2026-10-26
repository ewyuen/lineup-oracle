# Proposal

## Why

The service can say who starts but not what happened to a player: injuries, suspensions, starts, shots and tackles, and when. The 29k synthetic events are a flat file, and the roster-to-event relationships (club, player, match, event) are only implicit. A graph over that history, with a retrieval-augmented question answerer on top, lets a user ask "what happened to Pia Ash?" and get a cited answer. The data is deterministic and typed, so retrieval is a graph query, not vector search.

## What Changes

- Add a Postgres + Apache AGE graph (openCypher) holding Club, Player, Match and Event vertices and their edges. It is a derived index: `roster.json` and `events.jsonl` stay the source of truth, and a loader rebuilds the graph from them.
- Give each match a deterministic `kickoff_at` (season start plus one week per matchday), computed in the loader, and give each event an `occurred_at`. The event schema and `events.jsonl` do not change, so no regeneration is needed.
- Add `ask_player_history`: a question is turned into a small filter schema (player, club, event types, time range); fixed, parameterised Cypher templates fetch the rows; an answer is written from those rows only, citing event ids. The LLM never writes Cypher.
- Add the explicit-filter path: the same filters can be passed directly, with no LLM. When the LLM is unconfigured or fails, the answer is a template summary of the rows.
- When the graph DB is unreachable or not configured, the same filters run as an in-memory scan of the loaded events (identical results).
- Expose it as `POST /player_history`.
- Phase 2: this change builds on the current main baseline, where the MCP adapter has been removed, so there is no MCP tool.
- Modify the `lineup-api` requirement "In-memory state with no database": the XI path stays in memory and never depends on the graph; history reads may use the graph.
- Local Postgres + AGE through Docker Compose; the Azure Flexible Server (`azure.extensions` and `shared_preload_libraries` set to AGE) is the last, cuttable task.

Out of scope: vector search or embeddings, free-form LLM-generated Cypher, writing predictions or team news to the graph, graph analytics beyond one-hop and two-hop queries, the agent pipeline and its LLM explainer (separate change), UI changes.

## Capabilities

### New Capabilities
- `player-history-graph`: building and querying the Postgres/AGE graph of clubs, players, matches and timed events, including the deterministic kickoff times and the in-memory fallback with identical results.
- `player-history-qa`: answering "what happened to this player" from retrieved graph rows, from a free-text question or explicit filters, with cited event ids and a template answer when no LLM is available.

### Modified Capabilities
- `lineup-api`: the "In-memory state with no database" requirement allows an optional graph database for history reads only, and the API gains `POST /player_history`.

## Impact

- **ARCHITECTURE.md:** touches the system-context diagram (graph DB beside the API), the Azure deployment diagram (Postgres Flexible Server), a new `player_history` contract and the "Persistence" open decision, which reverses the Oct 20 "Postgres was cut" note. All are updated in the same PR.
- **Code:** new modules under `backend/lineup_oracle/` (graph loader and queries, history service, small LLM client), a route in `api.py`, new tests. No change to events, replay, scoring or the optimizer.
- **Dependencies:** a Postgres driver (`psycopg`); the LLM call reuses `httpx`.
- **Infra:** `docker-compose.yml` for local Postgres + AGE; Bicep addition for the Flexible Server (last task).
- **Risk:** AGE's openCypher support through psycopg is less mature than plain SQL, so the loader and queries need tests against a real AGE container. The XI path is unaffected if the graph fails.
