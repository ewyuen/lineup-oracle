# Proposal

## Why

Injured players, and doubtful players who do not rank in the top two, are excluded from the alternatives the analyst can inspect, even when the coach wants to keep them visible as possible options. Analysts need a manual alternatives override that does not claim the player is fit or change the deterministic starting XI.

## What Changes

- Let an analyst explicitly include a non-starting injured or doubtful player in the alternatives for their position, without clearing that player's status or changing the starting XI.
- Exclude suspended players from this override.
- Show up to two alternatives per position total. A manually selected injured or doubtful player takes a spot from the lowest-ranked alternative; if manual selections exceed the two spots, the latest selection takes priority.
- Give manually included players an explanation and a visible status, and add a status to every returned player.
- Keep manual selections scoped to the browser session, match, and club until changed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `llm-explanations`: Explain listed players who are injured or unavailable truthfully, in templates and model output.
- `lineup-api`: Return up to two alternatives and support session-scoped analyst selections of eligible injured or doubtful players while preserving status and XI.
- `lineup-ui`: Let the analyst select eligible players for alternatives and reflect the API's updated list without a full-page reload.

## Impact

This changes the prediction API and its in-memory session state, including how team-news kind is retained to distinguish injury from suspension. It affects backend picking, explanations and grounding checks, API tests, the Razor Pages/HTMX lineup and localization resources, UI tests, and `ARCHITECTURE.md`. No new dependencies or persistence service are needed.
