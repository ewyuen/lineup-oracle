# Proposal

## Why

Every later stage (scoring, optimizer, agents, UI) needs data, and the hackathon rules (4.1, 4.7) require synthetic, football-realistic match events ingested "as they happen". Nothing exists yet, so this change supplies the data and the event stream that the rest of the pipeline consumes. It also keeps real people out of the repo: clubs and players are invented from a seed.

## What Changes

- A seeded roster generator writes a committed synthetic roster for 6 clubs, with no real input: invented names, shirt numbers, positions, coarse skill archetypes and a club tactical profile.
- A seeded generator produces about 10 matchdays of synthetic events (passes, shots, tackles, possession changes, pressure events, match metadata) plus team-news events (injury, suspension, late fitness doubt) before kick-off, each written as free text that names the club and player.
- A replay component emits those events in time order through an async stream with a replay-speed control, so downstream stages see events "as they happen".

## Capabilities

### New Capabilities
- `synthetic-roster`: invented clubs and players with real-like squad structure, archetype-based ratings and club style profiles, loadable from one swappable roster file.
- `synthetic-match-events`: deterministic (seeded) generation of match and team-news events with a stable, documented event schema.
- `event-replay`: time-ordered replay of generated events with adjustable speed.

### Modified Capabilities

## Impact

- New Python package under `backend/` (generator, replay, tests), a roster file under `backend/data/`.
- Adds `pytest` as a dev dependency. No Azure resources, no LLM calls, no UI in this change.
- Defines the event schema that the scoring, agent and UI changes depend on.
