# Proposal

## Why

The shared news feed currently stores and polls English-only messages, even though the UI supports English, Spanish, and Traditional Chinese. Localizing the finite synthetic template catalog lets each visitor read the shared ticker in their selected language without adding per-poll translation work or model calls.

## What Changes

- Add deterministic Spanish and Traditional Chinese variants for every generated team-news template. English stays in `payload.text`, the single source the parser reads; the other two languages are stored beside it in `payload.translations`.
- Keep all three texts in each feed log entry and make the feed log available to callers in the requested locale.
- Reject loaded team-news event data that lacks a Spanish or Traditional Chinese translation, with a clear instruction to regenerate it.
- Add a validated `language` option to news polling; return only the selected message text, defaulting to English for callers that omit it.
- Have the UI include its selected language in background news polls so the ticker displays the corresponding translation.
- Preserve feed ordering, cadence, application status, sequence numbers, restart behavior, and lineup-refresh semantics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `synthetic-match-events`: generated team-news events include deterministic text for all supported languages.
- `event-ingestion`: feed entries retain complete localized text variants before they are pollable.
- `lineup-api`: news polling selects and returns only the requested locale's text.
- `lineup-ui`: ticker polling sends the selected language and displays the returned localized text.
- `ui-personalization`: the selected page language also governs shared news ticker messages.

## Impact

This changes the event payload produced by `backend/lineup_oracle/events.py`, event-data validation in `backend/lineup_oracle/state.py`, feed-log behavior in `backend/lineup_oracle/ingest.py`, the `GET /news` contract in `backend/lineup_oracle/api.py`, and the UI's news API client, page handler, and HTMX poll form. It does not change the LLM parser, lineup selection, or feed timing. Update `ARCHITECTURE.md` and `backend/README.md` (which documents the event fields and `GET /news`) and add backend and UI tests for complete generated translations, stale event data, and locale-specific polling.
