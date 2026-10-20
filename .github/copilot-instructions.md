# Copilot instructions

Lineup Oracle: hackathon project. Design is in `PLAN.md`; work is driven by OpenSpec changes in `openspec/changes/`. Read the change's `tasks.md` and stay within it. Do not add features or abstractions it doesn't ask for.

Hard rules:
- All data is synthetic: invented club and player names, no real names, crests, logos or photos.
- Never commit `.env` or `private/` (holds the real-to-synthetic mapping). No secrets in code.
- Agent pipeline uses Microsoft Agent Framework only. No LangGraph or AutoGen.
- Deterministic code picks the XI. The LLM only parses team news and writes explanations. The API must still return an XI, with a template explanation, if the LLM call fails.
- The model deployment name comes from an environment variable. Never hardcode it.
- Backend is Python (FastAPI). UI is ASP.NET Razor Pages + HTMX.
- Every change includes unit tests, is built on a branch `feature/<change-name>` (never main), and stops for human approval after tests pass. Once approved, run the OpenSpec archive, then create a PR and merge it; never archive or merge before approval.
- Harness changes (agent instructions, OpenSpec config, skills, prompts) go on `harness/<name>`, merged to main by PR. Feature branches also merge to main, never into each other.
