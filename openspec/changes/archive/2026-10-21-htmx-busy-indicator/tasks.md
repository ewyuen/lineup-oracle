# Tasks

## 1. Setup

- [x] 1.1 Create or switch to `feature/htmx-busy-indicator` and verify `git branch --show-current` reports that branch.

## 2. Busy Status

- [x] 2.1 Add one localized, accessible HTMX busy indicator shared across fixture, club, favourite, language, team-news, and retry requests; add UI integration tests verifying it is announced while pending, content remains visible, and the status clears on success and error responses.
- [x] 2.2 Update `ARCHITECTURE.md` with the shared busy-status scope, accessibility behavior, and indeterminate progress contract; verify the UI section describes the implemented behavior.

## 3. Validation and Approval

- [x] 3.1 Run `dotnet test ui\LineupOracle.Ui.Tests\LineupOracle.Ui.Tests.csproj` and `python -m pytest -q` from `backend`; verify both suites pass.
- [ ] 3.2 Stop for human approval after tests pass; after approval, archive this OpenSpec change, create a PR to `main`, and merge only after the approval gate.
