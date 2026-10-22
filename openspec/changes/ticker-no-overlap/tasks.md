# Tasks

## 1. Branch

- [ ] 1.1 Work on branch `feature/ticker-no-overlap` (already created from origin/main in its own worktree); verify with `git branch --show-current`

## 2. Timing logic and tests

- [ ] 2.1 In `ui/LineupOracle.Ui/wwwroot/js/news.js` add pure functions, exported through `module.exports` when `module` exists: `slideMs(itemWidth, laneWidth)` = `(laneWidth + itemWidth) / 80 * 1000`; `startGapMs(previousWidth)` = max of 3000 and `(previousWidth + 16) / 80 * 1000`; `trimQueue(queue, max)` (keeps the newest `max`, never drops an item with a restart marker, returns kept and dropped); `nextRelease(queue, now, nextStart)` (skips items whose `isConnected` is false, returns the head to start, or the wait in ms, or nothing for an empty queue); verify by a Node import
- [ ] 2.2 Add `ui/LineupOracle.Ui/wwwroot/js/news.test.js` using `node:test`: `slideMs` gives equal speed for a 100px and a 640px item (distance divided by time is 80 px/s); a 100px item then a 640px item never overlap over the whole slide (simulated positions); `startGapMs` floors at 3 s for a short item and exceeds 3 s for a 640px item; `trimQueue` keeps the newest 5, reports dropped, keeps a marker item, leaves an under-cap queue alone; `nextRelease` waits before `nextStart`, starts the head at or after it, skips disconnected items and handles an empty queue; verify with `node --test ui/LineupOracle.Ui/wwwroot/js`

## 3. Scheduler and markup

- [ ] 3.1 In `news.js` add the scheduler: one `MutationObserver` on `document.body` (`childList`, `subtree`) queues each added `.news-item` (and `.news-item` descendants of added nodes) that has no `news-run`, trims with `trimQueue` (removing dropped elements), and on a timer calls `nextRelease`; on release it sets the item's `animation-duration` from `slideMs`, adds `news-run`, and sets `nextStart = now + startGapMs(width)`; skip all of this under reduced motion; keep the existing `animationend` removal and 50-item trim; add a `shortcut:` comment about background-tab timers; verify with the manual check in 4.2
- [ ] 3.2 In `site.css` make `.news-item` start with `animation-play-state: paused` and run under `.news-run`; drop the `--news-delay` use and leave the 16s only as the fallback duration (JS sets the real one); leave the reduced-motion block as is; verify the stylesheet has no `--news-delay`
- [ ] 3.3 In `Pages/Shared/_NewsItems.cshtml` remove the `style="--news-delay: ..."` attribute (and the unused loop index if nothing else uses it); verify `dotnet test ui` passes and add or adjust a `LineupUiTests` assertion that an item renders without an inline delay

## 4. Docs and verification

- [ ] 4.1 Update the ticker paragraph in ARCHITECTURE.md (entries enter through a client-side queue at one constant speed; no per-entry CSS delay; cap of 5); verify the paragraph no longer mentions per-entry delays
- [ ] 4.2 Manual browser check with the UI running (`/dev-start`): switch to Spanish and Traditional Chinese, press Restart feed, change language and club after a restart, open the page late; verify items never overlap, the ticker keeps working after each swap, a long backlog drops the oldest, and a restart marker stays visible
- [ ] 4.3 Run the full suites: `python -m pytest -q` in `backend/`, `dotnet test ui`, `node --test ui/LineupOracle.Ui/wwwroot/js`; verify all pass

## 5. Approval

- [ ] 5.1 Human approval gate: summarize results and stop for the user's approval. Do not archive or merge before it. After approval, run the OpenSpec archive, then open a PR from `feature/ticker-no-overlap` and merge it
