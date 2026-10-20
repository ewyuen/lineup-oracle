## Why

The product has no face yet. The demo (PLAN.md) needs a page where a judge picks a fixture, sees the predicted XI with explanations, injects a late injury, watches the XI update, then switches language and fan mode. The API from change 3 defines what the UI can show.

## What Changes

- Add an ASP.NET Razor Pages app in `ui/` with HTMX for partial updates, no JavaScript framework and no build step.
- One main page: a fixture picker, a club toggle (home or away), and the predicted XI drawn by formation lines (goalkeeper, defenders, midfielders, forwards), each player with name, number and explanation, plus the alternatives per position.
- Team-news controls on the page: a preset button per picked player (injury, suspension, doubt) that sends a structured submission, and a free-text box. The XI updates in place through an HTMX swap.
- Personalization: mode (analyst or fan), language (en, es, zh-Hant) for the page text, and a favourite club remembered in a cookie that pre-selects the club.
- Analyst mode shows `p_start` and the "template or LLM" badge; fan mode hides the numbers and keeps short text.
- Show the API's rejection messages inline (for example free text not yet parsed), and a clear banner with a retry button when the API is unreachable, without losing the last XI on screen.
- Style the page from the Stitch design in `design-reference/` (hand-written CSS, no CDN), keeping the parts the API can support and cutting the rest (`ui-design-guide.md`).
- Send a stable per-browser `session_id` (cookie) with every API call, so visitors' team news stays separate.
- Add an ASCII wireframe of the page to ARCHITECTURE.md (this closes the outstanding PLAN.md item) and update the UI section there.
- Add an xUnit test project that runs the UI against a stub API.

Contracts and components touched (from ARCHITECTURE.md): the UI component and its place in the system context, the `predict_lineup` and `submit_team_news` contracts as the UI's only consumers (no change to them), and the Personalize stage (the UI applies mode, language and favourite club display; the API only echoes them until change 4). The API (change 3) is merged, so end-to-end checks run against the real service.

Out of scope: authentication, Azure deployment and OpenTelemetry (change 6), live replay streaming to the page, LLM explanations in other languages (change 4), crests, logos or photos.

## Capabilities

### New Capabilities
- `lineup-ui`: the page, the XI display, the team-news controls, in-place updates and error display.
- `ui-personalization`: mode, language and favourite club.

### Modified Capabilities

None.

## Impact

- New `ui/` folder: the Razor Pages project and its test project.
- ARCHITECTURE.md gains the wireframe and the UI section details; `backend/README.md` or a new `ui/README.md` gains run instructions.
- CLAUDE.md gains the `dotnet` commands only through a separate harness PR after merge.
