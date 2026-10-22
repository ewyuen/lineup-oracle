# Tasks

## 1. Branch

- [x] 1.1 Confirm branch `feature/player-history-chat-ui` (branched from `feature/player-history-graph-rag`, not main) with `git branch --show-current`, and that `/player_history` exists in `backend/lineup_oracle/api.py`.

## 2. API client

- [x] 2.1 Add `AskPlayerHistoryAsync(question)` and the response DTO records to `LineupApiClient`; verify with stub-HTTP tests in `LineupApiClientTests` for a success body (events, `llm_used`), a 422 detail mapped to a failure, and an unreachable API mapped to unavailable.

## 3. Panel and handler

- [x] 3.1 Add the `PlayerHistory:Enabled` setting (false in `appsettings.json`, true in `appsettings.Development.json`) and `HistoryEnabled` on `IndexModel`; verify with a test that the panel is absent when unset or false.
- [x] 3.2 Add the `_PlayerHistory` partial under `_TeamNews` in the rail (form, 300-character box, `hx-preserve`, id including the language, transcript container) and the `_HistoryExchange` partial; verify with render tests for the panel when enabled, the `maxlength`, the preserve attribute and the language-keyed id.
- [x] 3.3 Add `OnPostHistoryAsync` (blank question sends nothing, 404 when disabled, success and error exchanges, unavailable message, lineup untouched); verify with handler tests using a stub client for each case, including that the request carries only the question.
- [x] 3.4 Render answers with the Template or AI marker and a collapsible event list (time, type, match, team-news text, omitted when empty), all HTML-encoded; verify with render tests for an AI answer with events, a template answer, no events, and a team-news event containing markup.

## 4. Localization and styling

- [x] 4.1 Add the panel keys (heading, placeholder, Ask, Template and AI markers, event list label, unavailable message) to `UiText.resx`, `.en`, `.es` and `.zh-Hant`; verify with a test that every new key exists and is non-empty in all four languages, and Spanish renders Spanish labels.
- [ ] 4.2 Add the panel CSS (chat bubbles, error style, disabled Ask while busy) and wire the shared busy indicator; verify manually in the browser at desktop and phone width.

## 5. Contracts and docs

- [x] 5.1 Update the UI section and wireframe in ARCHITECTURE.md (optional panel, `PlayerHistory:Enabled`, transcript persistence) and mention the setting in `backend/README.md` or the UI README; verify by reading them against the specs.

## 6. Verify and approve

- [ ] 6.1 Run `dotnet test ui`, `python -m pytest -q` from `backend/` and `openspec validate player-history-chat-ui --strict`; verify all green, then with the API, graph database and `PlayerHistory:Enabled` on, ask a question, select another club (transcript stays) and switch language (transcript clears), and check the panel is absent with the setting off.
- [ ] 6.2 Human approval gate: summarize results, then stop and wait for the user to approve. After approval, archive this change, merge `feature/player-history-chat-ui` into `feature/player-history-graph-rag`, complete and archive that change's gate (7.2), merge `main` into it, then open one PR to main and merge it.
