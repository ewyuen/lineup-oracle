# Proposal

## Why

Restarting the feed resets shared availability and predictions, but visitor-specific player statuses can continue affecting lineups afterward. A manual restart is a reset of the whole shared demo, so it should return every session to the same clean baseline. Any visitor can already restart the shared feed, so this deliberately includes other visitors' personal news. The automatic loop's behavior does not change.

## What Changes

- Clear all session-scoped player availability and alternatives when a visitor manually restarts the feed.
- Preserve session-scoped player availability when the feed reaches its automatic end-of-lap reset.
- Keep the current restart behavior of recording a marker and immediately delivering the first feed item.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `event-ingestion`: distinguish manual restart behavior from automatic loop resets for session-scoped player availability.

## Impact

- Backend restart handling in `lineup_oracle.ingest` (`Feed.restart`) and `lineup_oracle.state` (`State.reset`).
- Unit tests for manual restart, automatic loop reset, and session isolation.
- The News feed and personal-news reset contract in `ARCHITECTURE.md`.
