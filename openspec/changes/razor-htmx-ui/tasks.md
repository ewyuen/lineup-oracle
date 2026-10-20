## 1. Setup and wireframe

- [ ] 1.1 Create the feature branch `feature/razor-htmx-ui` from main (it already exists if you are reading this on it).
- [ ] 1.2 Add an ASCII wireframe of the page to ARCHITECTURE.md (fixture picker, club toggle, mode and language controls, XI by lines, alternatives, team-news controls, message area) and update its UI section. Build the page from it.
- [ ] 1.3 Create the Razor Pages project `ui/LineupOracle.Ui` (net10.0) and the xUnit test project `ui/LineupOracle.Ui.Tests`; add both to a `ui/LineupOracle.sln`; vendor a pinned `htmx.min.js` into `wwwroot/`.

## 2. API client

- [ ] 2.1 Create `LineupApiClient` with records for matches, lineup, alternatives and errors, base URL from `LineupApi:BaseUrl` (default `http://127.0.0.1:8000`); map 4xx to a result with the API message and network failure to an "unavailable" result.
- [ ] 2.2 Unit tests with a stub handler: matches parsed; lineup parsed; 422 gives the API message; network failure gives unavailable; the configured base URL is used.

## 3. Page

- [ ] 3.1 Build `Pages/Index.cshtml` and the `_Lineup` and `_TeamNews` partials: fixture picker, club toggle, XI by lines, alternatives, preset buttons per picked player, free-text box, message area. Text only, no images.
- [ ] 3.2 Add the handlers: first load, `Lineup` (GET, fragment when `HX-Request` is present), and team-news POSTs (preset and text) with anti-forgery; success swaps `#lineup`, errors swap `#news-message` only.
- [ ] 3.3 Add the service-unavailable banner and inline API error messages, leaving the last XI untouched.
- [ ] 3.4 Unit tests with `WebApplicationFactory` and the stub API: fixture list rendered; XI shown in lines with names, numbers, explanations; alternatives listed and not in the XI; injury POST replaces the lineup and drops the player; HTMX request returns only the fragment; API down shows the banner and keeps the XI; 422 message shown; no `img` elements; base URL configuration used.

## 4. Personalization

- [ ] 4.1 Add analyst and fan modes (percentages, alternatives with percentages and the template or LLM badge versus names and explanation only) and send the mode with each prediction.
- [ ] 4.2 Add the language selector and `.resx` files for en, es and zh-Hant with English fallback; culture from a cookie; send the language with each prediction.
- [ ] 4.3 Add the favourite club cookie, the star control, preselection and the marker in the picker.
- [ ] 4.4 Unit tests: analyst shows a percentage for every player; fan shows no `p_start` number; switching mode keeps the same players; Spanish and Traditional Chinese labels appear; a missing key falls back to English; language and favourite club survive a reload; favourite preselects only when in the match, otherwise home; preferences unchanged after a news update.

## 5. Docs

- [ ] 5.1 Update ARCHITECTURE.md (UI section, system context) and add `ui/README.md` with how to run (`dotnet run --project ui/LineupOracle.Ui`) and test (`dotnet test ui`); update CLAUDE.md's commands only through a separate harness PR after merge.

## 6. Verify and approve

- [ ] 6.1 Run `dotnet test ui` and the backend suite (`cd backend && python -m pytest -q`) and fix any failure. If change 3 is merged, also run the UI once against the real API and walk the demo flow (pick a fixture, inject an injury, switch mode and language).
- [ ] 6.2 Human approval gate (HITL): stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR and merge it. Do not archive or merge before approval.
