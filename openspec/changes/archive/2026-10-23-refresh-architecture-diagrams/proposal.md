# Proposal

## Why

The architecture diagrams no longer fully represent the shipped system: the overview suggests a UI mode selector, omits the API's shared news feed and session-specific state, and the Azure section still describes the deployment as not live. Updating the diagrams and their adjacent status labels will make the architecture document reliable for reviewers and hackathon submission.

## What Changes

- Refresh the system-context diagram to show synthetic data loaded by the API, the browser UI's HTTP interactions, the API's deterministic lineup selection and optional model-assisted parsing/explanations, and the shared news-feed flow.
- Refresh the Azure deployment diagram to match the deployed UI/API Container Apps, public/internal ingress, registry, managed identity, optional Foundry model, and Application Insights.
- Correct adjacent text that contradicts current UI and deployment behavior, including the hidden mode switch and live deployment status.
- Reconcile `PLAN.md`'s current-state and outstanding-submission sections with the implemented architecture, merged MCP/tooling cleanups, public repository, and remaining submission deliverables.
- Keep the diagrams focused on component relationships; detailed contracts and telemetry notes remain in their existing sections.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change updates documentation only and does not alter behavior or contracts.

## Impact

Touches `ARCHITECTURE.md` and `PLAN.md` only. No application code, API, infrastructure, dependencies, or runtime behavior changes.
