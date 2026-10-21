# Design

## Context

See proposal.md for motivation and the spec deltas for observable behavior. The Razor Pages UI already distinguishes HTMX requests and has async handlers for lineup loading and team news. Team-news and retry responses use focused partials; fixture and club forms still navigate, while language and favourite handlers redirect. The FastAPI contracts and the UI's cookie-based preferences remain unchanged.

The affected components are the Razor Page and its selection/preference handlers, the fixture, team-news, banner, and lineup fragments, their integration tests, and the UI contract in `ARCHITECTURE.md`.

## Goals / Non-Goals

**Goals:**
- Make all existing same-page fixture, club, favourite, language, team-news, and retry interactions asynchronous.
- Establish the same HTMX pattern as the default for future actions that update the current page in place.
- Keep dependent controls and form values synchronized with the selected fixture, club, and language.
- Preserve last-successful selection and lineup on failed predictions, with a retry for the requested selection.
- Keep keyboard-accessible form controls, anti-forgery protection on POSTs, and full-page fallbacks.

**Non-Goals:**
- Add a visible mode selector or change the current analyst-mode demo UX.
- Change API routes, request/response contracts, lineup selection logic, preference storage, or add client-side rendering.
- Convert ordinary document navigation, such as the brand link, into an asynchronous interaction.
- Force downloads or actions that change document context through HTMX.

## Decisions

### Keep Razor Pages handlers as the request boundary

Use the existing page handlers and `LineupApiClient`; choose full-page versus fragment responses based on the HTMX request header. Successful HTMX requests return only the server-rendered fragment needed for that interaction. Non-HTMX requests continue to return a page or redirect as they do today.

**Alternative considered:** Add separate Minimal API or controller endpoints. Rejected because the UI already uses Razor Page handlers and partials, and a second endpoint style would duplicate binding, validation, localization, and rendering logic without changing the API contract.

### Use a shared workspace for successful selection changes

Group the fixture picker, team-news form, and lineup under a stable workspace target. Successful fixture and club selections return a replacement workspace so the selected fixture, default/favourite club, hidden form values, player actions, and lineup all reflect the same server-side model. Favourite changes use the same boundary because they can change the active club and lineup. Push the successful fixture/club selection into browser history so the URL remains useful and refreshable.

On a failed selection prediction, do not replace the workspace. Return an error update and restore the picker to its last successful values; preserve the requested match and club in the retry action. This avoids showing controls for one fixture alongside a lineup or player actions for another.

**Alternative considered:** Swap only the lineup and update controls out-of-band. Rejected because it makes synchronization dependent on several independently targeted fragments and is easier to leave stale hidden fields or selected-state markup.

### Refresh the application shell for language changes

The language preference changes labels throughout the page, so its HTMX response replaces the server-rendered application shell rather than only the lineup. Save the existing language cookie and set the request's UI culture before rendering localized strings and requesting the lineup. Keep the selected fixture, club, mode, and favourite values in the request. On an API failure, update the localized error state while retaining the last successful lineup.

**Alternative considered:** Keep the current redirect after saving the cookie. Rejected for HTMX requests because it would return the user to a full document navigation rather than an in-place update.

### Preserve existing team-news and retry response behavior

Keep the focused lineup, news-message, and service-banner targets for player presets, free-text news, and retry. Maintain the existing anti-forgery token on POST forms and the same API error text and retry semantics. Returned fragments retain their HTMX attributes so subsequent interactions continue working after swaps.

### Preserve progressive enhancement

Keep valid form actions and methods for requests without HTMX. The same handler must continue to render a full page or use the existing redirect path when the request is not HTMX; no JavaScript-only action should be required to select a fixture, select a club, save a preference, or submit news.

### Make HTMX the default for future in-page updates

Treat an action as an in-page update when its result changes the current view without taking the user to a different document context. Implement those actions with HTMX and server-rendered HTML fragments, following the same partial and error-handling conventions. Ordinary navigation and file downloads remain valid non-HTMX requests. Record this convention in `ARCHITECTURE.md` so later UI changes have a durable reference.

## Risks / Trade-offs

- **A fragment omits a dependent control or hidden value** → Integration tests assert the complete swapped workspace and selected state after each interaction.
- **A failed selection leaves attempted and displayed state inconsistent** → Keep the last successful workspace intact and put the requested selection only in the retry action until it succeeds.
- **Localized fragments use the prior request culture** → Set the selected culture for the current request before rendering and test all supported languages.
- **Overlapping requests can return out of order** → Keep requests scoped to the relevant target and use HTMX synchronization where needed so the final UI reflects the latest user selection.

## Migration Plan

No data or API migration is required. Add the HTMX attributes and fragment rendering, update integration tests and `ARCHITECTURE.md`, then run the UI tests and full backend test suite. Rollback is a code revert; existing full-page handlers remain available as fallback behavior.
