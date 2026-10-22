# Tasks

## 1. Manual restart behavior

- [x] 1.1 Create feature branch `feature/clear-personal-news-on-manual-restart`; verify `git branch --show-current` returns that branch. The branch was created for this proposal.
- [x] 1.2 Update the manual restart path to clear all session-scoped availability and alternatives (`State.reset()`) in `Feed.restart()` while synchronizing state before feed locks; keep automatic loop resets unchanged and release locks before the first item is processed. Verify with focused restart tests.
- [x] 1.3 Add backend regression tests proving manual restart clears availability across sessions, automatic loop reset preserves it, the first feed item is still delivered immediately, a submission completed before the restart is cleared and one made after it is kept, and `restart()` waits for a held state lock and then finishes (timeout, no deadlock). Run the focused tests with `python -m pytest -q -k "restart or availability"` from `backend/`.
- [x] 1.4 Update `ARCHITECTURE.md` to distinguish manual and automatic reset behavior; verify the News feed and personal-news contract documents both paths accurately.

## 2. Validation and approval

- [x] 2.1 Run the full backend test suite with `python -m pytest -q` from `backend/` and confirm it passes.
- [x] 2.2 Stop for human approval after tests pass. Only after approval, archive the OpenSpec change, create a PR from this feature branch to `main`, and merge it after approval.
