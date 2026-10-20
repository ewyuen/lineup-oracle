# Architecture

Lineup Oracle predicts a club's starting XI before kick-off. It replays synthetic match and team-news events through a Microsoft Agent Framework pipeline, picks the XI with deterministic code, and uses an LLM only to parse team news and explain the pick.

This file holds the system picture and the contracts between components. Implementation detail lives in each OpenSpec change's `design.md`. Working plan, deadlines and tool allocation are in [PLAN.md](PLAN.md). Any change that alters a contract or component updates this file in the same PR.

Status key: **stable** (built or fixed), **draft** (agreed shape, will change when its OpenSpec change is proposed), **planned** (not built).

## System context

```mermaid
flowchart LR
    Gen["Synthetic data generator<br/>(seeded, Python)"] -->|events| Replay["Event replay<br/>(async queue)"]
    Replay --> Pipe["Agent pipeline<br/>(Agent Framework)"]
    Pipe <-->|parse / explain| LLM["Foundry gpt-4.1-mini"]
    Pipe --> API["FastAPI service"]
    MCP["MCP server<br/>predict_lineup, submit_team_news, list_matches, get_match_xi"] --> API
    UI["ASP.NET Razor + HTMX UI"] --> API
```

All data is synthetic: invented clubs and players, no crests, logos or photos.

## Pipeline

```mermaid
flowchart LR
    I[Ingest] --> N[Interpret team news]
    N --> P["Pick XI<br/>(P(start) score + SciPy MILP)"]
    P --> E[Explain]
    E --> Z[Personalize]
    N -. LLM fails .-> P
    E -. LLM fails .-> T[Template explanation]
    T --> Z
```

- **Deterministic:** P(start) is a transparent weighted score, with no trained model: `availability × (0.7 × quality + 0.3 × share of the last 5 matches started)`, where availability is 1 (available), 0.5 (doubt) or 0 (out). The MILP runs once per formation, weighted by the club's formation prior (1.0 for its usual formation, 0.85 for any other), and the best weighted total wins. Ties go to the lower player id.
- **LLM:** only parses free-text team news and writes explanations. If it fails, the XI is still returned, with a template explanation.
- **Team news has two input paths.** Structured events (UI preset buttons) skip the LLM and go straight to availability. Free-text news (generated, or typed in the UI) goes through the LLM parser, which outputs the same structured availability. If the parse fails or names an unknown player, the news is rejected with a message and the XI is unchanged.

## Azure deployment (planned)

```mermaid
flowchart LR
    U[User] --> UIc["Container App: UI"]
    UIc --> APIc["Container App: API + MCP"]
    APIc --> F["Foundry<br/>gpt-4.1-mini"]
    UIc & APIc --> AI[App Insights]
```

Telemetry uses OpenTelemetry only: the API and UI use the standard instrumentation, the pipeline uses the Agent Framework's built-in traces, and everything exports to App Insights through the Azure Monitor OpenTelemetry distro. No custom telemetry or dashboards. The traces show per-stage timing and LLM failures with the template fallback serving the XI.

Bicep, secrets in Container Apps secrets, managed identity where possible. Model deployment name comes from an environment variable.

## Contracts

### Event schema (stable)

One flat JSON object per event, JSON Lines on disk:

| Field | Type | Notes |
|---|---|---|
| `id` | string | unique |
| `match_id` | string | |
| `type` | string | pass, shot, tackle, possession_change, pressure, team_news (injury, suspension, late fitness doubt), match_metadata |
| `minute` | float | match minute; team news uses offsets before kick-off |
| `club` | string | |
| `player` | string or null | null for non-player events |
| `payload` | object | type-specific |
| `simulated` | bool | always true |

Generated team-news events are free text in `payload.text` (naming the club and player, with `player` null), so the LLM parser must read them. The payload also carries `kind` and `player_name` as answer labels for the parser eval; the parser must not read them. Events with structured fields only (UI preset buttons) skip the LLM. The structured truth is the true XI in the match metadata.

