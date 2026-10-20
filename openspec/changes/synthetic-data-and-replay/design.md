# Design

## Context

Greenfield repo: no code yet. See proposal.md for why. Python backend lives in `backend/`; the Razor UI (`ui/`) and Bicep (`infra/`) come in later changes. The event schema defined here is the contract for scoring, agents and UI, so it must be stable and simple. Built by Copilot with a small model, so tasks and structures stay plain.

## Goals / Non-Goals

**Goals:**
- Reproducible synthetic data from one seed.
- A roster file that can be swapped without code changes.
- Replay usable both live (demo) and instantly (tests).

**Non-Goals:**
- Real data, video, or an auto-eventing model.
- Event Hubs or any external broker (later, only if time allows).
- Modelling football physics. Distributions only need to look plausible.

## Decisions

- **Layout:** `backend/src/lineup_oracle/{roster,events,replay}.py`, tests in `backend/tests/`, data in `backend/data/roster.json`. Alternative: one big module. Rejected, because separate files map to the three capabilities.
- **Event schema:** one flat JSON object per event: `id`, `match_id`, `type`, `minute` (float), `club`, `player` (nullable), `payload` (dict), `simulated` (true). Plain dataclasses and JSON Lines on disk. Alternative: Pydantic models. Deferred to the FastAPI change, where they are needed anyway.
- **Determinism:** one `random.Random(seed)` passed through the generator, never the global RNG. Alternative: numpy generators. Rejected as an extra dependency.
- **Generation model:** per match, draw an actual XI from available players (position-weighted by a hidden "starter-ness" derived from the archetype and recent minutes), then draw event counts per team from Poisson-like distributions scaled by team style, and distribute them over minutes. This keeps the "true" XI known, which the evaluation change needs as ground truth.
- **Team news:** emitted at fixed offsets before kick-off (for example 48 h, 24 h, 1 h) and simulated; an unavailable player is excluded from the true XI.
- **Roster aliasing:** a script `backend/tools/alias_roster.py` reads `private/real_roster.csv` (club, number, position, role) and writes the synthetic `roster.json` and `private/mapping.json`. Names come from seeded syllable lists. A generated name is rejected if it appears in the private real-name list. Ratings come from archetype templates plus seeded noise. Only `roster.json` is committed.
- **Replay:** an async generator over a time-sorted list with a virtual clock; `speed=0` skips waiting. Subscribers get their own `asyncio.Queue` fed by one pump task. Late events go into a heap so ordering holds. Alternative: a message broker. Rejected for the hackathon scope.

## Risks / Trade-offs

- [Synthetic data looks fake] → Check plausible ranges in a test and tune distributions by eye on a few matches.
- [Real roster input is not available when building] → Provide a tiny fake `private/real_roster.csv` template so the script and tests run without real data.
- [Name collisions or look-alikes with real names] → Reject exact matches only; review a sample of names by hand before publishing.
- [Event schema changes later] → Keep it flat and versioned with a `schema_version` field in match metadata.
