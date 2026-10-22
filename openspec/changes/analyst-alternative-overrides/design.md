# Design

## Context

See proposal.md - Why. The API stores effective availability as `(status, seq)` with status only `out` or `doubt`, so an injury and a suspension are indistinguishable after submission. `optimizer.pick_xi` returns the starters and `ALTERNATIVES = 2` ranked alternatives per position, drawn from players with a P(start) above 0 (so a doubtful bench player is already listed when ranked, an `out` player never is). `picking.pick` builds the explanation `facts` from the XI and those alternatives only, `_render` looks every listed player up in `facts`, and `Pipeline.explain` requires the model's explanations to cover exactly the `facts` ids. `feed.prediction` returns shared `XI` and `facts` objects by reference. The UI renders alternatives as text without actions. The API's in-memory availability is keyed by session, match and club.

The design changes the prediction/alternatives contract and spans backend state, picking, explanations, the API, the Razor/HTMX UI and `ARCHITECTURE.md`.

## Goals / Non-Goals

**Goals:**

- Preserve the deterministic optimizer's XI and existing availability semantics while allowing a coach to explicitly keep eligible injured or doubtful non-starters visible as alternatives.
- Retain the news kind needed to distinguish injury and doubt from suspension.
- Return at most four alternatives per position (two natural plus manual selections) and keep explicit selections per session, match and club.
- Make alternative selection a distinct UI/API operation from team-news submission.
- Give every listed alternative, manual or natural, a grounded explanation and a visible status.

**Non-Goals:**

- Clearing or changing injury, doubt or suspension status.
- Allowing suspended players to be selected.
- Promoting a selected alternative into the starting XI or changing formation.
- Durable storage across API restarts or sharing an analyst's selections across browser sessions.
- Exposing the operation through the MCP adapter (it stays at its four tools) or adding telemetry beyond the existing lineup span.

## Decisions

1. **Dedicated alternative-selection operation, not team news.** `POST /alternatives` takes the `PredictRequest` fields (match, club, session, mode, language, inheriting the `session_id` length limit), a `player_id` and `included` (true to include, false to remove), and returns the updated `LineupOut`. It sets state rather than toggling, so repeating a request is harmless. Reusing `/team_news` would imply a status update and could overwrite the player's real news. The UI calls it through HTMX and swaps only the lineup fragment. Errors: 404 for an unknown match; 422 with a message for a club not in the match, a player not of the club, a player in the XI or a player with no injury or doubt news (including a suspended one). Removal never checks eligibility, so a stale selection can always be cleared, and removing an absent selection is a no-op.

2. **Store the news kind, derive status from it.** Availability entries become `(kind, seq)` in the feed's shared state and in `State.availability`; status comes from `STATUS_OF_KIND`. `merge` keeps latest-sequence precedence (personal wins a tie, as today) and returns the winning `(kind, seq)`; callers that need statuses (`pick`, `p_start_scores`) derive them from the merged result. The call sites and tests that change are named in tasks (ingest, `team_news`, `state`, `test_ingest`, `test_api`). The feed log's own `kind` field (`news`/`restart`) is untouched.

3. **Natural alternatives stay at two; manual choices add to them.** `ALTERNATIVES` stays 2 (non-out players with a P(start) above 0, ranked by score then player id), so the xi-optimizer spec is unchanged. The XI never sees a selection: selections are not passed to P(start) scoring or the MILP. The overlay runs in `picking` next to `pick`, on whichever XI the request uses (stored or freshly picked), and builds **new** alternatives and `facts` collections, never touching the shared stored objects. Rules, applied per position:
   - A selection is **valid** when its player's latest effective kind is injury or doubt, the player is not in the XI, and the player is of that position. Invalid selections are ignored for the response (not deleted).
   - The list is the natural ranked entries followed by valid selections not already natural, each marked `included`. A doubtful player who is already a natural alternative stays in place with `included` true; removing them clears the flag and they stay listed by rank.
   - The list is capped at four per position, and nothing is pushed out to make room. The cap cannot be reached: natural and manual entries are all bench players of one position, and a position's bench is at most four with the supported rosters and formations. The overlay therefore has no cap logic. Code comment: `shortcut: no cap, bench per position is at most 4, add a cap if squads grow`.
   - Manual injured players have P(start) 0 and a doubtful one keeps its scored value; their order among manual entries is by player id.

4. **Explanations cover manual alternatives.** The overlay's `facts` include each manual player with status `out` or `doubt`, so `_render` and the model's exact-coverage check still hold. Template `explain` gains an `out` branch that says the player is injured or unavailable and not expected to start, instead of "Likely starter". The explainer instructions gain a rule for `out`, and the grounding check accepts unavailability wording for status `out` instead of counting it as a failure. A changed selection changes `facts`, so it is a new explanation cache key and may cost one model call; that is accepted.

5. **Return status and candidates with the lineup.** `PlayerOut` gains `status` (`available`, `doubt` or `out`, taken from `facts`), so the UI can mark any alternative as injured or doubtful without joining. The response also carries `candidates`: non-starting players whose latest effective kind is injury or doubt, each with id, name, number, position, kind and `included`. Suspended players are not candidates. The UI only offers actions for candidates.

6. **Selections are session state, filtered on every read.** `State` holds `selections[(session_id, match_id, club)]`, an immutable set of player ids, replaced copy-on-write under `s.lock` like `availability`; an empty set removes the key. The write validates eligibility from the shared plus personal availability and the XI of the path the request would use, advisory only (the feed state has its own lock), and the read-time filter in Decision 3 is what enforces eligibility. A selection that stops being valid (newer suspension, the player recovering, a starter's injury promoting them into the XI, a feed lap reset) disappears from the response but stays stored, and returns if the player becomes valid again; removal still works. `State.reset()` clears selections. `lineup.source` keeps its meaning: `personal` only when the session has news of its own, so a session with only selections overlays a copy of the stored prediction and does not re-run the optimizer.

7. **Analyst mode only.** The selection controls render in analyst mode. Fan mode, which hides numbers, shows the alternatives and their status but no controls. The browser session is the existing session cookie (30 days), so "browser session" in the specs means that cookie.

## Risks / Trade-offs

- [News kind must survive shared/personal precedence] -> Carry kind with each availability entry and test both feed and user submissions, including latest-event-wins and a same-sequence tie.
- [Overlay mutating shared stored objects] -> Build new alternatives and facts; a test proves another session's stored prediction is unchanged.
- [Concurrent selection writes] -> Copy-on-write under the existing state lock; the optimizer is not run under the lock for selection writes.
- [Selection state outlives eligibility] -> Filter on read, always allow removal, test suspension, recovery and promotion.
- [Selections are lost when the API restarts] -> Matches the in-memory session availability contract; persistence is out of scope.
- [Each change costs a possible model call] -> Accepted; failure falls back to templates as today.

## Migration Plan

No data migration is required because state is in memory and is reset on restart. Deploy the API first; it only adds fields, so the old UI keeps working, then the UI that uses the new action. Rollback by reverting both; no persisted records need cleanup.
