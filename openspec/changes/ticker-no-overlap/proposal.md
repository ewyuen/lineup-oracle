## Why

Ticker items overlap in the single lane. The server staggers items only within one poll batch (`--news-delay: i*6s`), so a batch from the next poll (10 s later) starts at 0 s over items still sliding (each takes 16 s). Even inside a batch, 6 s is too short for a long Spanish or Traditional Chinese line (up to 40rem wide), so its tail is still on screen when the next item enters. The result is unreadable text.

## What Changes

- Add a small client-side scheduler in `news.js`: new items wait offscreen and enter one at a time. The next item starts once the previous item's right edge has cleared the lane entrance (computed from measured widths), and never sooner than 3 s after the previous start.
- Move every item at one constant speed (80 px/s) by setting its slide duration from its width, so a wide item can never catch up with a narrower one ahead of it.
- Watch the whole page for new items, because Restart feed, club and language changes replace the whole news bar.
- Cap the waiting queue (5 items); on a longer backlog (page load with retained entries, restart, many posted lines) the oldest waiting items are dropped from the ticker, except a restart marker.
- Remove the server-side `--news-delay` stagger from `_NewsItems.cshtml` and its use in `site.css`; items start paused and are released by the scheduler.
- Reduced-motion static list is unchanged (no scheduler, no dropping).
- Add a `node --test` unit test for the timing and cap logic, run locally (not added to CI).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lineup-ui`: the "Shared news ticker" requirement gains a no-overlap rule and a bounded-backlog rule, with new scenarios.

## Impact

- Touches only the UI component of ARCHITECTURE.md (the "shared news ticker" paragraph: items now enter through a client-side queue instead of per-entry CSS delays). No API contract changes; the news endpoint, `seq` handling and polling are unchanged.
- Code: `ui/LineupOracle.Ui/wwwroot/js/news.js`, `wwwroot/css/site.css`, `Pages/Shared/_NewsItems.cshtml`; new `ui/LineupOracle.Ui/wwwroot/js/news.test.js`.
- Dropped items are only dropped from the visual ticker; the API log and the lineup refresh trigger are unaffected.
- Out of scope: multiple lanes, changing the poll interval. The fixed 16 s slide time is replaced by a width-based one at constant speed.
