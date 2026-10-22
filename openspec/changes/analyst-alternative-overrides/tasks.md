# Tasks

## 1. Branch Setup

- [ ] 1.1 Verify the active branch is `feature/analyst-alternative-overrides` (create it from `main` only if it does not already exist) and confirm with `git branch --show-current`

## 2. Backend Availability Kind

- [ ] 2.1 Store `(kind, seq)` in the feed's shared state and `State.availability`, derive status from `STATUS_OF_KIND`, and make `merge` return the winning kind; update `ingest.py`, `team_news`, `state.py`, `test_ingest.py` and `test_api.py`; add tests proving injury, doubt and suspension stay distinguishable through feed-versus-personal precedence, including a same-sequence tie; run `python -m pytest -q`

## 3. Backend Alternatives

- [ ] 3.1 Raise `ALTERNATIVES` to 4 in `optimizer.py`; update `test_api.py` (`<= 2`), `test_scoring_optimizer.py` and `backend/README.md`; run the focused optimizer and API tests
- [ ] 3.2 Add the overlay next to `pick` in `picking.py`: valid-selection filter, natural-then-manual ordering, the four-entry cap with no displacement (extra stored selections hidden), new alternatives and `facts` collections, and the `candidates` list; test a full list refusing a new selection, a doubtful player already natural, and that the stored prediction objects are not mutated
- [ ] 3.3 Add the `out` explanation branch to `explain.py`, the explainer instructions and `checks.failed_rules`; add `status` to `PlayerOut`; add tests for the template text, grounding, and model coverage of a manually included injured player
- [ ] 3.4 Add `State.selections` (copy-on-write, cleared by `State.reset()`) and `POST /alternatives` with the error contract in design Decision 1; add API tests for include and remove of an injured and a doubtful player, every 422 and 404 case, idempotent repeats, the unchanged XI and availability, isolation across sessions, matches and clubs, suspension after selection, recovery, promotion into the XI, and `lineup.source` for a selection-only session

## 4. UI Selection Flow

- [ ] 4.1 Add the alternative-selection client call and DTO fields (`status`, `candidates`), and localized analyst-mode HTMX controls for eligible candidates that show their status and keep the lineup fragment on errors; add UI tests for selection, removal, a full list refusing a selection with a message, suspension exclusion, fan mode without controls, and the same session cookie across a refresh; verify with `dotnet test ui/LineupOracle.sln --filter FullyQualifiedName~LineupUiTests`

## 5. Documentation and Integration

- [ ] 5.1 Update `ARCHITECTURE.md` with the `/alternatives` action, the `status` and `candidates` response fields, session-scoped behavior, the kind distinction and the four-alternative limit; verify no document still states a two-alternative limit
- [ ] 5.2 Run the full backend suite with `python -m pytest -q` from `backend/` and the full UI suite with `dotnet test ui/LineupOracle.sln`; confirm both pass
- [ ] 5.3 Stop for human approval after implementation and tests pass; only after explicit approval, archive the OpenSpec change, open a PR to `main`, and merge it
