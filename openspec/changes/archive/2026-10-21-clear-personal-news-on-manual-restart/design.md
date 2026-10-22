# Design

## Context

See proposal.md for motivation and the event-ingestion spec delta for the required behavior. The feed's reset helper clears shared availability and cached predictions for both automatic and manual resets. Per-session availability and alternatives are held separately in `State.availability` and `State.selections`; `State.reset()` clears both but nothing calls it, and the manual restart path does not clear them. Team-news writes use `State.lock` and then access the feed, so any combined reset must preserve that lock order. The first feed item is processed immediately after a manual restart.

## Goals / Non-Goals

**Goals:**
- Clear all per-session availability and alternatives only for a manual restart.
- Preserve per-session availability during the automatic end-of-lap reset.
- Keep feed log sequencing and immediate first-item delivery unchanged.

**Non-Goals:**
- Changing which feed item is replayed or how the shared feed cache resets.
- Clearing visitor session identifiers, posted news, or other state not representing player availability or alternatives.
- Changing the API response or adding a restart option.

## Decisions

- Keep the automatic and manual reset paths distinct. Call the existing `State.reset()` (availability and alternatives, so a cleared alternative cannot reappear when a player is marked doubt again) in `Feed.restart()`, not in the shared reset helper used by the automatic loop; otherwise every lap would erase personal news.
- Coordinate the manual clear with the feed reset by acquiring the existing state lock before the feed lock, matching the lock order used by team-news submissions. Reset the personal and shared state and update the feed cursor while synchronized, then release locks before processing the first item so model and lineup work do not hold the state lock.
- Keep the `/news/restart` contract unchanged. The request still logs a restart marker, resets shared cached predictions, immediately attempts the first feed item, and returns the latest sequence.
- Alternatives considered: clearing only the calling session would need a restart parameter and does not match the shared demo reset; clearing in the API handler separately from the feed reset risks a concurrent submission landing between the two operations; clearing it in the common reset helper would incorrectly affect automatic laps.

## Risks / Trade-offs

- A reversed lock order could deadlock with a concurrent team-news submission. The reset must acquire state before feed locks, and tests should hold the state lock and check that `restart()` waits for it, then finishes.
- The first feed item may immediately add a shared player status after the manual clear. This is expected; the reset clears visitor-specific statuses while preserving the existing replay behavior.

## Migration Plan

No persistent data migration is needed because availability is in memory. Deploy the code change normally; reverting the code restores the previous restart behavior.
