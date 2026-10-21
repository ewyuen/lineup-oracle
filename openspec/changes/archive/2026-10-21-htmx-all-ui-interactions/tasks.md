# Tasks

## 1. Setup

- [x] 1.1 Create and switch to `feature/htmx-all-ui-interactions`; verify `git branch --show-current` reports the feature branch.

## 2. Fixture and Club Selection

- [x] 2.1 Convert fixture and club selection to HTMX requests and a shared server-rendered workspace update; add UI integration tests verifying selection state, dependent controls, lineup, partial-only response, and browser URL behavior.
- [x] 2.2 Preserve the last successful selection and lineup on rejected or unavailable predictions, and make retry target the attempted selection; add integration tests for error message, retained view, and successful retry.

## 3. Preferences and UI Consistency

- [x] 3.1 Convert favourite-club updates to HTMX while preserving the cookie and active-club behavior; add integration tests for the favourite marker, selected club, updated lineup, and non-HTMX fallback.
- [x] 3.2 Convert language changes to HTMX while preserving the language cookie, request culture, selected fixture/club, and translated content; add integration tests for English, Spanish, and Traditional Chinese responses and non-HTMX fallback.
- [x] 3.3 Verify team-news presets, free-text news, and retry remain asynchronous and preserve anti-forgery and error behavior; add or update integration tests for returned fragments and dynamically swapped controls.
- [x] 3.4 Update `ARCHITECTURE.md` with the HTMX request, fragment, browser-history, error-preservation behavior, and future in-page interaction convention; verify its UI section matches the implemented interactions and states the navigation/download exception.

## 4. Validation and Approval

- [x] 4.1 Run the full UI test suite with `dotnet test ui\LineupOracle.Ui.Tests\LineupOracle.Ui.Tests.csproj` and the backend suite with `python -m pytest -q` from `backend`; verify both pass.
- [ ] 4.2 Stop for human approval after tests pass; after approval, archive this OpenSpec change, create a PR to `main`, and merge only after the approval gate.
