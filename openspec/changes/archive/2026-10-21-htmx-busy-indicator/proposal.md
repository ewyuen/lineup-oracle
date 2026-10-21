# Proposal

## Why

Some HTMX requests can take long enough that users cannot tell whether their action was received or the page is still updating. A consistent, accessible busy status will make pending work clear while keeping the last rendered content available.

## What Changes

- Show an indeterminate, localized busy status while any current in-page HTMX interaction is in flight.
- Keep the current workspace and lineup visible while a request is pending; clear the status after success or failure.
- Ensure the busy state is announced accessibly and does not imply a measurable completion percentage.
- Document the UI behavior and add focused integration coverage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lineup-ui`: In-page HTMX requests expose an accessible busy state while pending and retain existing content until the server response is applied.

## Impact

- ASP.NET Razor Pages UI: shared application shell, HTMX request indicators, and CSS.
- UI integration tests for pending and completed request states across existing HTMX interactions.
- `ARCHITECTURE.md` to document the busy-state contract.
- No FastAPI contract or dependency changes.
