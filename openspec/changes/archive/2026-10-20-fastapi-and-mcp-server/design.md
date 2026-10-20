## Context

See proposal.md for why. The scoring (`scoring.py`), optimizer (`optimizer.py`), roster and events already exist and are pure Python. This change wraps them in a service. There is no database (Postgres is cut), and no LLM yet (change 4). The event schema was kept as plain dataclasses in the data change, with Pydantic deferred to this change.

## Goals / Non-Goals

**Goals:**
- A small, stable HTTP contract the UI, pipeline and MCP adapter can rely on.
- A prediction that can never see its own match's XI.
- An MCP adapter that is trivially thin.

**Non-Goals:**
- LLM parsing and explanations, the pipeline, live replay into the API, UI, authentication, deployment.
- Persistence. State is in memory and lost on restart.

## Decisions

- **Layout:** `backend/lineup_oracle/api.py` (FastAPI app, models, routes), `state.py` (loaded data and availability), `explain.py` (template explanations) and `mcp_server.py` (adapter). Alternative: one module. Rejected, because `state.py` and `explain.py` are what change 4 replaces or extends, and the adapter must not import the API internals.
- **Routes:** `GET /matches`, `GET /matches/{match_id}/xi`, `POST /predict_lineup`, `POST /team_news`, `GET /health`. Operation names match the MCP tools. Alternative: REST resources per club. Rejected as extra surface the demo does not need.
- **State:** one `State` object built at startup (roster, events indexed by match, `availability[match_id][club][player_id]`), held on `app.state`, with a `reset` method for tests. Single process, so no locking beyond FastAPI's default. Assumption: one API process in the demo (Container Apps with one replica); revisit in the Azure change if it scales out.
- **Data loading:** use `data/roster.json` and `data/events.jsonl` if present, else generate from seed 42 in memory. Alternative: require the files. Rejected, because a fresh clone and the CI-less test runs would fail.
- **Prediction:** `recent_xis(events, club, matchday)` (earlier matchdays only) feeds `p_start_scores` with the match's availability for that club, then `pick_xi`. Generated team-news events in the file are free text and are not applied here: no parser exists until change 4. So the baseline availability is "all available" plus whatever was submitted. Assumption: acceptable for this change, and the pipeline change adds replayed news.
- **Sessions:** requests carry an optional `session_id` (default `default`, at most 64 characters) and availability is keyed by `(session_id, match_id, club)`, so visitors to one deployment do not overwrite each other's news. Sessions are never evicted (a `shortcut:` comment in `state.py` says when to add a cap or expiry). Added after review.
- **Team news kinds:** injury and suspension map to out, doubt to doubt, matching the scorer's availability values. Latest submission for a player wins. An invalid player or kind is rejected before any state changes. Validation lives in the API, since `p_start_scores` already raises `ValueError` for bad ids and statuses; the route maps those to 422.
- **Free text:** the request model has an optional `text`. A request with `text` and no player and kind gets 422 with "free-text parsing is not available yet". This keeps the contract final so change 4 only replaces that branch.
- **Mode and language:** validated with enums (analyst or fan; en, es, zh-Hant) and echoed in the response. No behavior change yet. Assumption: change 4 (explanations) and 5 (UI) give them meaning.
- **Template explanation:** one sentence per player built from `p_start`, number of starts in the last 5, the strongest rating and the availability, for example "Starter likely: 0.81 P(start), started 4 of the last 5, strong shooting." Deterministic and English only.
- **Models:** Pydantic request and response models in `api.py`, which are the contract written into ARCHITECTURE.md.
- **MCP adapter:** official `mcp` package (`FastMCP`), four tools, each one `httpx` call to `LINEUP_API_URL`, errors turned into tool errors with the API's message. Stdio transport by default. Alternative: mount MCP inside the FastAPI app. Rejected, because the adapter must stay separable (it is the first thing cut) and ARCHITECTURE.md says it calls the API.
- **Tests:** API tests with FastAPI's `TestClient` on seeded data. Adapter tests call the tool functions with an `httpx.ASGITransport` pointed at the real app, so the "flow through MCP" scenario runs end to end without a server process.
- **Dependencies:** `fastapi`, `uvicorn`, `mcp`, `httpx` in `pyproject.toml`; all already installed locally.

## Risks / Trade-offs

- [Free-text news is rejected, so the full MCP demo flow is not complete until change 4] → Documented in the proposal and the spec. The structured path demonstrates the flow now.
- [In-memory availability is lost on restart and is not shared across replicas] → Accepted for the demo. Revisit in the Azure change.
- [The adapter and the API drift] → The adapter has no logic and a test forwards each tool to the real app.
- [Generated team-news events are not used by predictions yet] → Explicit assumption above, so the pre-match XI in this change ignores injuries unless submitted.
