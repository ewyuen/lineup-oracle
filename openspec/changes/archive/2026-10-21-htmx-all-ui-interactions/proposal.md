# Proposal

## Why

Fixture selection, club selection, favourite-club changes, and language changes currently navigate or redirect the whole page, while team-news updates and retry already use HTMX. Making the existing same-page interactions asynchronous will provide a consistent experience without moving rendering or lineup decisions out of the Razor Pages UI and API.

## What Changes

- Convert fixture and club selection to HTMX requests that refresh all dependent server-rendered UI state, including the selection controls, team-news form values, and lineup.
- Convert favourite-club and language preference submissions to HTMX updates while preserving their cookies, selection behavior, localization, and anti-forgery protection.
- Preserve and align the existing HTMX team-news, player-preset, and retry flows with the same partial-update and error-handling conventions.
- Establish HTMX as the default for future UI actions that update the current page in place; retain normal requests for true document navigation and downloads.
- Keep non-HTMX full-page behavior as a fallback; do not add a mode switch or change the currently hidden mode-toggle UX.
- Keep the FastAPI contract and the deterministic lineup-selection behavior unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lineup-ui`: Fixture and club selection update asynchronously and refresh dependent page state without a full-page navigation, failed predictions preserve the last displayed view, and future in-page UI actions use HTMX.
- `ui-personalization`: Language and favourite-club preferences update asynchronously, remain remembered, and keep their existing effect on localization and club selection.

## Impact

- ASP.NET Razor Pages UI: `Index.cshtml`, `Index.cshtml.cs`, fixture and preference partials, and any shared fragment introduced for dependent UI updates.
- UI integration tests for HTMX requests, returned fragments, cookies, selected state, localization, anti-forgery, and non-destructive failures.
- `ARCHITECTURE.md`, to document the UI interaction/update contract.
- No backend API, data model, or third-party dependency changes.
