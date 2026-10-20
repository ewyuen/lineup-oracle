## Context

See proposal.md for why. This is the first .NET code in the repo (`dotnet` SDK 10 is installed). The UI only talks to the FastAPI service defined in `fastapi-and-mcp-server`, which is not merged yet, so the API contract is read from that change's spec: `GET /matches`, `POST /predict_lineup`, `POST /team_news`. The UI never talks to the MCP server, the optimizer or the LLM. It has no database and no server-side session. Built by Copilot with a small model, so structure stays plain.

## Goals / Non-Goals

**Goals:**
- The demo flow in PLAN.md works on one page.
- The UI stays dumb: no scoring, no formation logic, no availability state.
- Fast to build: no JS framework, no bundler.

**Non-Goals:**
- Authentication, deployment, telemetry (change 6), live replay streaming, new API behavior.

## Decisions

- **Stack:** ASP.NET Razor Pages on `net10.0` with HTMX served as a pinned static file in `wwwroot/` (no CDN at runtime). Alternative: Blazor. Rejected, because ARCHITECTURE.md and the plan say Razor and HTMX, and HTMX needs no client runtime.
- **Layout:** `ui/LineupOracle.Ui/` (project) and `ui/LineupOracle.Ui.Tests/` (xUnit). One page `Pages/Index.cshtml` with partials: `_Lineup.cshtml` (XI and alternatives), `_TeamNews.cshtml` (controls and messages). Alternative: several pages. Rejected, since the demo is one screen.
- **API client:** one typed `HttpClient` wrapper `LineupApiClient` with records for the contract (matches, lineup, errors), base URL from `LineupApi:BaseUrl`. It turns a 4xx into a result carrying the API message and a network failure into an "unavailable" result, so pages never see exceptions. Alternative: call `HttpClient` from page handlers. Rejected, because the stub-based tests need one seam.
- **Page state:** all state is in the request (query string: match, club, mode) and cookies (language, favourite club). The last XI is not stored server-side: after a failed submission the handler returns an error fragment that HTMX swaps into the message area only, leaving the lineup element untouched. Alternative: re-fetch and re-render the XI on error. Rejected as extra API calls and a visible flicker.
- **HTMX use:** picking a match, club or mode does `hx-get` on `/?handler=Lineup` and swaps `#lineup`; a team-news button does `hx-post` and swaps `#lineup` on success and `#news-message` on an error status. The handler returns the fragment alone when the `HX-Request` header is present. Full page loads still work without JavaScript for the first view.
- **Anti-forgery:** the preset buttons and text form are POSTs, so use ASP.NET's built-in anti-forgery tokens with `hx-headers`. Cheap and standard.
- **Localization:** `.resx` resource files for en, es and zh-Hant using ASP.NET's built-in localization, culture chosen by a cookie (`ui-culture`) set from the language selector. English is the fallback for a missing key. Alternative: a hand-made dictionary. Rejected, since the framework already does fallback.
- **Modes:** one flag passed to the partial. Analyst shows percentages (`p_start` as whole percent), alternatives with percentages and the template or LLM badge (`llm_used`). Fan hides all numbers. Both modes always send the mode to the API.
- **Favourite club:** cookie `fav-club`. A star control in the fixture picker sets it; the page selects it if the match includes it, else the home club.
- **Wireframe:** an ASCII wireframe goes into ARCHITECTURE.md first (task 1), and the page is built from it. This closes the PLAN.md outstanding item.
- **Pitch rendering:** lines of text and CSS flex rows, no images or SVG assets, which also keeps rule 4.7 (no crests or photos) trivially true.
- **Tests:** xUnit with `WebApplicationFactory` and a stub `HttpMessageHandler` serving canned API JSON, so UI tests do not need the API running. One manual end-to-end run against the real API after change 3 is merged.

## Risks / Trade-offs

- [The API contract is not merged yet and could change in review] → The client records live in one file, and the stub JSON in the tests is copied from the API spec, so a contract change touches two places. Run the manual end-to-end check once change 3 is merged.
- [Small-model build of a first .NET project] → Tight tasks, one page, the wireframe first, tests with a stub, and my review before approval.
- [Free-text news is rejected by the API until change 4] → The UI shows the API's message as designed, so the box already works when the parser arrives.
- [Chinese text rendering depends on the viewer's fonts] → Rely on system fonts, no custom font files.
- [In-memory API state is lost on restart] → The UI reloads the lineup on each pick, so it never shows stale data longer than one interaction.