Match metadata records the actual starting XI and formation of both clubs, `payload.matchday` (1 to 10) and `payload.schema_version` (1). Event minutes are relative to each match's kick-off, so replay one match at a time. Source: `openspec/changes/synthetic-data-and-replay/design.md`.

### `predict_lineup` (stable)

`POST /predict_lineup` with `{match_id, club, mode, language}`. `mode` is `analyst` or `fan` (default analyst); `language` is `en`, `es` or `zh-Hant` (default en); both are validated and echoed, and change nothing until the pipeline and UI changes. The club must play in the match.
Response: `formation`; `players` (11, each with `id`, `name`, `number`, `position`, `p_start`, `explanation`); `alternatives` (up to 2 per position, same player shape); `llm_used` (false until the LLM explainer exists); `mode`; `language`. The prediction uses only the club's XIs from earlier matchdays plus the availability submitted for that match and club, never the match's own XI. Explanations are English templates for now.
Errors: `{"detail": message}` with 404 for an unknown match and 422 for a club not in the match, a bad mode or language, or when no formation can be filled.

### `submit_team_news` (stable)

`POST /team_news` with the predict fields plus `player_id` and `kind` (`injury`, `suspension` or `doubt`). Injury and suspension mark the player out, doubt marks the player doubt, for that match and club only; the latest news for a player wins. The response is the updated `LineupOut` (same shape as `predict_lineup`). The structured path is what the UI preset buttons use. A request with `text` and no player and kind is rejected with 422 ("not available yet") until the LLM parser exists in the pipeline change. A player outside the club, an unknown match or a bad kind is rejected with no state change. Availability lives in memory and is lost on restart.

### Read-only operations (stable)

`GET /matches` returns `[{match_id, matchday, home_club, away_club}]` in matchday order. `GET /matches/{match_id}/xi` returns the recorded XI and formation of both clubs (404 for an unknown match). `GET /health` returns `{"status": "ok"}`. Run with `uvicorn lineup_oracle.api:create_app --factory`.

### MCP server (stable)

A thin adapter over the FastAPI service with no logic of its own (`lineup_oracle/mcp_server.py`, stdio transport). Tools: `predict_lineup`, `submit_team_news` (same contracts as above), `list_matches` and `get_match_xi` (read-only). Each tool is one HTTP call to `LINEUP_API_URL` (default `http://127.0.0.1:8000`), and API errors come back as tool errors carrying the API's message. Any MCP client, such as GitHub Copilot or Claude Desktop, can submit structured team news and read the new XI; free text works once the pipeline change adds the parser. The agent pipeline does not call MCP. It is the first thing cut after Azure polish if time runs short.

### Pipeline stages (draft)

| Stage | In | Out |
|---|---|---|
| Ingest | replayed events | events grouped by match |
| Interpret | structured team-news events (built), or free-text news via the LLM parser (pipeline change) | availability per player (or rejection) |
| Pick XI | availability, roster, form | formation + 11 players with `p_start`, and up to 2 alternatives per position |
| Explain | picked XI | explanation per player |
| Personalize | explanations, mode, language, favourite club | final response |

## Evaluation

Correct starters out of 11 versus a "same XI as last match" baseline, on held-out synthetic matches. It shows the pipeline works, not real-world accuracy.

## Open decisions

- **Event Hubs instead of the in-process queue:** cut unless time allows. Owner: user. Decide by Oct 25 feature freeze.
- **Persistence:** none. Roster and events are files; prediction history, if needed, is in memory or SQLite. Postgres was cut (decided Oct 20).
- ~~Formation-to-MILP mapping and formation priors~~ Decided in `pstart-scoring-and-xi-optimizer`: one MILP per supported formation (1 GK, DEF, MID, FWD counts, middle bands as midfield), priors 1.0 / 0.85.
- **Theme fit of a pre-match predictor:** decided not to ask the sponsor; accepted risk.
