# Design

## Context

History is derived read-only from the seeded events: `retrieve_player_history` (`history.py`) takes rows from the graph or from `history_from_memory`, and both filter by time themselves (the graph in Cypher). The feed (`ingest.py`) replays the matchday-1 team-news events in a loop and keeps no event id in its log. Manual submissions (free text and the buttons) converge in `POST /team_news`, where `s.availability[key] = updated`, and are kept per `session_id` in `State`. `POST /player_history` has no session. See proposal.md for the why and the specs for the behavior; this covers how.

## Goals / Non-Goals

**Goals:**
- One overlay applied in `retrieve_player_history`, the same for the graph and memory paths.
- State in memory only, next to the existing per-session availability.

**Non-Goals:**
- No write to Postgres at runtime; the graph stays derived and read-only.
- No persistence across restarts (a restart re-dates feed items by their next delivery; accepted).
- Posted info lines are not history. No change to the feed, the news log or any lineup behavior.

## Decisions

- **State holds both maps.** `State.delivered: dict[event_id, datetime]` (feed items) and `State.session_news: dict[(session_id, player_id, kind), NewsEntry]` with `NewsEntry(at, match_id, club, text)`. They sit beside `availability`. `State.reset()` (called by `/news/restart`) clears neither, since a restart must not re-stamp or duplicate. Alternative: keep `delivered` on `Feed`; rejected because retrieval already takes `State`, and `Feed` is an HTTP-layer object.
- **Set only if absent.** `delivered.setdefault(id, now)` and the same for session entries, so the first time wins and repeats are no-ops without extra checks. `setdefault` on a dict is atomic in CPython, so no new lock.
- **Stamp at delivery, whether or not it was applied.** `Feed.step` stamps the item before it is interpreted, so an item the parser could not read still arrived as news. Alternative: stamp only applied items; rejected because the feed shows unapplied items too and history would then disagree with the ticker.
- **Id for manual entries.** `manual-<player_id>-<kind>`, type `team_news`, payload `{kind, text, player_name}`. Only that session sees it, so the id needs no session part. The text is the submitted line, or for a button an English line made from the player's name and kind.
- **Time filter moves after the overlay.** Both stores are asked for the player's rows with only the type and match filters; `retrieve_player_history` then re-times delivered items, adds the session's entries (honoring the same type and match filters), applies `from`/`to` in Python and sorts by (time, id). This is the only way the graph, which filters in Cypher on the synthetic time, can match memory. Cost: the graph returns the player's whole history instead of a range; it is per player and small. The graph queries themselves do not change; callers pass no time bounds.
- **Clock.** `create_app` gets a `now` callable (default UTC now) next to the existing `clock`, passed to `Feed` and used in `team_news`, so tests can fix the time. The history parser gets `now` through `Pipeline.parse_history_question`.
- **Today for the parser.** `HISTORY_PARSER_INSTRUCTIONS` gets one sentence and the payload gets `now` (ISO UTC); code validation of the returned range is unchanged.
- **Session on the history endpoint.** `PlayerHistoryRequest.session_id` (default `default`, max 64, like the others). The UI handler calls `EnsureSessionCookie()` and sends `GetSessionId()`.

## Risks / Trade-offs

- [Per-session entries are never evicted] → same as `availability`; the existing `shortcut:` comment covers it.
- [Restart re-dates feed news] → accepted (memory only); documented in ARCHITECTURE.md.
- [Time filtering in Python hides a Cypher/Python disagreement] → the graph parity test runs with the overlay on and off.
- [A feed item delivered on a day other than the question's day] → "today" is the UTC date; a question near midnight UTC can miss it. Accepted for a demo.

## Migration Plan

None: no schema or data change. Merge after `player-history-graph-rag`.
