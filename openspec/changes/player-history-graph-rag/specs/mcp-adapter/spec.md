# Spec Delta

## MODIFIED Requirements

### Requirement: Four tools forwarding to the API
The MCP server SHALL expose the tools `predict_lineup`, `submit_team_news`, `list_matches`, `get_match_xi` and `ask_player_history`. Each tool SHALL call the matching API operation over HTTP with the same inputs and return the API's result, with no scoring, optimizing, retrieval or state of its own.

#### Scenario: Tool list
- **WHEN** an MCP client lists the tools
- **THEN** exactly those five tools are listed, each with a description

#### Scenario: Forwarding
- **WHEN** a client calls `predict_lineup`
- **THEN** the server calls the API's predict operation with the same arguments and returns its result unchanged

#### Scenario: Flow through MCP
- **WHEN** a client submits an injury for a starter with `submit_team_news` and then calls `predict_lineup`
- **THEN** the second result does not contain that player

#### Scenario: History through MCP
- **WHEN** a client calls `ask_player_history` with a player id
- **THEN** the server calls the player-history operation with the same arguments and returns its result unchanged
