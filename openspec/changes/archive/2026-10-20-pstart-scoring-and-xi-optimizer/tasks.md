## 1. Setup

- [x] 1.1 Confirm you are on the existing branch `feature/pstart-scoring-and-xi-optimizer` (do not create another) and merge main in if PR #9 has been merged.
- [x] 1.2 Add `scipy` to `backend/pyproject.toml` dependencies and install it.

## 2. P(start) scoring

- [x] 2.1 Create `backend/lineup_oracle/scoring.py` with the constants (weights, rating mix per position, doubt factor, neutral recent share) and a `quality(player)` function.
- [x] 2.2 Add `recent_xis(events, club, before_match_id_or_matchday)` returning earlier XIs oldest first, from `match_metadata` events only.
- [x] 2.3 Add `p_start_scores(roster_club, recent_xis, availability)` returning a score per player id.
- [x] 2.4 Unit tests: score range 0 to 1; better ratings score higher; more recent starts score higher; no history uses the neutral share; out is 0; doubt is half; only earlier matchdays used; same inputs give identical output.

## 3. XI optimizer

- [x] 3.1 Create `backend/lineup_oracle/optimizer.py` with `solve_formation(club, scores, formation)` using `scipy.optimize.milp`, id-based tie-breaking, out players excluded.
- [x] 3.2 Add `pick_xi(club, scores)` that solves all six formations, applies the prior (1.0 usual, 0.85 other), skips infeasible ones and raises an error naming the club if none fits.
- [x] 3.3 Add alternatives per position (two best non-out, non-picked players).
- [x] 3.4 Unit tests: position counts for each formation; out players never picked; best players picked; MILP result equals a greedy per-position reference; usual formation wins when close; injuries force another formation and the XI stays legal; alternatives are bench players of the same position; error names the club when too few players; ties go to the lower id and repeat runs match.

## 4. Generator change

- [x] 4.1 Change `_pick_true_xi` in `events.py` to weighted sampling without replacement (weight `quality ** 4`), keeping the single seeded RNG.
- [x] 4.2 Unit tests: same seed gives identical XIs; over a generated season the top-third players by rating start more matches on average than the bottom third; all existing synthetic-data tests still pass (update expectations that depended on the old uniform draw, and say so).

## 5. Docs

- [x] 5.1 Update ARCHITECTURE.md in this PR: the Pick XI stage detail (score formula, formation prior 1.0/0.85, alternatives) and mark the formation-prior open decision as resolved.
- [x] 5.2 Add a short section to `backend/README.md` on scoring and the optimizer, and update CLAUDE.md's repo state if it changes.

## 6. Verify and approve

- [x] 6.1 Run the full backend suite (`cd backend && python -m pytest -q`) and fix any failure.
- [x] 6.2 Human approval gate (HITL): stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR and merge it. Do not archive or merge before approval.
