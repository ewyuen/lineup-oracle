# Design

## Context

See proposal.md and the `lineup-ui` spec delta for motivation and observable behavior. The Razor Pages UI currently makes fixture, club, favourite, language, team-news, and retry requests with HTMX, but it has no in-flight status. These requests swap different targets: `#workspace`, `#lineup`, and `#app-shell`. The workspace and lineup may remain on screen while waiting, and language changes replace the application shell after the request finishes.

## Goals / Non-Goals

**Goals:**
- Give every current in-page HTMX interaction one consistent, accessible indication that work is pending.
- Keep the current rendered view visible until the existing response fragment is applied.
- Avoid showing a false percentage or other claim of measurable progress.

**Non-Goals:**
- Add a backend progress protocol, polling, or streaming.
- Change endpoint behavior, response fragments, or error/retry semantics.
- Lock the entire page while a request is active.

## Decisions

### Use an HTMX request indicator shared by the application shell

Add one localized status element with `role="status"` and a polite live announcement outside the replaceable workspace. Configure the application shell so its current and future in-page HTMX requests activate that indicator. Use HTMX's request lifecycle class and CSS for visibility, with an indeterminate visual spinner or equivalent. The response fragment continues to swap into its existing target; the indicator is independent of that content.

**Alternative considered:** Add separate indicators to the fixture picker, lineup, news form, and language control. Rejected because the multiple swap targets make this easy to implement inconsistently, and users would have to look in different places to know whether an action is still running.

### Preserve existing content and interaction behavior

Do not replace the workspace with a loading placeholder or block the whole page. Keep the last rendered content visible until the current handler returns, then let existing HTMX success and error handling apply. The status returns to its idle state when the request lifecycle ends.

**Alternative considered:** Cover the page with a blocking overlay. Rejected because the previous lineup is useful context and a long-running request should not make the whole UI appear unavailable.

### Show indeterminate activity, not estimated progress

Use a short localized status message and an indeterminate animation. Do not show percentages or a progress bar unless the backend later provides real progress data.

**Alternative considered:** A numeric progress bar based on elapsed time. Rejected because request duration is unknown and elapsed time is not a measure of backend completion.

## Risks / Trade-offs

- **The status flashes during fast requests** -> Delay its visual reveal slightly while keeping the accessible status tied to the HTMX request lifecycle.
- **The indicator is inside a fragment target and disappears during a swap** -> Keep it outside `#workspace` and `#lineup`; the shell swap for language completes as that response is applied.
- **Multiple requests overlap** -> The global status communicates pending work but does not serialize requests or resolve response ordering; retain the existing request/response behavior and avoid adding a page-wide interaction lock in this change.

## Migration Plan

No API or data migration is required. Add the shared status to the Razor UI, wire the HTMX indicator behavior and styling, test its presence and lifecycle across request types, and update `ARCHITECTURE.md`. Rollback is a code revert.
