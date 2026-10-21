# Tasks

## 1. Branch

- [x] 1.1 Create the feature branch `feature/event-ingestion` from main; verify `git branch --show-current` prints it.

## 2. Feed and shared state (backend)

- [x] 2.1 Move the `_pick` logic out of `api.py` into a helper both the API and the feed call, with no change in behaviour. Verify the existing `backend/tests/test_api.py` and `test_scoring_optimizer.py` pass unchanged.
- [x] 2.2 Add `backend/lineup_oracle/ingest.py` with `Feed`: the matchday-1 team-news items ordered by (minute, match_id, id), the constants `FEED_INTERVAL`, `POLL_INTERVAL` and `FEATURED_MATCHDAY`, shared availability with sequence numbers, stored predictions, the bounded numbered news log, and a generation counter. Verify with `backend/tests/test_ingest.py` (fake pipeline, no sleeping): item count and order, only matchday 1 and only team news, and the log's sequence numbers never decrease.
- [x] 2.3 Add `Feed.step()`: interpret once outside any lock, discard the result if the generation changed, validate the club, update the shared availability, pick through the helper, store the prediction. Verify in `test_ingest.py`: an injury removes the player from the stored prediction, the pipeline is asked once per item however many reads follow, an unreadable item, an unknown player and a no-legal-XI item are logged not applied and change nothing, and an exception in processing marks the item not applied and the next `step()` still runs.
- [x] 2.4 Add loop and restart to the feed: after the last item the next tick resets and appends a restart marker, `restart()` resets and delivers item 1 at once, and a reset keeps personal availability. Verify in `test_ingest.py`: the lap wraps with a marker, restart mid-lap gives marker then item 1, sequence numbers continue across a reset, and a restart during a model call discards the late result.
- [x] 2.5 Add the producer thread (fixed schedule from a monotonic clock, no burst after a slow tick, daemon, stopped with the lifespan) started from the FastAPI lifespan in `create_app`. Verify with a test that drives the schedule with a fake clock: no burst after a 40 s tick, and an error in one tick does not stop the thread; and verify that `TestClient(create_app(...))` without lifespan starts no thread.
- [x] 2.6 Store personal availability as `(status, seq)` and merge it with the shared availability per player, the larger sequence number winning and a tie going to the personal entry; a session with no personal entry for the key reads the stored prediction (computed and stored once if absent). Verify in `test_api.py` with the fake LLM: a feed injury shows in a session's prediction, personal doubt then feed out gives out, feed out then personal doubt gives doubt, other sessions are unaffected by personal news, and two sessions with no personal news get the same XI with one pick.
- [x] 2.7 Add `GET /news` and `POST /news/restart` to `api.py` (changed rules, first poll reports nothing changed, restart marker counts for every club, read only). Verify in `test_api.py`: new news for the caller's club says changed, news for another club does not, a not-applied entry does not, a restart marker does, a poll without `since` returns the recent entries and no change, and polling processes nothing.
- [x] 2.8 Verify that `evals.py` and the MCP adapter do not read the shared feed state (a test that runs the evals after the feed has applied news and gets the same scores). Run `python -m pytest -q` in `backend/`; verify everything passes.

## 3. UI

- [x] 3.1 Add `GetNewsAsync` and `RestartFeedAsync` and their DTOs to `LineupApiClient`. Verify with `LineupApiClientTests.cs` (request shape with and without `since`, success, API error).
- [x] 3.2 Add the `_NewsBar` partial (ticker where each new item is appended as its own element with its own right-to-left slide-across animation, so existing items never restart; a restart marker and its first item as one entry; the static list under `prefers-reduced-motion`, an accessible name, a text mark for not-applied items, the restart marker, and the Restart feed button) and the `Index` handlers `News` (GET poll) and `RestartFeed` (POST). The bar polls with `hx-trigger="load, every 10s"`, `hx-sync="this:drop"` and its own indicator; the poll answers 204 when nothing is new and sends `HX-Trigger: lineup-changed` when the API says changed. Verify with `LineupUiTests.cs`: 204 when nothing new, the header only when changed, new items are appended and old ones are not re-rendered, a marker and its first item are one entry, items rendered newest last, the markup does not use the shared busy indicator, the Restart button does, and a failed API call keeps the previous ticker.
- [x] 3.3 Render `#news-bar` between the header and `#busy-indicator`, refresh it (out-of-band) on every selection response and inside the language shell with no last-seen number, and make `#workspace` fetch the current lineup on `lineup-changed` without pushing history. Verify with `LineupUiTests.cs`: selection and language responses carry a bar with no last-seen number, and the workspace has the listener.
- [x] 3.4 Add the new strings (Restart feed, ticker label, not-applied mark, restart marker) to the en, es and zh-Hant resources, and the ticker styles to `site.css`. Verify with a test that every culture has every new key, and run `dotnet test` from `ui/`.

## 4. Documents

- [x] 4.1 Update ARCHITECTURE.md: the Ingest row (shared feed, processed once, stored predictions), a news-feed contract (`GET /news`, `POST /news/restart`, constants, loop and restart), the UI contract and the wireframe (news bar above the status), the one-replica note, and that `ReplaySession` is not used by the feed. Update `backend/README.md` with the new operations. Verify by reading both against the code.

## 5. Final checks

- [x] 5.1 Run `python -m pytest -q` in `backend/`, `dotnet test` in `ui/` and `openspec validate event-ingestion --strict`; verify all pass.
- [x] 5.2 With `dev-start` running both locally and the model configured: verify the first item shows within 15 s, items come about every 15 s and move right to left, a second browser profile sees the same ticker, an item for the displayed club changes its XI within 10 s, an item for another club does not refresh it, the busy status does not flash on polls, Restart feed resets the ticker for both profiles, and the feed loops after the last item. Record the result in this file.
- [x] 5.3 Human approval gate (HITL): summarize the results and stop for the user's approval. After approval, run the OpenSpec archive, then open a PR from `feature/event-ingestion` and merge it. Do not archive or merge before approval.

## Live check (task 5.2) — 2026-10-21

Run with the API and UI started locally, model configured. Checked by script (no browser):
- Items arrived at 10 s, 25 s, 40 s, 50 s samples: seq 1 to 4, one about every 15 s, all applied (the model parsed them).
- The UI poll `GET /?handler=News` returned the last three items as separate `news-item` elements, newest last, with the hidden sequence number updated.

Not verified: the browser could not open localhost (the Chrome tool stayed on the new-tab page), so these were not checked: items moving right to left, a second browser profile seeing the same ticker, an XI changing within 10 s for the displayed club, no busy-status flash on polls, Restart feed in two profiles, and the loop after the last item. Please check these by eye before approving.

Approved by the user on 2026-10-21 with the browser checks above not verified by Claude.
