## Why

The XI is picked by deterministic code, but nothing yet reads free-text team news, and explanations are fixed English templates. The demo needs a late news line typed or generated as text to move the XI, explanations in the chosen language and mode, and a measured result. This change adds the LLM parts, built as a small multi-agent pipeline on Microsoft Agent Framework (the "Best Multi-Agent System" target), without ever letting the LLM choose the XI.

## What Changes

- Add a pipeline of stages built on Microsoft Agent Framework: Interpret (a News Parser agent), Pick XI (existing scoring and optimizer, unchanged), Explain (an Explainer agent), Personalize. A deterministic orchestrator runs the stages and owns every decision.
- **News Parser agent:** turns a free-text team-news line into one structured submission (player id and kind). Code validates the answer against the club's roster; an unknown player, a different club, or an unclear line is rejected with a message and the XI is unchanged.
- **Explainer agent:** writes one short explanation per picked player in the requested language (en, es, zh-Hant) and mode (analyst with numbers, fan plain), from facts computed by code. One batched call per prediction, cached.
- **Fallback:** if the LLM is not configured, errors, times out or returns an invalid answer, the XI is still returned with the English template explanations and `llm_used` false. Free text is then rejected with a clear message.
- `POST /team_news` accepts free `text` (replacing the "not available yet" rejection); `llm_used` becomes true when the LLM wrote the explanations; `mode` and `language` now change the explanations.
- Fan mode template explanations stop showing `P(start)` numbers (the UI hides numbers in fan mode, and the current template would leak one).
- Add an evaluation command: parser accuracy on the generated team-news events (against their answer labels), and the starters-correct-out-of-11 score of the pipeline versus the "same XI as last match" baseline on held-out matches.
- LLM settings come from environment variables (endpoint, deployment name, optional key, otherwise Azure identity); with none set, the LLM is off and everything else works.

Contracts and components touched (from ARCHITECTURE.md): the Pipeline section and the "Pipeline stages" contract (draft becomes stable), `predict_lineup` (`llm_used`, `mode`, `language` now have effect), `submit_team_news` (free text accepted), the MCP tool descriptions (free text now works; no code change in the adapter), and the Evaluation section. No change to the event schema.

Out of scope: OpenTelemetry and App Insights (change 6), streaming replay into the pipeline (the API keeps reading state directly), changing the scoring or optimizer, Event Hubs, a model other than the configured one, translating the page text (the UI does that), persistent caches.

Assumptions to confirm: a Foundry `gpt-4.1-mini` deployment (endpoint plus key or identity) is available for the live check and the parser eval; automated tests use a fake model and need no network. No credentials are present on this machine today.

## Capabilities

### New Capabilities
- `team-news-parsing`: the News Parser agent, roster validation, rejection rules and the structured result.
- `llm-explanations`: the Explainer agent, languages and modes, validation of its output, caching and the template fallback.
- `lineup-evaluation`: the evaluation command (parser accuracy and the XI versus baseline score).

### Modified Capabilities
- `lineup-api`: predict reports `llm_used` truthfully and honours mode and language; template explanations become the fallback and drop numbers in fan mode; free-text team news is accepted (the "rejected for now" requirement is removed).

## Impact

- New modules in `backend/lineup_oracle/`: `llm.py` (settings and the Agent Framework client), `agents.py` (parser and explainer), `pipeline.py` (stages and orchestrator), `evals.py`; changes in `api.py` and `explain.py`.
- New dependencies: `agent-framework-core` and `agent-framework-openai` (1.x), plus `azure-identity`.
- Tests use a fake chat client, so the suite stays offline and deterministic.
- ARCHITECTURE.md, `backend/README.md` and the root README status table.
