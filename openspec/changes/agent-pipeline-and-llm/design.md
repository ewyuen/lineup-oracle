## Context

See proposal.md for why. Today `api.py` builds every lineup with scoring, the optimizer and template explanations (`explain.py`); `POST /team_news` rejects `text`. ARCHITECTURE.md already fixes the shape: Interpret, Pick XI, Explain, Personalize, with the LLM only parsing news and writing explanations, and the XI returned even if the LLM fails. The rules in `openspec/config.yaml` allow Microsoft Agent Framework only (no LangGraph or AutoGen); `agent-framework-core` and `agent-framework-openai` 1.x are on PyPI (checked: `Agent(client, instructions, name=...)`, `agent.run(messages, options=...)`, and an OpenAI chat client that takes an Azure endpoint, a model or deployment name, an API key or an Azure credential). No LLM credentials exist on this machine yet; the live model is gpt-4.1-mini on Foundry, deployment name from an environment variable.

## Goals / Non-Goals

**Goals:**
- Free-text news moves the XI through a parser that code checks.
- Explanations in en, es and zh-Hant and in analyst or fan style, written by the model from computed facts.
- The API never fails or changes the XI because of the model.
- An evaluation that shows the pipeline against a baseline.

**Non-Goals:**
- Telemetry (change 6), streaming replay into the pipeline, new scoring, a second model, persisting anything.

## Decisions

- **Two agents, one deterministic orchestrator.** `agents.py` builds a News Parser agent and an Explainer agent with Agent Framework's `Agent`. `pipeline.py` runs the stages in plain async Python (Interpret, Pick XI, Explain, Personalize) and owns every branch and fallback. Alternative: an Agent Framework `WorkflowBuilder` graph. Rejected for now, because the fallbacks are easier to read and test in code; wrapping the same stages in a workflow is a stretch task only if time remains.
- **The model sits behind one small seam.** `llm.py` reads settings and builds the chat client; the agents take a client object. Tests pass a fake client that returns canned answers, so no test needs a network or credentials. Alternative: mock HTTP. Rejected, as it ties tests to the transport.
- **Config from the environment:** `LINEUP_LLM_ENDPOINT`, `LINEUP_LLM_DEPLOYMENT`, optional `LINEUP_LLM_API_KEY` (otherwise Azure default credentials, which is the managed identity on Azure), and `LINEUP_LLM_TIMEOUT` seconds (default 15). The model is on only when endpoint and deployment are both set. Unset means off: templates, and text news rejected with the unavailable message.
- **Parser:** the agent gets the club's roster (id, name, number, position) and the text, and answers a pydantic model `{club, player_id, kind}` as structured output. Code then checks that the club equals the requested club, that `player_id` is in that roster and that `kind` is one of the three; any other answer is a rejection with a specific message. Only the validated player id and kind leave the parser. The structured availability then follows the existing `team_news` path (same lock, same state update), so text and button news give the same result.
- **Explainer:** one call per prediction. Input is a list of facts computed by code for the 11 players and the alternatives (id, name, position, p_start, starts, played, status, strongest rating) plus mode and language; the answer is `{explanations: [{id, text}]}`. The prompt says: one sentence, use only the facts, fan mode has no numbers or percentages, write in the language. Code accepts it only if the ids match the lineup exactly, texts are non-empty, at most 200 characters, and fan texts contain no `%` or "P(start)". Anything else counts as a failure and the template path runs for the whole lineup (no mixing).
- **Template fallback keeps English.** The template in `explain.py` gets a mode argument: analyst unchanged, fan drops the `P(start)` clause (the UI hides numbers in fan mode, so the old template would leak one).
- **Cache:** an in-memory dict keyed by a hash of the facts JSON (which includes mode and language), bounded to 256 entries with oldest-first eviction. Same lineup, same mode, same language gives the same text without a model call. `# shortcut:` comment: per-process cache, lost on restart.
- **Async from sync endpoints:** the API endpoints stay plain `def`. The pipeline owns one long-lived event loop on a dedicated thread and runs each model call with `run_coroutine_threadsafe(...).result(timeout)`. This avoids creating a loop and client per request, and mirrors the single solver thread already used for HiGHS. A timeout counts as a model failure.
- **API wiring:** `create_app(state=None, pipeline=None)`; the default pipeline is built from the environment. `_lineup` computes the XI as today, asks the pipeline for explanations, and on `None` uses the templates. `llm_used` is the pipeline's answer, not a constant. `team_news` with `text` and no player or kind calls `pipeline.interpret`, maps rejection to 422 with its message, then continues through the existing validated update under the same lock. The model call happens before the lock is taken so a slow call does not block other sessions' news.
- **Evaluation:** `python -m lineup_oracle.evals` runs two checks. (1) Lineup score: for matchdays 3 to 10 (at least two earlier matches of history), each club in each match, apply that match's recorded team news as structured availability (labels `kind` and `player_name`, mapped to ids), predict, and count how many of the true 11 are in the predicted XI; the baseline is the club's previous match XI. Prints mean correct out of 11 for both and the number of club-matches (48 with the seeded data). No model needed. (2) Parser accuracy: with the model configured, parse every team-news event from `payload.text` and the club only, compare to the labels, print the share correct and the failures; without it, print that it was skipped. Alternative: write the labels into the parser input. Rejected, since it would make the score meaningless.
- **Dependencies:** `agent-framework-core`, `agent-framework-openai` and `azure-identity` in `pyproject.toml`; the meta package `agent-framework` pulls many unused extras.

## Risks / Trade-offs

- [No credentials here, so the live structured-output call is unverified] → An early task runs one real call (`python -m lineup_oracle.llm --check`) once the user supplies an endpoint and deployment; all other tests use the fake client. Until then the model path is covered by fake-client tests only.
- [Agent Framework 1.x API details differ from the docs the plan assumed] → Keep its use inside `llm.py` and `agents.py`, so a change touches two files.
- [Model latency on each prediction slows the demo] → One batched call, caching, and a timeout with the template fallback; the UI keeps the last XI while waiting.
- [The model writes a wrong or off-language sentence] → Facts-only prompt, code validation of shape, and fan-mode number check; wording is not otherwise verified (accepted).
- [Parser mistakes a player with a shared surname] → The roster list in the prompt carries ids and numbers, and code rejects ids outside the club; a wrong in-club player is possible and is reported by the parser eval.
- [Cost of the eval on the model] → About 60 short calls per run, run on demand only.
- [Free text is the demo's headline flow but depends on credentials at demo time] → The structured buttons keep working with no model, so the demo degrades instead of breaking.
