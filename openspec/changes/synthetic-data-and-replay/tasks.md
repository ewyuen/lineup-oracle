# Tasks

## 0. Branch

- [x] 0.1 Create the feature branch `feature/synthetic-data-and-replay` from main

## 1. Backend scaffold

- [x] 1.1 Create `backend/` with `pyproject.toml` (Python 3.12, pytest dev dependency) and the package `lineup_oracle`; verify `pytest` runs and reports zero tests collected without error
- [x] 1.2 Add `private/` and `.env` to `.gitignore` if missing and verify `git check-ignore private/x` prints the path

## 2. Synthetic roster

- [ ] 2.1 Define roster dataclasses and a loader with the validation in the roster spec; verify unit tests cover duplicate shirt numbers, a missing position and a valid roster
- [ ] 2.2 Write `backend/tools/alias_roster.py` and a fake `private/real_roster.csv.example` (no real names); verify running it with a seed writes `backend/data/roster.json` and `private/mapping.json`
- [ ] 2.3 Add a test that the committed roster contains no name from the private real-name list and that regenerating with the same seed gives an identical file
- [ ] 2.4 Generate the real 6-club roster file once from your private input and verify it loads through 2.1 with at least 20 players per club

## 3. Synthetic events

- [ ] 3.1 Implement fixtures for about 10 matchdays; verify a test that each club plays once per matchday and each matchday has 3 matches
- [ ] 3.2 Implement team-news events with seeded free-text templates (club and player named in `payload.text`) and true-XI selection; verify tests that no injured or suspended player is in the true XI, that each text names a player of its club, and that texts are identical for the same seed
- [ ] 3.3 Implement per-match event generation with the schema in design.md; verify tests for event fields, 11 distinct starters per club, and identical output for the same seed
- [ ] 3.4 Add the plausibility test (100 matches: mean passes 300 to 600, mean shots 8 to 20); verify it passes and tune distributions if not
- [ ] 3.5 Add `python -m lineup_oracle.events --seed N --out backend/data/events.jsonl` and document the command and schema in `backend/README.md`; verify the documented command runs as written

## 4. Event replay

- [ ] 4.1 Implement the ordered async replay with speed factor and instant mode; verify tests for ordering and for speed 0 delivering everything immediately
- [ ] 4.2 Add late event injection; verify a test that an injected injury arrives before later-scheduled events
- [ ] 4.3 Add multi-subscriber delivery; verify a test where two subscribers see identical sequences
- [ ] 4.4 Verify a 90-minute match replays in under 2 minutes at the demo speed and document the speed option in `backend/README.md`

## 5. Wrap-up

- [ ] 5.1 Run the full test suite and `openspec validate synthetic-data-and-replay`; verify both pass
- [ ] 5.2 Compare the implemented event schema with ARCHITECTURE.md and update ARCHITECTURE.md in this branch if they differ; verify the schema table matches `design.md` and the code
- [ ] 5.3 Human approval gate: summarize test results and stop for user approval; after approval run `/opsx:archive`, then open a PR from this branch to main and merge it
