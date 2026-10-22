# Proposal

## Why

The analyst's candidate list ("Injured or doubtful players") hides suspended players entirely, so an unavailable non-starter looks like a healthy one. The analyst should see every unavailable non-starter, and a suspension should stay until it is explicitly served ("cleared"), not be overwritten by other news.

## What Changes

- The candidate list shows all unavailable non-starters: injured, doubtful and suspended. Its heading becomes "Unavailable players" (en, es, zh-Hant).
- Suspended candidates carry kind `suspension`, show a "Suspended" badge and have no Add action. `POST /alternatives` still rejects them with 422 (visible and selectable kinds are split in `picking.py`).
- A suspension can only be lifted by a "cleared" team-news message typed in the Team News box. While a player is suspended, injury, doubt, recovered and fit news for them is rejected with 422 (text and structured). A repeated suspension is accepted. A shared-feed event cannot override a session's suspension.
- ARCHITECTURE.md: the `candidates` contract now includes suspended players.

Out of scope: healthy bench players in the list, a "cleared" preset button, changing the XI logic.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `lineup-api`: Predict a lineup (candidates include suspended players); Manage session-scoped alternative selections (suspended stays listed, not selectable); new requirement that a suspension is lifted only by "cleared".
- `lineup-ui`: Alternatives and Choose eligible unavailable players (list shows suspended players with a badge and no action; heading renamed).
- `team-news-parsing`: Parse free-text team news (a suspension is cleared only by a "cleared" status; other statuses for a suspended player are rejected).

## Impact

- Contracts and components in ARCHITECTURE.md: the `/predict_lineup`, `/team_news` and `/alternatives` response `candidates` field, and the availability merge (feed vs session).
- Backend: `picking.py` (`eligible`, `overlay`), `api.py` (`team_news` guard), `ingest.py` (`merge`, feed ingest) and tests.
- UI: `_Lineup.cshtml`, `UiText*.resx` (`AlternativeCandidates`, new `StatusSuspended`) and UI tests.
- No new dependencies.
