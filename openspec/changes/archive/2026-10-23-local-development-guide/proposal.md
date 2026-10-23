# Proposal

## Why

The root README does not provide a complete local-development path and has outdated project status, so a first-time reviewer cannot reliably start the demo or understand how to try its main features. A concise setup guide and feature walkthrough will make the repository easier to run and evaluate before submission.

## What Changes

- Replace the abbreviated “Try it” section with copyable Windows PowerShell instructions for prerequisites, backend setup, API startup, UI startup, and a health check.
- Explain that model configuration is optional and describe the deterministic/template fallback versus model-assisted news parsing and explanations.
- Add a practical walkthrough of selecting a fixture, reading the predicted XI, testing team-news updates, and switching the UI language.
- Correct project status to reflect the built UI and current Azure deployment.
- Keep detailed backend, UI, and Azure references for deeper setup and operational details.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a documentation-only change; application behavior and contracts do not change.

## Impact

Touches the root `README.md` only. No application code, API/UI behavior, dependencies, or architecture contracts change. The existing [backend/README.md](../../backend/README.md), [ui/README.md](../../ui/README.md), and [infra/README.md](../../infra/README.md) remain the detailed references.
