# Design

## Context

See proposal.md for why. Facts that shape the approach:

- The league has 6 clubs and 3 matches per matchday. Each club has up to three generated team-news events per match (injury, suspension, doubt), with free text in `payload.text`, `player` null, and `kind` / `player_name` as eval labels the parser must not read. Matchday 1 therefore yields at most 18 items.
- `POST /team_news` does what an item needs: `Pipeline.interpret(text, club)` (model call, outside the lock), then validate, pick before saving, save. Today availability is `State.availability[(session_id, match_id, club)]`.
- `Pipeline.explain` already caches explanations by facts, mode and language, so a stored prediction does not make explanations expensive.
- The API runs as one replica with `minReplicas` and `maxReplicas` at 1. Uvicorn runs the FastAPI lifespan; existing tests build the app without it.
- `_AppShell.cshtml` sets `hx-indicator="#busy-indicator"` on `<main>`, inherited by every HTMX element. `#busy-indicator` sits above `#workspace`, which selection requests replace.
- The optimizer must be called only through `optimizer.py` (one long-lived solver thread).

## Goals / Non-Goals

**Goals:**
- Ingest is a real stage in code, and one item costs one parse and one pick whatever the number of visitors.
- A poll is a cheap read.
- No new infrastructure, dependency or UI framework; deterministic tests (no sleeping).

**Non-Goals:**
- Changing `ReplaySession`, `Pipeline`, scoring, the optimizer or the evals.
- Persistence across restarts, more than one featured matchday, per-visitor control of the feed.

## Decisions

