# Design

## Context

See proposal.md - Why. ARCHITECTURE.md (UI section) says each news entry is appended as its own element with its own CSS animation. The animation is `news-slide`: a fixed 16 s, linear, `translateX(100cqw)` to `translateX(-100%)`, with `--news-delay` set server-side as `i*6s`. The poll swaps `beforeend` into `#news-track`, and `news.js` removes an item on `animationend` and trims the track to 50.

Because the distance is `lane + item width` but the time is fixed, a wider item moves faster than a narrower one, so a wide item released after a narrow one can catch up with it. The spec requires that items never share space, so both the start time and the speed must depend on item width, which only the browser knows. That rules out a server-side delay.

## Goals / Non-Goals

**Goals:**
- No two items overlap, across polls and for any line length or language.
- A bounded backlog, so a page opened late or a restart does not queue minutes of old news.
- Timing logic that is pure functions, testable without a browser.

**Non-Goals:**
- Multiple lanes or a different poll interval.
- Changing what the server sends: it still returns every new entry.

## Decisions

**1. Items are released by a client-side queue, not by CSS delays.** New `.news-item` elements arrive paused offscreen (CSS: `animation-play-state: paused`, already at `translateX(100cqw)`). A scheduler adds a `news-run` class that sets `animation-play-state: running`. Alternative: keep CSS delays and compute them server-side from an estimated text width. Rejected: width depends on font, language and viewport, so overlap would remain for CJK.

**2. One constant speed for every item, and a width-based gap.** `SPEED` is 80 px/s (about what 16 s gave for a typical lane). On release the scheduler sets the item's `animation-duration` to `(laneWidth + itemWidth) / SPEED`, so all items move at the same speed and none can overtake another. The next item may start at `previousStart + max(3000 ms, (previousWidth + 16 px) / SPEED)`: the previous item's right edge clears the entrance after travelling its own width, 16 px is a visual margin, and 3 s is the requested floor between starts. Alternative: keep the fixed 16 s slide. Rejected: speed then varies with width, so a wide item overtakes a narrow one. Alternative: a fixed 3 s gap only. Rejected: a 640px line moves only 240 px in 3 s. Alternative: wait for the previous `animationend`. Rejected: that serialises on the full slide time and the ticker falls behind the feed. Cost: a wide line takes longer to cross than before (up to about 20 s), which is accepted.

**3. Logic is pure functions; the DOM glue is thin.** `news.js` exports, when `module` exists, `slideMs(itemWidth, laneWidth)`, `startGapMs(previousWidth)`, `trimQueue(queue, max)` and `nextRelease(queue, now, nextStart)`. `nextRelease` skips queued items whose `isConnected` is false, then returns either the head to start or how long to wait (or nothing when the queue is empty). Alternative: a bundler or JS test framework. Rejected: node's built-in `node --test` is enough and adds no dependency.

**4. Observe the whole page, not `#news-track`.** The Restart feed button, a selection change and a language change replace the whole `#news-bar` (`outerHTML`, directly or out of band), which creates a new `#news-track`. An observer bound to the old track would never see the new items. A single `MutationObserver` on `document.body` with `{childList: true, subtree: true}` queues any added `.news-item` (or any added node that contains one), so the initial render, polls, restart and language swaps all work with no change to the HTMX wiring. Queued items that were replaced are dropped by the `isConnected` check in `nextRelease`.

**5. Backlog cap of 5.** When more than 5 items wait, the oldest waiting ones are removed from the DOM, except an item with a restart marker, which is kept so the restart stays visible. Items already running are never dropped. The server log and the lineup refresh (`HX-Trigger`) do not depend on the ticker, so nothing is lost beyond display.

**6. Reduced motion bypasses the queue.** If `matchMedia("(prefers-reduced-motion: reduce)")` matches, the scheduler does nothing and the static list shows everything, as today.

**7. ARCHITECTURE.md** is updated in the same PR: the ticker paragraph now describes the queue and the constant speed instead of per-entry CSS delays.

## Risks / Trade-offs

- [Timers are throttled in background tabs, so queued items may enter in a burst on return] -> the cap bounds this; acceptable, with a `shortcut:` comment.
- [A resize changes lane width after an item starts, so its clear time shifts] -> duration and gap are fixed at release; a small error is tolerated.
- [Dropping hides a news item from the ticker] -> accepted per the spec; the ticker is transient, not the record. Restart markers are kept.
- [A narrow lane makes long lines slow: at 300px a 640px line takes about 12 s to clear, so 5 waiting items is about a minute] -> the cap of 5 is tuned for desktop widths; revisit if phones drop news in practice.
- [The Node test is not run in CI, so a regression is not caught automatically] -> run `node --test` locally with the other suites; add a CI step later if wanted. The DOM scheduling is verified by a manual check in a browser, since the repo has no browser tests.
