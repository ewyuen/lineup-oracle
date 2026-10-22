# Design

## Context

See proposal.md - Why. The API currently stores effective availability as only `out` or `doubt`, so an injury and suspension are indistinguishable after submission. `pick_xi` returns the starters and two ranked alternatives per position, and the UI renders alternatives as text without actions. The API's in-memory availability is already keyed by session, match, and club.

The design changes the prediction/alternatives contract and spans backend state, selection, API, the Razor/HTMX UI, and `ARCHITECTURE.md`.

## Goals / Non-Goals

**Goals:**

- Preserve the deterministic optimizer's XI and existing availability semantics while allowing a coach to explicitly keep eligible injured or doubtful non-starters visible as alternatives.
- Retain the news kind needed to distinguish injury and doubt from suspension.
- Return at most four alternatives per position and persist explicit selections per session, match, and club.
- Make alternative selection a distinct UI/API operation from team-news submission.

**Non-Goals:**

- Clearing or changing injury, doubt, or suspension status.
- Allowing suspended players to be selected.
- Promoting a selected alternative into the starting XI or changing formation.
- Durable storage across API restarts or sharing an analyst's selections across browser sessions.

## Decisions

1. **Use a dedicated alternative-selection operation rather than team news.** Add a focused API operation that accepts the match, club, session, player, and include/remove intent and returns the updated lineup. Reusing `/team_news` would incorrectly imply a new status update and could overwrite the player's actual news. The UI calls it through HTMX and swaps only the lineup fragment.

2. **Preserve the originating team-news kind with effective availability.** Store the kind alongside status and sequence for both shared feed events and per-session news. Merge shared and personal entries using the existing sequence precedence, carrying the winning kind. This is required to reject suspension while allowing injury or doubt; alternatives considered were exposing all `out` players (which would allow suspended players) or guessing from text (which would be unreliable).

3. **Keep optimizer output separate from manual alternatives.** Continue calculating the XI and the natural ranked alternatives from availability as today, then overlay the session's explicit choices on the alternatives only. Never feed an override into P(start) scoring or the MILP. Rank natural candidates by the existing score and tie-break rules. When a manual choice is added to a full position list, include it and remove the lowest-ranked current alternative; store the resulting explicit selection state consistently with the four-player limit. A manual removal returns that position to its natural ranked list.

4. **Return eligible candidates and selection state with the lineup.** Add a response collection for non-starting players whose latest effective team-news kind is injury or doubt, including identity, position, kind, and whether each is manually included. Exclude suspended players. This gives the UI actionable candidates without inventing player data or requiring it to reconstruct availability.

5. **Scope selections by the existing session context.** Store selections in memory under `(session_id, match_id, club)` and apply them to every subsequent prediction in that context. Other sessions and match/club contexts remain independent. A newer effective suspension makes a player ineligible and removes them from the returned selected alternatives; restart clears the in-memory selections with the rest of API state.

## Risks / Trade-offs

- [News kind must survive shared/personal precedence] -> Carry kind with each availability entry and test both feed and user submissions, including latest-event-wins behavior.
- [A full four-player list can displace an existing candidate] -> Use deterministic score and player-id ordering for the displaced candidate and test replacement at capacity.
- [Concurrent alternative actions could overwrite each other] -> Validate and update session selections under the existing state lock; keep optimizer work outside the lock where possible.
- [Selections are lost when the API restarts] -> This matches the existing in-memory session availability contract; persistent storage is out of scope.
- [UI catalog could imply a suspended player is available] -> Populate candidate actions only from the API's eligible injured/doubt candidate collection and visibly retain their status when shown.

## Migration Plan

No data migration is required because state is in memory and is reset on restart. Deploy the API and UI together so the UI's selection action and candidate rendering use the updated API contract. Rollback by reverting the API and UI changes together; no persisted records need cleanup.
