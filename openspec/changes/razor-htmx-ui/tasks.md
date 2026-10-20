## 1. Setup and wireframe

- [ ] 1.1 Create the feature branch `feature/razor-htmx-ui` from main (it already exists if you are reading this on it).
- [ ] 1.2 Read `ui-design-guide.md` and look at `design-reference/` (screens 1, 3 and 5 first). Add an ASCII wireframe of the page to ARCHITECTURE.md (fixture picker, club toggle, mode and language controls, four formation tiers with alternatives strips, team-news box, message area, degraded banner) and update its UI section. Build the page from it.
- [ ] 1.3 Create the Razor Pages project `ui/LineupOracle.Ui` (net10.0) and the xUnit test project `ui/LineupOracle.Ui.Tests`; add both to a `ui/LineupOracle.sln`; vendor a pinned `htmx.min.js` into `wwwroot/`.

## 2. API client

- [ ] 2.1 Create `LineupApiClient` with records for matches, lineup (including `llm_used` and `alternatives` per position) and errors, base URL from `LineupApi:BaseUrl` (default `http://127.0.0.1:8000`); every prediction and team-news call carries `mode`, `language` and `session_id`; map 4xx to a result with the API message (`{"detail": text}`) and network failure to an "unavailable" result.
- [ ] 2.2 Unit tests with a stub handler: matches parsed; lineup parsed; 422 gives the API message; network failure gives unavailable; the configured base URL is used; the request body carries `session_id`.

## 3. Page

- [ ] 3.1 Write `wwwroot/css/site.css` from the tokens in `design-reference/DESIGN.md` (CSS variables for colours, type and spacing; dark theme; two columns from 1024px, one column below; `.htmx-swapping` fade). No CDN, no Tailwind, no icon font, no images.
- [ ] 3.2 Build `Pages/Index.cshtml` and the partials `_FixturePicker`, `_Lineup`, `_PlayerCard`, `_TeamNews` and `_Banner`, following `ui-design-guide.md`: picker with club toggle, four formation tiers (forwards on top, goalkeeper at the bottom) with an alternatives strip under each, a card per player with Injure, Suspend and Doubt buttons, the free-text box and message area. Text only.
- [ ] 3.3 Add the handlers: first load, `Lineup` (GET, fragment when `HX-Request` is present), and team-news POSTs (preset and text) with anti-forgery; success swaps `#lineup` and writes a message ("<player> marked <kind>; XI updated"), errors swap `#news-message` only.
- [ ] 3.4 Add the session cookie (`session-id`, random, created on first visit) and send it on every API call.
- [ ] 3.5 Add the service-unavailable banner with a retry button and the inline API error messages, leaving the last XI untouched.
- [ ] 3.6 Unit tests with `WebApplicationFactory` and the stub API: fixture list rendered; XI shown in tiers with names, numbers, explanations; alternatives listed and not in the XI; injury POST replaces the lineup, drops the player and shows the message; HTMX request returns only the fragment; API down shows the banner and keeps the XI; retry reloads; 422 message shown; no `img` elements; no invented figures (no text such as "confidence", "latency", "win probability"); base URL configuration used; two first visits get different session ids and later calls reuse one.

## 4. Personalization

- [ ] 4.1 Add analyst and fan modes (percentages in green, amber below 50%; alternatives with percentages; one Template or AI badge per lineup versus names and explanation only) and send the mode with each prediction.
- [ ] 4.2 Add the language selector and `.resx` files for en, es and zh-Hant with English fallback; culture from a cookie; send the language with each prediction. Every label, button, heading and message goes through the resource files (the mockups left some English in the Spanish screens).
- [ ] 4.3 Add the favourite club cookie, the star control, preselection and the marker in the picker.
- [ ] 4.4 Unit tests: analyst shows a percentage for every player; fan shows no `p_start` number and no badge; switching mode keeps the same players; Spanish and Traditional Chinese labels appear; every resource key exists in all three languages; a missing key falls back to English; language and favourite club survive a reload; favourite preselects only when in the match, otherwise home; preferences unchanged after a news update.

## 5. Docs

- [ ] 5.1 Update ARCHITECTURE.md (UI section, system context) and add `ui/README.md` with how to run (`dotnet run --project ui/LineupOracle.Ui`, API at `LineupApi:BaseUrl`) and test (`dotnet test ui`); update CLAUDE.md's commands only through a separate harness PR after merge.

## 6. Verify and approve

- [ ] 6.1 Run `dotnet test ui` and the backend suite (`cd backend && python -m pytest -q`) and fix any failure. Run the UI once against the real API (`uvicorn lineup_oracle.api:create_app --factory`) and walk the demo flow (pick a fixture, inject an injury, switch mode and language, stop the API and check the banner).
- [ ] 6.2 Human approval gate (HITL): stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR and merge it. Do not archive or merge before approval.
