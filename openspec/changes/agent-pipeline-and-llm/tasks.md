## 1. Setup

- [x] 1.1 Create the feature branch `feature/agent-pipeline-and-llm` from main (it already exists if you are reading this on it).
- [x] 1.2 Add `agent-framework-core`, `agent-framework-openai` and `azure-identity` to `backend/pyproject.toml` and install them; confirm `from agent_framework import Agent` works.

## 2. Model seam

- [x] 2.1 Create `lineup_oracle/llm.py`: settings from `LINEUP_LLM_ENDPOINT`, `LINEUP_LLM_DEPLOYMENT`, optional `LINEUP_LLM_API_KEY` (else default Azure credentials) and `LINEUP_LLM_TIMEOUT` (default 15); `enabled` only when endpoint and deployment are set; a function that builds the chat client; a `--check` entry point that makes one real structured-output call and prints the result.
- [x] 2.2 A small fake chat client for tests (returns queued canned answers, can raise or sleep), kept in `tests/`.
- [x] 2.3 Tests: settings off when either variable is missing; on when both are set; timeout default and override.

## 3. Agents and pipeline

- [x] 3.1 Create `lineup_oracle/agents.py`: the News Parser agent (roster and text in, `{club, player_id, kind}` out as a pydantic structured output) and the Explainer agent (facts, mode and language in, `{explanations: [{id, text}]}` out), each built from an Agent Framework `Agent` with short instructions as specified in design.md.
- [x] 3.2 Create `lineup_oracle/pipeline.py`: the long-lived event-loop thread that runs model calls with a timeout; `interpret(text, club)` that validates club, player id and kind and raises a rejection with a specific message; `explain(facts, mode, language)` that validates the answer (exact id set, non-empty, at most 200 characters, no `%` or `P(start)` in fan mode), caches by a hash of the facts (bounded to 256, with a `# shortcut:` comment) and returns `None` on any failure.
- [x] 3.3 Add the `mode` argument to the template in `explain.py` (fan drops the `P(start)` clause).
- [x] 3.4 Unit tests with the fake client: parser accepts a valid answer; rejects an unknown player id, another club, no player, a bad kind and malformed output; ignores extra fields; model error and timeout give the unavailable rejection; explainer accepts a full valid answer; returns `None` for a missing player, an extra id, an empty text, an over-long text, a fan text with `%`, an error and a timeout; the same facts hit the cache and call the model once; changed facts call it again; model off returns `None` and the unavailable rejection; fan template has no `P(start)`; analyst template unchanged.

## 4. API wiring

- [x] 4.1 Change `create_app` to take an optional pipeline (default from the environment); in `_lineup` ask the pipeline for explanations over the XI and the alternatives, fall back to the templates (with the request's mode) on `None`, and set `llm_used` from the result.
- [x] 4.2 Accept free `text` in `POST /team_news`: call the model before taking the lock, map a rejection to 422 with its message, then continue through the existing validated update; keep the structured path unchanged and keep rejecting a request with neither a player and kind nor text.
- [x] 4.3 Remove the `FREE_TEXT_MESSAGE` "not available yet" behaviour and its tests; update the tool descriptions in `mcp_server.py` if they mention it.
- [x] 4.4 API tests with a fake pipeline or fake client: text injury removes the player and equals the button result; unknown player, other club and unclear text give 422 and change nothing; model off gives 422 with the unavailable message and structured news still works; `llm_used` is true with model explanations in the requested language and false on failure; XI identical with the model on and off; fan explanations have no `P(start)`; two identical predictions call the model once; news triggers new explanations; the model is called outside the news lock (a slow parse does not block another session).

## 5. Evaluation

- [x] 5.1 Create `lineup_oracle/evals.py` (`python -m lineup_oracle.evals`): the lineup score against the previous-match baseline over matchdays 3 to 10 and the parser accuracy with failures listed, skipped with a clear message when the model is off.
- [x] 5.2 Tests: the lineup score is deterministic and prints both scores and 48 club-matches on the seeded data; a match's own XI is never an input; the parser eval gives only the text and the club to the parser (fake client records its input and never sees `kind` or `player_name`); the parser eval is skipped when the model is off and the lineup eval still runs.

## 6. Docs

- [x] 6.1 Update ARCHITECTURE.md (Pipeline stages become stable, `predict_lineup` and `submit_team_news` contracts, MCP note, Evaluation section, environment variables), `backend/README.md` (settings, `--check`, evals) and the root README status table; keep the PLAN.md evals item accurate. Update CLAUDE.md commands only through a separate harness PR after merge.

## 7. Verify and approve

- [x] 7.1 Run the full suite (`cd backend && python -m pytest -q`) and fix any failure; run `python -m lineup_oracle.evals` and record the lineup scores in the PR notes.
- [ ] 7.2 If the user provides an endpoint and deployment: run `python -m lineup_oracle.llm --check`, the parser eval and one live predict in each of en, es and zh-Hant, and record the results; otherwise say plainly that the live model path is untested.
- [ ] 7.3 Human approval gate (HITL): stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR and merge it. Do not archive or merge before approval.
