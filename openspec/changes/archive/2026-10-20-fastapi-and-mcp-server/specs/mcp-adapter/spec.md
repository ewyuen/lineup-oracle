## ADDED Requirements

### Requirement: Four tools forwarding to the API
The MCP server SHALL expose the tools `predict_lineup`, `submit_team_news`, `list_matches` and `get_match_xi`. Each tool SHALL call the matching API operation over HTTP with the same inputs and return the API's result, with no scoring, optimizing or state of its own.

#### Scenario: Tool list
- **WHEN** an MCP client lists the tools
- **THEN** exactly those four tools are listed, each with a description

#### Scenario: Forwarding
- **WHEN** a client calls `predict_lineup`
- **THEN** the server calls the API's predict operation with the same arguments and returns its result unchanged

#### Scenario: Flow through MCP
- **WHEN** a client submits an injury for a starter with `submit_team_news` and then calls `predict_lineup`
- **THEN** the second result does not contain that player

### Requirement: API errors are passed on
When the API answers with an error, the tool SHALL report the API's message to the client as a tool error. It SHALL NOT invent a result.

#### Scenario: Unknown match
- **WHEN** a tool is called with an unknown match id
- **THEN** the client receives an error that carries the API's message

### Requirement: API address from the environment
The MCP server SHALL read the API base URL from the environment variable `LINEUP_API_URL`, defaulting to `http://127.0.0.1:8000`.

#### Scenario: Custom URL
- **WHEN** `LINEUP_API_URL` is set
- **THEN** the tools call that address
