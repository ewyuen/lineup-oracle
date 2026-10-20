# Lineup Oracle: working plan (Microsoft x Premier League "Inside the Game" hackathon)

Status: design agreed in the grill-me session. Final "shared understanding" confirmation still pending, so nothing is built yet.

## Urgent actions (yours)
1. Register before **Oct 20, 2026, 12:00 PM PT**.
2. Email the sponsor (rules section 11.6): "Does a lineup predictor built on a synthetic event pipeline fit the theme?"
3. Submit by **Oct 27, 2026, 11:59 PM PT**. Plan: freeze features Oct 25, video Oct 26, submit the morning of Oct 27.
4. Create the new public repo AFTER registering (rules require a project newly created after registration). Move this file and `openspec/` into it.

Rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md
(Not yet compared with aka.ms/insidethegame or the Reactor page.)

## Who builds what (Copilot Pro is monthly: $10 of token-metered AI Credits, so use it sparingly)
| Tool | Does |
|---|---|
| Claude Code | OpenSpec proposals, spec review, the XI optimizer (SciPy MILP), the Agent Framework pipeline, final review of every change |
| Copilot agent mode, **small model** (e.g. GPT-5 mini; check current rates) | Data generator, MCP server, Razor/HTMX UI, Bicep files |
| Copilot completions (free) | Boilerplate while editing |

Rule: a tight OpenSpec task list is what lets a small model build reliably. Do not spend Copilot credits on the optimizer or agent wiring.
Check your usage on GitHub's billing page now and then. The legacy 300-premium-request plan applies only to annual plans.

## Design
- **Data:** all synthetic. A seeded Python generator emits match events plus injury and suspension events. 6 clubs, about 10 matchdays, and a swappable roster file. Clubs and players are invented aliases that keep the real squad structure and use skill archetypes. The real-to-synthetic mapping stays private and gitignored. No crests, logos or photos.
- **Pipeline:** Microsoft Agent Framework only. Events replay through an in-process async queue with a speed control (Event Hubs only if time is left). Stages: ingest, interpret, pick the XI, explain, personalize.
- **Prediction:** P(start) is a transparent weighted score with no trained model. A SciPy MILP runs once per formation, weighted by the club's formation prior. Deterministic code picks the XI. The LLM only parses team news and writes explanations. If the LLM fails, the XI still returns with a template explanation.
- **Model:** gpt-4.1-mini on Foundry, deployment name in an environment variable.
- **Backend:** FastAPI (Python) returns formation, 11 players with P(start), alternatives per slot, and explanations as JSON. Postgres for storage.
- **MCP:** a small server exposing `predict_lineup`, built with Copilot.
- **UI:** ASP.NET Razor Pages + HTMX, an SVG pitch, a live event feed and an explanation panel. Modes are analyst and casual fan, with a favourite-club selector, in English, Spanish and Traditional Chinese.
- **Azure:** Container Apps (two services), Postgres, Foundry, App Insights, Bicep. Secrets in Container Apps secrets and an uncommitted `.env`, managed identity where possible, a budget alert on the account.
- **Targets:** Best Multi-Agent System and Best Azure Cloud Native Integration.
- **Evaluation:** correct starters out of 11 versus a "same XI as last match" baseline, on held-out synthetic matches. It proves the pipeline works, not real-world accuracy. Say so in the demo.
- **Demo (under 2 minutes):** pick a fixture, see the predicted XI with explanations, inject a late injury, watch the XI update, then switch language and fan mode.

## OpenSpec changes (one per step; Claude Code proposes, Copilot builds, Claude Code reviews)
1. Data generator and event replay.
2. P(start) scoring and XI optimizer.
3. FastAPI service and MCP server.
4. Agent pipeline and LLM explanations.
5. Razor/HTMX UI.
6. Azure deployment (Bicep).

## Risks
- A pre-match predictor is not named in the rules. Theme fit (Stage 1, pass/fail) depends on the sponsor's reply.
- gpt-4.1-mini availability in your region and account is unconfirmed. Make one structured-output call after deploying.
- About 8 days solo with two languages, an MCP server and a UI is tight. Cut Event Hubs and the extras first.
- Do not commit the real-to-synthetic name mapping.
