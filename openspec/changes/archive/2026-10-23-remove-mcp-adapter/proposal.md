# Proposal

## Why

The MCP adapter is not used by the API, UI, or planned demo, and the project plan identifies it as an early cut when time is short. Removing it reduces submission surface area and an unnecessary backend dependency before the final documentation pass.

## What Changes

- **BREAKING** Remove the standalone MCP server and its tests and dependency.
- Remove the MCP adapter capability from the maintained specifications and architecture overview.
- Remove only obsolete MCP usage/status text from the READMEs; broader submission README updates remain a separate next step.
- Keep the FastAPI endpoints and UI behavior unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mcp-adapter`: remove the requirement to expose the standalone MCP tools; this capability is no longer part of the submission.

## Impact

Touches `backend/lineup_oracle/mcp_server.py`, `backend/tests/test_mcp_server.py`, the `mcp` dependency in `backend/pyproject.toml`, the MCP contract in `ARCHITECTURE.md`, and obsolete MCP references in the root and backend READMEs. No API routes, UI behavior, deployment resources, or agent pipeline contracts change.
