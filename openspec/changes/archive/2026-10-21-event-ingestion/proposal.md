# Proposal

## Why

The pipeline's first stage, Ingest, exists only as a box in ARCHITECTURE.md. The event feed and `ReplaySession` are built and tested, but nothing consumes them: the API loads events once as a static list, and the "late injury" in the demo is a button posting to `/team_news`. The multi-agent story (events flow in, the pipeline interprets them, the XI updates) is not real yet, and a feed that every visitor processed on their own would repeat the same model call and XI pick for each of them.

## What Changes

- A shared news feed runs inside the API from start-up. Every 15 seconds it takes the next team-news item of the featured matchday (matchday 1, 3 matches, at most 18 items, in order of scheduled time across the matches).
- Each item is processed once, whatever the number of visitors: the model parses it, the shared availability for that match and club is updated, the XI is picked again and the resulting prediction is stored, in memory.
- Every browser polls every 10 seconds with a cursor and receives the new items. All visitors see the same news in a right-to-left ticker above the "Updating" status. A tab refreshes its lineup only when a new item is for the match and club it shows. A poll does no processing and does not show the busy status.
- A visitor with no personal news of their own is served the stored prediction. Personal news (preset buttons and typed text) stays per session, as an overlay on the shared availability, and the later of two conflicting events wins.
- One shared "Restart feed" control resets the shared availability and predictions and begins again at the first item. After the last item the feed waits one interval, resets and loops.
- The interval (15 s), the poll (10 s) and the featured matchday (1) are named constants.
- ARCHITECTURE.md is updated: the Ingest row, a news-feed contract, the UI contract and wireframe.

Touches these ARCHITECTURE.md parts: Pipeline stages (Ingest becomes real), Contracts (a news-feed contract; `predict_lineup` and `submit_team_news` keep their shape), UI (ticker, restart control, polling). `ReplaySession` is not changed and is not used by the feed.

Out of scope: Event Hubs or any external transport, server push (SSE), a start/stop control, in-play events (passes, shots), persistence across restarts, more than one featured matchday, and the MCP adapter. Evals and the MCP adapter keep ignoring the shared feed.

## Capabilities

### New Capabilities
- `event-ingestion`: a shared, paced, looping feed of team news that is processed once per item into shared availability and stored predictions.

### Modified Capabilities
- `lineup-api`: adds the news poll and feed restart operations, and serves the stored prediction to a visitor with no personal news.
- `lineup-ui`: adds the news ticker, the Restart feed control and silent background polling that refreshes only the displayed match and club.

## Impact

- Backend: new `ingest.py` (feed, producer thread, news log, stored predictions); `state.py` gains the shared availability and stored predictions; `api.py` gets the poll and restart operations and merges shared availability with a session's own news. No change to `scoring.py`, `optimizer.py`, `replay.py` or `evals.py`.
- UI: new ticker and restart partials, a poll handler in `Index.cshtml.cs`, new methods on `LineupApiClient`, new localized strings (en, es, zh-Hant), CSS.
- Model: one parse call per item, about four a minute. Explanations are already cached by facts, mode and language.
- Tests: pytest for the feed order and pacing, process-once, shared and personal availability, restart and loop, and the API; dotnet tests for the poll handler, the refresh rule and the busy-status exemption.
- Dependencies and infrastructure: none. The API stays at one replica, since the feed and predictions are in memory and the feed restarts from the start when the API restarts.
