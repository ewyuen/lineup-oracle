# Proposal

## Why

The system runs only on a laptop. The hackathon targets "Best Azure Cloud Native Integration", and judges need a live URL. Change 6 puts the API, the UI and the model on Azure with one repeatable command, and wires the OpenTelemetry traces ARCHITECTURE.md already promises.

## What Changes

- Add `infra/` with Bicep: Log Analytics, Application Insights, Container Registry, a Container Apps environment, a user-assigned managed identity, a Foundry (Azure AI services) account with a `gpt-4.1-mini` deployment, and two Container Apps (UI with public ingress, API with internal ingress only).
- Add a Dockerfile for the API (`backend/`) and one for the UI (`ui/`), and `infra/deploy.ps1` (infra, image build in ACR, apps updated to the new images).
- The API reaches the model with the managed identity (no API key). The deployment name and endpoint are passed as `LINEUP_LLM_*` environment variables; nothing is hardcoded.
- Add OpenTelemetry to the API and the UI through the Azure Monitor distro, switched on only when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set, so local runs and tests are unchanged.
- Add a GitHub Actions workflow: `pytest`, `dotnet test`, `az bicep build` (the CI item PLAN.md deferred to this change).
- Update ARCHITECTURE.md (Azure section: status, MCP is not hosted, ingress and identity details), README status and run steps.

Out of scope: Event Hubs, authentication, custom domains, custom telemetry or dashboards, autoscaling, persistent session storage, hosting the MCP adapter.

## Capabilities

### New Capabilities
- `azure-deployment`: the system deploys to Azure from the repo with one script; public UI, private API, keyless model access, safe behaviour when the model is missing.
- `telemetry`: API and UI export traces to Application Insights when configured, and are silent otherwise.

### Modified Capabilities
<!-- None: no existing requirement changes. -->

## Impact

- ARCHITECTURE.md: touches the Azure deployment component (planned to built) and the system-context note on the MCP server. Contracts (event schema, API, MCP tools) are unchanged.
- New: `infra/`, two Dockerfiles with `.dockerignore`, `.github/workflows/ci.yml`.
- Changed: `backend/pyproject.toml` (`azure-monitor-opentelemetry`), `backend/lineup_oracle/api.py` (telemetry hook), `ui/LineupOracle.Ui` (`Azure.Monitor.OpenTelemetry.AspNetCore`, `Program.cs`).

Assumptions to confirm:
- The Azure Sponsorship subscription has `gpt-4.1-mini` quota in the chosen region; Bicep creates the Foundry account and deployment itself. If quota is missing, pass the existing endpoint and deployment instead (a parameter, see design).
- Deploying and tearing down the real resources needs the user's approval; automated checks use `az bicep build`, `what-if` and local tests only.
