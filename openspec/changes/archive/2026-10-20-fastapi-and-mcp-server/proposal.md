## Why

The scoring and optimizer exist only as Python functions. The UI, the agent pipeline and any MCP client need a service that exposes them, with the match state (loaded events, submitted team news) behind it. This change builds that service and the thin MCP adapter, so the rest of the system has a stable contract to build on.

## What Changes

- Add a FastAPI service with four operations: list matches, get a match's actual XI, predict a lineup, and submit team news.
- Load the roster and events at startup (from the files, or generated in memory from seed 42 if the events file is missing). Keep availability from submitted team news in memory per match and club. No database.
- `predict_lineup` scores the club's players from earlier matchdays only (never the match's own XI), applies the submitted availability, picks the XI with the optimizer, and returns the formation, 11 players with `p_start`, alternatives per position and a template explanation. `llm_used` is always false in this change.
- `submit_team_news` accepts the structured event (player, kind) used by the UI preset buttons. A `text` field is accepted in the contract, but until the agent pipeline exists it is rejected with a clear message and the XI stays unchanged.
- `mode` (analyst or fan) and `language` (en, es, zh-Hant) are validated and echoed. Explanations stay in English until the pipeline and UI changes.
- Add an MCP server that is a thin adapter: four tools that call the API over HTTP and add no logic.
- Add `fastapi`, `uvicorn`, `mcp` and `httpx` as dependencies.

Contracts and components touched (from ARCHITECTURE.md): the `predict_lineup` and `submit_team_news` contracts (draft becomes defined, with endpoint paths and error shapes), the "MCP server" section, the system context diagram (API and MCP now built), and the pipeline's Interpret stage (structured path only, free text deferred). The event schema is unchanged.

Out of scope: the LLM parser and explainer, the agent pipeline, replay-driven live news into the API, the UI, authentication, and Azure deployment.

## Capabilities

### New Capabilities
- `lineup-api`: the HTTP service, its four operations, the in-memory match state and the error behavior.
- `mcp-adapter`: the MCP server whose tools forward to the API.

### Modified Capabilities

None.

## Impact

- New code in `backend/lineup_oracle/` (API and MCP modules) and tests in `backend/tests/`.
- `backend/pyproject.toml` gains the new dependencies.
- ARCHITECTURE.md and `backend/README.md` are updated in the same PR (run commands, endpoints).
