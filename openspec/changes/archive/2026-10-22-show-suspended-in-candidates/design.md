# Design

## Context

ARCHITECTURE.md (the `candidates` field of the lineup response, and availability as (kind, seq) per player merged from the feed and the session) is the contract touched. See proposal.md for motivation.

Today `picking.eligible()` serves two jobs: which non-starters the UI lists, and which may be added to the alternatives. Its filter `SELECTABLE_KINDS = (injury, doubt)` therefore hides suspended players. Availability is one latest (kind, seq) entry per player in the shared map and in each session's map; `ingest.merge` picks the later one. Nothing stops later news from overwriting a suspension, and the UI offers presets only for injury, suspension and doubt on picked players (suspended non-starters have no card).

## Goals / Non-Goals

**Goals:**
- Suspended non-starters appear in `candidates`, never selectable.
- A suspension ends only on a text "cleared".

**Non-Goals:**
- Healthy bench players, a cleared button, any change to scoring or the optimizer.

## Decisions

1. **Split visible from selectable in `picking.py`.** `eligible()` returns every non-starter whose latest kind is in `VISIBLE_KINDS = (injury, doubt, suspension)`; `SELECTABLE_KINDS` stays `(injury, doubt)`. `overlay` builds `candidates` from the visible set, but `chosen` selections, `included` and the `/alternatives` 422 check use only the selectable set. No new response field: the UI derives "no Add button" from `kind == "suspension"`. Alternative considered: a `selectable` boolean on each candidate; rejected as redundant, since the kind already says it and the contract stays smaller.

2. **Enforce the lock when news is written, plus one rule in `merge`.** In `api.team_news`, inside the `s.lock` block and before `pick`, read the player's current effective kind (`merge(shared, personal)`); if it is `suspension` and the new kind is not `suspension` or `cleared`, raise 422 naming the player. A repeated suspension is accepted. Structured submissions cannot send `cleared` (the `Kind` literal is unchanged), so the Team News box is the only release path, as asked. For the feed: `Feed` ingestion ignores a non-clearing event for a player whose shared entry is a suspension, and `merge` keeps a personal suspension when the winning shared entry is not a cleared status. Only the shared side needs the `merge` rule, because the session side is guarded at write time against the merged state, so a session that cleared and then re-injured a player is not resurrected by an older feed suspension. Alternative considered: keeping a history of events and replaying it; rejected as much more code for a case the feed rarely produces (the generator emits injury, suspension and doubt once each per match).

3. **Reject, do not ignore.** A blocked kind returns 422 with a clear message rather than silently doing nothing, so the analyst learns why. The text-path model call happens before the lock, so it is unaffected.

4. **UI.** `_Lineup.cshtml` badge and button logic keys on `candidate.Kind`: `suspension` shows a new `StatusSuspended` badge (red like out) and no form. The `AlternativeCandidates` string becomes "Unavailable players" (en, es, zh-Hant, and the neutral `UiText.resx`). The picked-player and alternative badges are unchanged (status `out` still reads "Injured"), since a suspended player is never a starter or an alternative.

## Risks / Trade-offs

- [A suspension never lifted if the model cannot parse "cleared"] → The text parser already supports `cleared` (agents.py, evals); the evals include "has served his ban". With the model off, text is unavailable, so the only recourse is restarting the feed (which clears session news).
- [Message in an eval or test that sends injury for a suspended player now fails] → Update those tests in the same change.
- [Feed ordering corner case] → Covered by the shared-side rules in decision 2 and a unit test.

## Open Questions

- None blocking. Whether the feed generator should ever emit "cleared" is left for later; it currently never does.
