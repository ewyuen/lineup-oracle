# Proposal

## Why

Injured players, and doubtful players who do not rank in the top two, are excluded from the alternatives the analyst can inspect, even when the coach wants to keep them visible as possible options. Analysts need a manual alternatives override that does not claim the player is fit or change the deterministic starting XI.

## What Changes

- Let an analyst explicitly include a non-starting injured or doubtful player in the alternatives for their position, without clearing that player's status or changing the starting XI.
- Exclude suspended players from this override.
- Show up to four alternatives per position (the optimizer's natural list grows from two to four). A manual selection is refused with a message when the position's list is already full; nobody is pushed out.
- Give manually included players an explanation and a visible status, and add a status to every returned player.
- Keep manual selections scoped to the browser session, match, and club until changed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `xi-optimizer`: List up to four alternatives per position instead of two.
- `lineup-api`: Return up to four alternatives and support session-scoped analyst selections of eligible injured or doubtful players while preserving status and XI.
- `lineup-ui`: Let the analyst select eligible players for alternatives and reflect the API's updated list without a full-page reload.

## Impact

This changes the prediction API and its in-memory session state, including how team-news kind is retained to distinguish injury from suspension. It affects the optimizer constant, backend picking, explanations and grounding checks, API tests, `backend/README.md`, the Razor Pages/HTMX lineup and localization resources, UI tests, and `ARCHITECTURE.md`. No new dependencies or persistence service are needed.
