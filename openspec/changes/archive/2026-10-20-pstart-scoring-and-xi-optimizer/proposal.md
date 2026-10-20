## Why

The data change produces events and true XIs, but nothing yet turns them into a prediction. This change adds the deterministic core of the product: a transparent P(start) score per player and an optimizer that picks the best legal XI. The agent pipeline, API and UI all depend on it, and the LLM must never decide the XI.

## What Changes

- Add a P(start) score per player: a fixed weighted sum of squad quality for the player's position and how often the player started recently, multiplied by availability (out, doubt, available). No trained model.
- Add an XI optimizer: for each supported formation, a SciPy mixed-integer program picks the 11 players that maximize total P(start) with the right number of players per position. The final formation is the one with the best score after weighting by the club's formation prior.
- Return the formation, the 11 players with `p_start`, and up to two alternatives per position, so the explain stage and API can use them.
- Add a helper that builds a club's recent XIs from earlier `match_metadata` events.
- **Modify the generator** so the true XI favours higher-rated players. Today it draws starters uniformly at random from the available players, which gives a predictor nothing to learn. The data design already called for this ("position-weighted by a hidden starter-ness").
- Add `scipy` as a runtime dependency.

Contracts and components touched (from ARCHITECTURE.md): the "Pick XI" pipeline stage and its row in the pipeline-stages table, and the formation-prior open decision (resolved here). The match-metadata XI keeps its schema; only how it is drawn changes. The `predict_lineup` contract is not changed here; it is built on top of this in the API change.

## Capabilities

### New Capabilities
- `p-start-scoring`: transparent weighted P(start) per player from squad quality, recent starts and availability.
- `xi-optimizer`: per-formation MILP selection of the XI, formation choice by prior, and alternatives per position.

### Modified Capabilities
- `synthetic-match-events`: the true XI favours higher-rated players, so the data has a signal the predictor can find.

## Impact

- New code in `backend/lineup_oracle/` (scoring and optimizer modules) and tests in `backend/tests/`.
- `backend/pyproject.toml` gains the `scipy` dependency.
- Generator behavior changes (true XIs differ for the same seed). `backend/data/roster.json` does not change.
- ARCHITECTURE.md is updated in the same PR: the Pick XI stage detail and the formation-prior decision.
