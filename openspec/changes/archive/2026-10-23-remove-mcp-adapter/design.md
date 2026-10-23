# Design

## Context

See proposal.md for motivation. `ARCHITECTURE.md` currently describes the MCP adapter as a separate stdio process that forwards calls to FastAPI; the UI and agent pipeline do not depend on it. The adapter is isolated in `backend/lineup_oracle/mcp_server.py` with a dedicated test module and an `mcp` package dependency.

## Goals / Non-Goals

**Goals:**
- Remove the adapter and its unique dependency without changing the HTTP API or UI.
- Keep architecture and setup documentation consistent with the runtime.

**Non-Goals:**
- Remove or redesign API routes used by the adapter.
- Change agent orchestration, telemetry, Azure deployment, or user-facing features.
- Perform the broader submission README rewrite in this change.

## Decisions

- Delete the adapter module and its MCP-specific tests, and remove only the `mcp` package from backend dependencies. Keep `httpx`, which is used by other backend functionality.
- Remove the MCP component and contract from `ARCHITECTURE.md`; remove only statements that claim the adapter exists or describe how to run it in the READMEs. Do not rewrite unrelated README content here. The obsolete MCP command in `CLAUDE.md` is handled on the separate `harness/remove-mcp-instructions` branch, not this feature branch.
- Remove the `mcp-adapter` delta requirements so the maintained specifications no longer promise this integration. Keep all `lineup-api` requirements and implementation unchanged.
- Verify the removal with the full backend test suite and a reference search across the architecture and README files. The Claude guidance correction is tracked by the separate harness PR.

Alternatives considered: retain the adapter but omit it from the demo, or keep the optional dependency. Both leave unneeded code and packaging surface in the submission, so the cut is more complete and simpler.

## Risks / Trade-offs

- [Existing MCP clients lose this integration] → The adapter is not part of the planned demo; users can call the existing FastAPI endpoints directly.
- [A stale reference could mislead contributors] → Search runtime, tests, and docs for MCP references as part of implementation verification.

## Migration Plan

Remove the local stdio adapter and its dependency. No service migration or data change is required; the API and UI continue to run as before. Rollback is to restore the module, test, dependency, and documentation from the preceding revision.
