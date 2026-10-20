## Context

See proposal.md for why. The roster (`roster.py`), the generator (`events.py`) and replay already exist. This change adds the deterministic pick stage. It is plain Python with no I/O: no database (Postgres is cut), no LLM. Inputs are the roster, earlier `match_metadata` events and an availability map; the output is a formation plus 11 players with `p_start` and alternatives. The API change (change 3) wraps it.

## Goals / Non-Goals

**Goals:**
- A transparent score a reader can recompute by hand.
- A legal, deterministic XI for any club, including with injuries.
- A true XI in the generated data that carries a learnable signal.

**Non-Goals:**
- A trained model, or tuning weights against the eval (the eval is change 4).
- The API shape, explanations and parsing of team news.
- Per-slot positions (left back, striker). Positions are GK, DEF, MID, FWD, as in the roster.

## Decisions

- **Layout:** `backend/lineup_oracle/scoring.py` (P(start), recent XIs) and `optimizer.py` (MILP, formation choice, alternatives). Alternative: one module. Rejected, since they map to the two capabilities and the pipeline calls them separately.
- **Score:** `p_start = availability * (0.7 * quality + 0.3 * recent_share)`. `quality` is the mean of the player's position-relevant ratings divided by 100 (GK: defending and passing; DEF: defending, pace, passing; MID: passing, dribbling, defending; FWD: shooting, pace, dribbling). `recent_share` is starts in the last 5 matches divided by matches played, 0.5 when there is no history. Availability is 1.0, 0.5 (doubt) or 0. The weights and the rating mix are constants at the top of `scoring.py`. Assumption: these values are a first guess, to be tuned only if the eval shows a problem.
- **Recent XIs:** a function over `match_metadata` events returns a club's XIs from earlier matchdays, oldest first. The caller passes the events, so the module stays pure and works the same for the replay and the API.
- **Optimizer:** `scipy.optimize.milp` with one binary variable per player, maximizing the sum of `p_start`. Constraints: exactly 1 GK, and DEF, MID and FWD counts from `_formation_counts` (reused from `events.py`). Out players (score 0) are excluded from the variables, so a shortage makes the problem infeasible instead of picking them. Alternative: a greedy sort per position. It gives the same answer for this problem, but the hackathon pitch and PLAN.md call for the MILP, and it keeps room for cross-position rules. The MILP is kept, and a test checks it against the greedy answer.
- **Ties:** players are sorted by id and a tiny id-based epsilon is subtracted from each objective weight, so equal scores resolve to the lower id on every run.
- **Formation choice:** solve all six formations, score = total `p_start` times the prior, choose the maximum. Prior 1.0 for the club's usual formation (from the roster) and 0.85 for any other. Infeasible formations are skipped. If all are infeasible, raise an error naming the club. Assumption: 0.85 is a first guess.
- **Alternatives:** per position, the two highest non-out, non-picked players by `p_start` (ties by id).
- **Generator change:** `_pick_true_xi` draws each slot by weighted sampling without replacement, with weight `quality ** 4` (same quality formula as the score, imported from `scoring.py`). The power makes better players start clearly more often but not always. The same seeded RNG is used, so output stays deterministic. The roster is unchanged. The committed `events.jsonl` is gitignored, so only tests are affected.
- **Dependency:** `scipy` in `backend/pyproject.toml`. Alternative: write a small solver. Rejected, since SciPy is already named in the plan.

## Risks / Trade-offs

- [Quality-weighted XI makes the "same XI as last match" baseline strong] → That is realistic and the eval compares honestly. The `**4` exponent is one constant to adjust.
- [Generator and score share the quality formula, so the predictor looks better than it is] → Accepted: the eval shows the pipeline works, not real-world accuracy (ARCHITECTURE.md). Recent starts and availability still add information the quality alone lacks.
- [Hand-picked weights and prior] → Constants in one place with tests on their effects, not on exact values.
- [SciPy install size in the container image] → Small enough for the hackathon.
