# Tasks

## 1. Setup

- [x] 1.1 Create branch `feature/remove-mcp-adapter` from `main` and verify it is the active branch.

## 2. Remove the adapter

- [x] 2.1 Delete the MCP server and its dedicated tests, remove the `mcp` backend dependency, and run the retained backend unit tests to verify the API and pipeline remain usable.
- [x] 2.2 Remove MCP component and contract claims from `ARCHITECTURE.md` and obsolete MCP status/run text from the root and backend READMEs; verify those docs no longer present the adapter as available. The stale Claude command is handled separately on `harness/remove-mcp-instructions` (PR #35); do not edit harness files on this feature branch.
- [x] 2.3 Keep the FastAPI and UI contracts unchanged; verify the API spec and route behavior have no unrelated changes.

## 3. Verify

- [x] 3.1 Run `python -m pytest -q` from `backend/` and confirm the full backend suite passes.
- [x] 3.2 Run `openspec validate remove-mcp-adapter` and confirm the delta validates.

## 4. Approval

- [x] 4.1 Stop for human approval after tests pass; only after approval, archive the OpenSpec change, open a PR from `feature/remove-mcp-adapter` to `main`, and merge it.
