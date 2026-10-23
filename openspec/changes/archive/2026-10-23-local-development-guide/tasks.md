# Tasks

## 1. Setup

- [x] 1.1 Create branch `feature/local-development-guide` from `origin/main` and verify it is the active branch.

## 2. Update the README

- [x] 2.1 Replace the abbreviated local run section with Windows PowerShell prerequisites, backend virtual-environment installation, API startup, separate UI startup, and a health check; verify paths and ports against `backend/pyproject.toml` and the UI launch settings.
- [x] 2.2 Add a feature walkthrough for fixture/club selection, lineup and explanations, structured team-news actions, the news ticker, and language selection; verify each described control exists in the current UI.
- [x] 2.3 Explain optional model configuration and the deterministic/template fallback, correct the UI/Azure status, and retain the synthetic-data/evaluation caveat; verify `.env.example` settings and project state.

## 3. Verify

- [x] 3.1 Run `python -m pytest -q` from `backend/` and `dotnet test ui` from the repository root; confirm both suites pass.
- [x] 3.2 Run `openspec validate local-development-guide` and confirm the documentation-only change validates.

## 4. Approval

- [ ] 4.1 Stop for human approval after verification; only after approval, archive the OpenSpec change, open a PR from `feature/local-development-guide` to `main`, and merge it.
