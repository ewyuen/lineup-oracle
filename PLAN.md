# Lineup Oracle: working plan (Microsoft x Premier League "Inside the Game" hackathon)

Status: design agreed in the grill-me session. Final "shared understanding" confirmation still pending, so nothing is built yet.

## Urgent actions (yours)
1. ~~Register before Oct 20, 2026, 12:00 PM PT.~~ Done.
2. ~~Email the sponsor (rules section 11.6)~~ Skipped by decision; not asking the sponsor about theme fit.
3. Submit by **Oct 27, 2026, 11:59 PM PT**. Plan: freeze features Oct 25, video Oct 26, submit the morning of Oct 27.
4. ~~Create the new repo as **private**~~ Done (private repo created, files moved in). Still to do: make it **public before submitting**.

Rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md
(Not yet compared with aka.ms/insidethegame or the Reactor page.)

## Outstanding items
- [x] Decide: keep or cut Postgres. Cut: roster and events are files, history is in memory or SQLite if needed.
- [x] Decide: the MCP server's role. A thin adapter over the API with `predict_lineup`, `submit_team_news`, `list_matches` and `get_match_xi`; the agent pipeline does not call it (see ARCHITECTURE.md).
- [x] Add the new workflow tasks to `synthetic-data-and-replay` (branch, unit tests, HITL approval, ARCHITECTURE.md update).
- [ ] Write a UI wireframe (ASCII in ARCHITECTURE.md) before the UI change. Google Stitch brief is in `private/stitch-brief.md`; commit the chosen layout as ASCII (task 1.2 of `razor-htmx-ui`).
- [ ] Add OpenSpec tasks: evals (change 4), OpenTelemetry (change 6), team-news controls (changes 3 and 5).
- [ ] CI workflow on GitHub (run `pytest`, later `dotnet test` and a Bicep check): deferred, build it together with change 6 (Azure).
- [ ] Demo video task (Oct 26).
- [ ] Submission checklist: README, repo link, video, architecture diagram.
- [ ] Make the repo public before submission, and check no `.env`, `private/` or real names are in the history.
- [x] Merge the harness branches and push (PRs #1 to #3 merged).
- [x] Delete the merged harness branches, local and remote: `harness/agent-workflow-rules`, `harness/architecture-doc`, `harness/read-architecture-rule`.

## Who builds what (Copilot Pro is monthly: $10 of token-metered AI Credits, so use it sparingly)
| Tool | Does |
|---|---|
| Claude Code | OpenSpec proposals, spec review, the XI optimizer (SciPy MILP), the Agent Framework pipeline, final review of every change |
| Copilot agent mode, **small model** (e.g. GPT-5 mini; check current rates) | Data generator, MCP server, Razor/HTMX UI, Bicep files |
| Copilot completions (free) | Boilerplate while editing |

Rule: a tight OpenSpec task list is what lets a small model build reliably. Do not spend Copilot credits on the optimizer or agent wiring.
Check your usage on GitHub's billing page now and then. The legacy 300-premium-request plan applies only to annual plans.

## Design
- **Architecture:** see [ARCHITECTURE.md](ARCHITECTURE.md) (data, pipeline, prediction, model, backend, MCP, UI, Azure, evaluation).
- **Observability:** OpenTelemetry exported to App Insights (details in ARCHITECTURE.md). Wire it in the Azure change; pipeline spans may come earlier in the pipeline change.
- **Targets:** Best Multi-Agent System and Best Azure Cloud Native Integration.
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
- gpt-4.1-mini is confirmed available. Still make one structured-output call early to check the parser works.
- About 8 days solo with two languages, an MCP server and a UI is tight. Cut Event Hubs and the extras first.
- Time: about 6 days to the Oct 25 freeze, not 8. Each change needs implementation, tests, human approval, archive, PR and merge. If you slip, cut in this order: Azure polish, MCP server, Event Hubs, extra languages.
- New-repo rule: this repo already has history. Decide whether to move only the final files into the new repo. The official rules have not been read in full.
