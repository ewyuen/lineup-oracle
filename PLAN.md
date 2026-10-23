# Lineup Oracle: working plan (Microsoft x Premier League "Inside the Game" hackathon)

Status: implementation is complete and deployed. This plan now tracks hackathon submission readiness; it is not a statement that the project is still in design.

## Urgent actions (yours)
1. ~~Register before Oct 20, 2026, 12:00 PM PT.~~ Done.
2. ~~Email the sponsor (rules section 11.6).~~ Skipped by decision; the theme-fit risk was accepted.
3. Submit by **Oct 27, 2026, 11:59 PM PT**. Prioritize the demo video and project-page completion before the deadline.
4. ~~Make the code repository public.~~ Done: [ewyuen/lineup-oracle](https://github.com/ewyuen/lineup-oracle) is public.

Rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md

## Outstanding items
- [x] Build synthetic data/replay, P(start) scoring and XI optimization, the FastAPI service, Agent Framework pipeline, Razor/HTMX UI, evaluation, telemetry, CI, and Azure deployment.
- [x] Cut the unused MCP adapter and remove Antigravity/OpenCode workflow support; keep Claude Code and GitHub Copilot.
- [x] Update the root README with local setup and a feature walkthrough.
- [x] Make the GitHub repository public: https://github.com/ewyuen/lineup-oracle
- [ ] Review the public repository and its history for secrets, `.env`, `private/`, or real-person/club data before final submission.
- [x] Refresh the architecture diagrams and current deployment/UI notes in [ARCHITECTURE.md](ARCHITECTURE.md).
- [ ] Record a demonstration video under two minutes, showing the app running on its supported platform. Use only material you own or have permission to use; avoid third-party trademarks and copyrighted audio.
- [ ] Upload the video to an allowed public host and add the public video URL and repository URL to the hackathon project page.
- [ ] Save the project page and verify its required fields and links before the deadline.

## Who builds what (Copilot Pro is monthly: $10 of token-metered AI Credits, so use it sparingly)
| Tool | Does |
|---|---|
| Claude Code | OpenSpec proposals, spec review, the XI optimizer (SciPy MILP), the Agent Framework pipeline, final review of every change |
| Copilot agent mode | Data generator, FastAPI service, Razor/HTMX UI, Bicep files |
| Copilot completions (free) | Boilerplate while editing |

Rule: a tight OpenSpec task list is what lets a small model build reliably. Do not spend Copilot credits on the optimizer or agent wiring.
Check your usage on GitHub's billing page now and then. The legacy 300-premium-request plan applies only to annual plans.

## Design
- **Architecture:** see [ARCHITECTURE.md](ARCHITECTURE.md) for the implemented data, API, agent, UI, Azure, and evaluation flows.
- **Observability:** OpenTelemetry traces are exported to Application Insights in the Azure deployment.
- **Challenge focus:** Best Multi-Agent System; confirm the exact category label in the project form.
- **Demo (under 2 minutes):** select a fixture and club, inspect the predicted XI and explanations, apply an injury/doubt/suspension update, show the lineup change and news ticker, then switch the display language.

## OpenSpec workflow (Claude Code + GitHub Copilot)

Claude Code prepares and reviews the OpenSpec proposals and specifications. Copilot implements the approved task list, and Claude Code performs the final review. Both tools use the repository's OpenSpec workflow files: Claude commands and skills under `.claude/`, Copilot prompts and skills under `.github/`.

## Implemented OpenSpec changes

The planned implementation changes are complete, including the Azure deployment. The MCP adapter was subsequently removed as an unnecessary submission feature. Recent cleanup and documentation changes keep the repository focused on Copilot and Claude and make the local demo easier to evaluate.

## Risks
- Synthetic-data evaluation demonstrates the approach, not real-world prediction accuracy; state this clearly in the project description and video.
- The repository is public; complete the history/content review before relying on it as the submission repository.
- The project page and public demo video are the remaining submission deliverables; leave time to verify both URLs and save the form.
