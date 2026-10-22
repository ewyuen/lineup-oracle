# Tasks

## 1. Branch Setup

- [ ] 1.1 Verify the active branch is `feature/analyst-alternative-overrides` (create it from `main` only if it does not already exist) and confirm with `git branch --show-current`

## 2. Backend Availability and Alternative Overrides

- [ ] 2.1 Preserve the originating news kind with shared-feed and session availability while keeping latest-sequence precedence; add backend tests proving injury, doubt, and suspension remain distinguishable and run the focused API/feed tests
- [ ] 2.2 Implement session/match/club-scoped include/remove alternative selection and eligible-candidate response data; keep the XI and availability unchanged, enforce the four-player cap and deterministic lowest-ranked displacement, and add API tests for add, remove, suspension rejection, persistence, isolation, and unchanged XI; verify with focused backend tests

## 3. UI Selection Flow

- [ ] 3.1 Add the alternative-selection API client contract and localized HTMX controls for eligible injured/doubtful candidates, displaying their status and preserving the lineup fragment on errors; add UI tests for selection, removal, four-player behavior, suspension exclusion, and session context; verify with `dotnet test ui/LineupOracle.sln --filter FullyQualifiedName~LineupUiTests`

## 4. Documentation and Integration

- [ ] 4.1 Update `ARCHITECTURE.md` with the API response and action, session-scoped behavior, status-kind distinction, and four-alternative UI; verify the documented contracts no longer state a two-alternative limit
- [ ] 4.2 Run the full backend suite with `python -m pytest -q` from `backend/` and the full UI suite with `dotnet test ui/LineupOracle.sln`; confirm both pass
- [ ] 4.3 Stop for human approval after implementation and tests pass; only after explicit approval, archive the OpenSpec change, open a PR to `main`, and merge it