**1. A feed object ticked by one producer thread.** `ingest.py` holds `Feed`: the item list (decision 2), a position, the shared availability and stored predictions, the news log, and a generation counter. `step()` delivers the next item; the thread started from the FastAPI lifespan calls it every 15 seconds. Tests call `step()` and `restart()` directly with a fake pipeline, so nothing sleeps. Alternatives: lazy delivery driven by polls (no thread, but catch-up bursts, model calls inside visitors' requests, and nothing happens without a poll), or an asyncio task (needs the loop to own a blocking model call). A thread is the plain fit for a synchronous API and a blocking call.

**2. Items and constants.** On construction the feed takes the `team_news` events of the matches whose `matchday == FEATURED_MATCHDAY`, sorted by (minute, match_id, id), which interleaves the three matches. `FEED_INTERVAL = 15`, `POLL_INTERVAL = 10` and `FEATURED_MATCHDAY = 1` are named constants (the UI reads its own poll value from configuration with the same default).

**3. Schedule.** The thread computes each deadline from a monotonic clock: `next = max(next + 15, now)`, so a slow tick is followed by the next item, not a burst. It wraps `step()` in a catch-all that marks the item not applied and logs; the feed must never die. The thread is a daemon and stops with the lifespan.

**4. One item, once.** `step()`: take the next item; interpret it with `Pipeline.interpret` (no lock held); then, under the feed lock, check the generation still matches (a restart during the model call discards the result), validate the player belongs to the club, set the player's status in the shared availability with the item's sequence number, call the shared pick helper (the existing `_pick` logic moved out of `api.py` so both use it) and store `(xi, facts, seq)` for that (match, club). If interpretation or the pick fails the item is logged as not applied and nothing is stored. The pick raises before any state changes, as `/team_news` does.

**5. Shared plus personal availability.** Shared availability is `{(match, club): {player_id: (status, seq)}}`. Personal availability keeps its key `(session_id, match, club)` but stores `(status, seq)` too, where `seq` is the feed's latest sequence number when the visitor submitted it. A prediction merges the two per player, the larger `seq` winning and a tie going to the personal entry. A session with no personal entry for the key reads the stored prediction (computed and stored once if absent); a session with one picks again from the merged availability (milliseconds) and relies on the explanation cache. `/team_news` keeps its contract and response; only the stored shape changes. A reset clears shared availability and stored predictions but never personal entries.

**6. The news log.** A bounded list (the last 50 entries) of `{seq, kind: "news" | "restart", match_id, club, text, applied}`. A single counter hands out `seq` and never goes backwards, including across resets. The log is guarded by the feed lock. Every step and every reset appends.

**7. Loop and restart.** After the last item, the next tick (one interval later) resets and appends a restart marker; the following tick delivers item 1 again. `restart()` (the API call) does the same at once: bump the generation, clear shared state, append the marker, and call `step()` for item 1 in the request thread (a model call of at most the model timeout, behind the busy indicator), then re-anchor the producer's schedule to one interval from now.

**8. API.** `GET /news?since=&match_id=&club=` returns `{items, latest_seq, changed}`: the log entries (all retained entries when `since` is absent, otherwise those newer than `since`; the UI renders only what is new), and `changed` true when a new applied item has the given match and club, or a new restart marker exists; false when `since` is absent. It only reads the log. `POST /news/restart` returns `{latest_seq}`. No session id is needed for either. Both routes live in `api.py` and take the feed from `app.state`.

**9. Threading rules.** The feed lock guards shared availability, predictions, the log and the generation, and is never held across a model call. `State.lock` still guards personal availability. A pick for a session copies the shared availability under the feed lock and then runs the optimizer outside it, so the optimizer thread is never waited on under a lock.

**10. UI wiring.**
- A `#news-bar` partial sits between the header and `#busy-indicator`: the ticker and the Restart feed button. It loads with `hx-trigger="load, every 10s"`, and carries the last-seen `seq` and the displayed match and club as hidden values.
- `OnGetNews` calls `GET /news`. If no entry is newer than the last-seen `seq` it answers 204 (HTMX makes no swap, so the ticker does not move). Otherwise it renders the new entries into the ticker, updates the hidden `seq`, and when the API said `changed` adds `HX-Trigger: lineup-changed`.
- `#workspace` listens (`hx-trigger="lineup-changed from:body"`), and fetches the lineup for the current selection without pushing history, reusing the existing lineup handler.
- Selection and language responses carry a fresh `#news-bar` (out-of-band and inside the shell), whose `load` poll has no last-seen `seq`, so news seen before the switch cannot trigger a refresh.
- Smooth scrolling: the ticker track is appended to (`hx-swap="beforeend"`), and each new item is its own element with its own CSS slide-across animation (about 120 px/s, right to left), so items already on screen are never re-rendered and never jump. A restart marker and the item delivered with it are rendered as one entry, so they cannot overlap. Finished items are hidden by `animation-fill-mode: forwards` and are cleared whenever the bar is rendered afresh (selection, language, restart). Under `prefers-reduced-motion` the same elements are a static list. Fallback if this proves awkward: re-render the whole strip when items change, which jumps on each new item.
- The bar sets its own `hx-indicator` so polls never show the busy status; the Restart button keeps the shared one. `hx-sync="this:drop"` stops a slow poll from stacking. A failed poll is ignored by HTMX defaults.
- The Restart feed button posts `POST /?handler=RestartFeed`, which calls the API and responds with the bar and `HX-Trigger: lineup-changed`.
- Strings (Restart feed, ticker label, not-applied mark, restart marker) are added for en, es and zh-Hant. News text is the generated English and is not translated.

## Risks / Trade-offs

- [Anyone can restart the shared feed for everyone, and there is no stop] → accepted: one visitor pressing Restart resets the demo for all. Run and record the demo when nobody else is on the site.
- [Without a configured model every item is not applied, so the ticker moves but no XI ever changes] → the not-applied mark makes it visible; check `llm_used` before recording. Free text cannot be used without the model.
- [A restart request makes a model call in the request thread, up to the model timeout] → it runs behind the busy indicator and is one call.
- [A slow or timed-out parse delays the items behind it, never overlaps them] → the schedule skips bursts (decision 3).
- [Up to 10 s between delivery and display] → accepted.
- [Each poll from each open page, every 10 s, forever] → a read of a cursor, but it adds requests to Application Insights.
- [Memory is bounded (6 clubs, 3 matches, a 50-entry log) but personal availability per session is still never evicted] → the existing `shortcut:` in `state.py`; unchanged.
- [In-memory feed and predictions are lost on restart, and the API must stay at one replica or each replica would run its own feed] → already required for team news.
- [The feed's lock ordering is the most delicate code] → the generation check, no model call under a lock, and a concurrency test (task 2.5).
- [`ReplaySession` stays unused outside tests] → left alone to keep the change small; ARCHITECTURE.md says the feed does not use it.

## Migration Plan

None: no stored data. The stored shape of personal availability changes in memory only. Rollback is reverting the change. Merging does not update the live site; deploying is a separate step.
