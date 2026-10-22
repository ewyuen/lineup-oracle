# Proposal

## Why

`POST /player_history` answers "what happened to this player" from the graph, but it is reachable only through the API and MCP. A small chat panel under Team news lets a visitor ask in plain words and see a cited answer in the page. This is phase 2 work: it sits on the unmerged `player-history-graph-rag` branch and must not change what the hackathon demo shows, so the panel is off unless switched on.

## What Changes

- Add an "Ask about a player" panel under the Team news panel: a text box (up to 300 characters, the API's limit) and an Ask button that send the question to `POST /player_history` and show that question and its answer in the panel, replacing the previous pair, without a page reload. Only one exchange is kept.
- Show each answer with its Template or AI marker (`llm_used`) and a collapsible list of the retrieved events (time, type, match, and the text of team news). No events found shows the API's "nothing found" answer and no list.
- Show API errors (unknown player, a question that could not be read, a question with no model configured) and an unreachable service as a message in the exchange, leaving the lineup and earlier messages as they are.
- Single turn: every question is sent alone, with no earlier messages or resolved player.
- The exchange survives lineup updates (club or fixture selection, news polls, team news) and is cleared by a language change, which also relocalizes the panel.
- The panel is optional: it renders only when the UI setting `PlayerHistory:Enabled` is true (default false), and no history request is made otherwise.
- Labels in English, Spanish and Traditional Chinese. Answer text is shown as the API returns it (English; see Out of scope).

Out of scope: follow-up questions or conversation memory; a `language` field on `/player_history` (answers stay English, the model's wording and the template); a History button on player cards; any API, MCP or graph change; Azure or Bicep changes (the setting is off in the deployed UI until chosen); persisting the exchange in cookies or on the server.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `lineup-ui`: adds requirements for the optional player-history chat panel, its answers, errors, persistence across in-page updates, and localization.

## Impact

- **ARCHITECTURE.md:** touches the **UI** contract section (a new optional panel and the `PlayerHistory:Enabled` setting) and the UI wireframe. It reads the existing `player_history` contract and does not change it. Updated in the same PR.
- **Code:** `ui/LineupOracle.Ui` only: `LineupApiClient` (one call and DTOs), `IndexModel` (one handler), a new `_PlayerHistory` partial placed in the rail, the four `UiText` resource files, a little CSS and a settings entry; tests in `ui/LineupOracle.Ui.Tests`.
- **Dependencies and infra:** none.
- **Branching:** this change is stacked on `feature/player-history-graph-rag` (it needs `/player_history`) and merges into that branch. The graph change is then archived and one PR goes to main, an exception to the "never into each other" rule that the user chose.
- **Risk:** the panel lives inside the swapped `#workspace`, so it must be kept across swaps or its exchange is lost (see design.md).
