## 1. Setup

- [x] 1.1 Create the feature branch `feature/fastapi-and-mcp-server` from main (it already exists if you are reading this on it).
- [x] 1.2 Add `fastapi`, `uvicorn`, `mcp` and `httpx` to `backend/pyproject.toml` dependencies.

## 2. State and explanations

- [x] 2.1 Create `backend/lineup_oracle/state.py`: load roster and events (files if present, else generate from seed 42), index matches, hold availability per match, club and player, with a `reset`.
- [x] 2.2 Create `backend/lineup_oracle/explain.py`: the deterministic English template explanation per player.
- [x] 2.3 Unit tests: state loads from files and generates when the events file is missing; the match list has 30 matches in matchday order; the explanation mentions doubt for a doubt player and is deterministic.

## 3. API

- [x] 3.1 Create `backend/lineup_oracle/api.py`: Pydantic models and the routes `GET /matches`, `GET /matches/{match_id}/xi`, `POST /predict_lineup`, `POST /team_news`, `GET /health`.
- [x] 3.2 Implement prediction using only earlier matchdays and the submitted availability; map unknown match to 404 and bad club, player, kind, mode or language to 422.
- [x] 3.3 Implement the free-text rejection (422 with the "not available yet" message, no state change).
- [x] 3.4 Unit tests with `TestClient`: list and get-XI (including 404); prediction shape and legality; own XI never used (changing the match's own XI leaves the prediction unchanged); club not in the match; injury removes a starter and the XI stays legal; other matches unaffected; bad player rejected with no state change; doubt then injury gives out; free text rejected; same request twice gives identical responses.

## 4. MCP adapter

- [x] 4.1 Create `backend/lineup_oracle/mcp_server.py` with `FastMCP` and four tools that call the API with `httpx`, base URL from `LINEUP_API_URL` (default `http://127.0.0.1:8000`), and turn API errors into tool errors carrying the API message.
- [x] 4.2 Unit tests using `httpx.ASGITransport` against the real app: exactly four tools listed; each forwards its arguments; the submit-then-predict flow drops an injured starter; an unknown match gives an error with the API message; the URL comes from the environment.

## 5. Docs

- [x] 5.1 Update ARCHITECTURE.md in this PR: define the `predict_lineup` and `submit_team_news` contracts with endpoint paths and error shapes, mark the MCP server built, and note that the Interpret stage handles only structured news until change 4.
- [x] 5.2 Update `backend/README.md` with how to run the API (`uvicorn lineup_oracle.api:app`) and the MCP server, and update CLAUDE.md's backend commands and repo state only through a separate harness PR after merge.

## 6. Verify and approve

- [x] 6.1 Run the full backend suite (`cd backend && python -m pytest -q`) and fix any failure.
- [x] 6.2 Human approval gate (HITL): stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR and merge it. Do not archive or merge before approval.
