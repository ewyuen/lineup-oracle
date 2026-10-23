# Design

## Context

See proposal.md for motivation. `ARCHITECTURE.md` already documents detailed contracts and describes that the mode switch is hidden; the current high-level diagrams have not been brought into alignment with those details.

The current implementation loads seeded synthetic data through `State.load`, starts the shared `Feed` from the FastAPI lifespan, and serves the Razor/HTMX UI from a public Azure Container App. The API Container App is internal. Both apps export telemetry to Application Insights when configured by deployment.

## Goals / Non-Goals

**Goals:**
- Make the diagrams show the actual runtime and deployment boundaries.
- Keep detail in the diagrams at component/flow level; API contracts and telemetry attributes remain in their existing prose.
- Keep the current-state and submission checklist in `PLAN.md` consistent with the built system and repository state.

**Non-Goals:**
- Change runtime code, deployment resources, API contracts, or the detailed pipeline/contract prose.
- Rewrite historical design decisions or tool-allocation notes that do not affect current status or submission readiness.
- Suggest that the UI exposes a mode selector or that the model chooses the XI.

## Decisions

- Represent data generation as producing synthetic roster and match/event data consumed by API startup. Do not depict the old standalone replay queue as a mandatory stage in live prediction; the FastAPI process owns the running shared news feed.
- Show browser-to-UI-to-API requests, including fixture/lineup/news actions, with the UI running in analyst mode by default and no visible mode control.
- Show the API's deterministic scoring/optimizer as the only XI selector. The optional Microsoft Agent Framework parser and explainer call the configured model; parsing may affect availability, explanations have a template fallback, and a model failure never prevents an XI response.
- Show the shared feed flowing through parsing and updating shared in-memory availability/predictions, while user-submitted team news is session-scoped. Keep implementation details such as feed cadence and telemetry span names in prose, not in the overview diagram.
- Update the Azure heading/status while preserving the already documented resources: Container Apps, Azure Container Registry, managed identity, optional Foundry deployment or existing endpoint, and Application Insights.

## Risks / Trade-offs

- [An overview diagram can imply a stronger guarantee than the implementation] → Verify every arrow and boundary against `State`, `Feed`, `Pipeline`, the UI client, and Bicep before editing.
- [Duplicate details may drift from the detailed contract sections] → Limit diagram labels to current components and principal flows; avoid restating endpoint payloads and observability attributes.

## Migration Plan

No runtime migration or rollback is needed. Update `ARCHITECTURE.md` and validate the Mermaid blocks and documentation consistency.
