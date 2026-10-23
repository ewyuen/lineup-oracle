# Design

## Context

See proposal.md for motivation. The root README currently introduces the product but offers only a partial Python setup, while separate backend, UI, and infrastructure READMEs contain deeper reference details.

## Goals / Non-Goals

**Goals:**
- Make the root README a complete, copyable local quick start for the Windows PowerShell workflow.
- Use the existing subsystem READMEs as linked references rather than duplicating their operational details.

**Non-Goals:**
- Change application behavior, supported platforms, dependencies, or deployment configuration.
- Rewrite detailed backend, UI, or Azure reference documentation.

## Decisions

- Keep the main path model-optional: install the backend, start the API, start the UI in a separate terminal, and confirm the API health endpoint. This gets the deterministic XI and template explanations running without Azure credentials or model configuration.
- Describe Foundry configuration as an optional enhancement, using the existing `.env.example` variable names and noting that valid endpoint and deployment values are required for model-assisted behavior.
- Walk through controls verified in the UI: fixture and club selection, lineup/explanations, structured injury/suspension/doubt actions, news ticker, and language selector. Do not promise a mode toggle that is not currently presented in the UI.
- Correct the status table based on the current repository and live deployment; retain the synthetic-data and evaluation caveat.

## Risks / Trade-offs

- [A setup command or feature description could drift from the app] → Verify commands against the project manifests and UI launch settings, and run the backend and UI test suites.
- [Optional model setup can distract from first run] → Keep it separate from the required quick-start steps and explain the no-model behavior.

## Migration Plan

No runtime migration is needed. Update the root README and validate its commands and links against the existing subsystem documentation.
