# Tasks

## 1. Setup

- [x] 1.1 Create branch `feature/architecture-diagram-refresh` from `origin/main` and verify it is the active branch.

## 2. Refresh architecture documentation

- [x] 2.1 Update the system-context and Azure deployment Mermaid diagrams in `ARCHITECTURE.md` to represent the verified runtime and deployment boundaries; inspect both code paths and render or validate the Mermaid blocks.
- [x] 2.2 Correct stale deployment and UI-mode statements in `ARCHITECTURE.md` and verify they agree with the current deployment and Razor UI.
- [x] 2.3 Reconcile `PLAN.md` current status, completed cleanup/deployment work, and remaining submission checklist without rewriting unrelated historical decisions; verify each status against the repository and project page.

## 3. Verify

- [x] 3.1 Check Markdown links and Mermaid diagram syntax in the edited docs, run `openspec validate refresh-architecture-diagrams`, and confirm `git diff --check` succeeds.
- [x] 3.2 Run the full backend and UI test suites (`python -m pytest -q` from `backend/` and `dotnet test ui` from the repository root); confirm both pass.

## 4. Approval

- [x] 4.1 Stop for human approval after implementation and verification; approval received before archiving, opening the PR, and merging it.
