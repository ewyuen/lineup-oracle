# Design

## Context

See proposal.md. ARCHITECTURE.md (UI section) says the UI uses Razor Pages and HTMX, calls only the API, and that in-page features follow the HTMX convention. `/player_history` exists on the stacked branch `feature/player-history-graph-rag`: one of `question` (max 300 characters) or `filters`, returning `{filters, events, answer, cited_event_ids, llm_used}`, with 422 `{"detail": ...}` errors and no `language` field.

Observed in the UI:
- `#workspace` (rail with fixture picker and Team news, plus the lineup column) is swapped with `outerHTML` on club select and on `lineup-changed`; the language form swaps `#app-shell`.
- `IndexModel` handlers set a session cookie, call `LineupApiClient`, map `ApiResult` failures to inline errors, and return a partial. Settings use `configuration.GetValue` (for example `News:PollSeconds`).
- Text lives in four resx files; tests are rendering and handler `[Fact]`s plus stub-HTTP client tests.

## Goals / Non-Goals

**Goals:**
- A small, single-turn panel that never disturbs the lineup, and that is invisible unless enabled.
- UI-only: no API, MCP or graph change.

**Non-Goals:**
- Conversation memory or history of earlier exchanges, a `language` field, player-card History buttons, persisting the exchange.

## Decisions

**1. Panel placement and persistence.** The panel is a partial `_PlayerHistory` rendered inside the rail under `_TeamNews`, with `hx-preserve` and an id that includes the language (`history-panel-@Model.Language`). HTMX keeps a preserved element, with its exchange, when a swap brings an element with the same id; a language change swaps `#app-shell` with a different id, so the panel is re-rendered empty and relabelled. Rejected: placing the panel outside `#workspace` (changes the page layout and the rail's grid), and storing the exchange in a cookie or on the server (more state for a phase 2 feature).

**2. One handler.** `OnPostHistoryAsync(string question)` in `IndexModel`: trim, return an empty-exchange response for blank input without calling the API, otherwise call `LineupApiClient.AskPlayerHistoryAsync` and return a `_HistoryExchange` partial holding the question bubble and either the answer or the error. The form posts with `hx-post="/?handler=History" hx-target="#history-log" hx-swap="innerHTML"`, and the input is cleared after the request. The 300-character limit is set by `maxlength` and the API enforces it too (422 shown as an error). Rejected: sending prior turns (single turn was chosen).

**3. Client.** `AskPlayerHistoryAsync(string question)` posts `{question}` through the existing private `SendAsync<T>`, with DTO records for `HistoryEvent`, `PlayerHistoryResponse` matching the API fields. 422 maps to `ApiResult.Failure(detail)` and connection errors to `Unavailable`, as for the other calls.

**4. Flag.** `PlayerHistory:Enabled` read by `IndexModel` as `HistoryEnabled`; `appsettings.json` sets it false, `appsettings.Development.json` true. The partial renders nothing when false, and the handler returns 404 when false so the endpoint is not usable by a crafted request. Rejected: always on (it would change the hackathon demo, which must not depend on phase 2).

**5. Events display.** Events render in a `<details>` list: occurred time, type, match id and, for team news, `payload.text`. All text is Razor-encoded; the answer is plain text with line breaks preserved. Time formatting uses the invariant culture, as the answer text is English.

**6. Busy and errors.** The panel uses the shared busy indicator (`hx-indicator` on `#busy-indicator`) and the Ask button is disabled while a request is in flight. Errors use the existing inline error styling and do not retarget `#lineup`.

## Risks / Trade-offs

- **Preserved element not kept** (for example HTMX swaps by a different id) → a render test checks the id and `hx-preserve`, and a manual check selects a club after asking.
- **Without model credentials, free text returns 422** → shown as an error message; documented as expected, and explicit filters stay available through the API.
- **English-only answers under Spanish or Chinese UI** → recorded as out of scope; a `language` field is a phase 2 follow-up.
- **Stacked on an unmerged branch** → this change merges into `feature/player-history-graph-rag`; merge `main` into that branch before its one PR.

## Migration Plan

Additive. Setting `PlayerHistory:Enabled` to false (the default) removes the feature; no data or contract migration.
