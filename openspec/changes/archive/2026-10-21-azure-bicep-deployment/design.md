# Design

## Context

ARCHITECTURE.md already fixes the shape: UI Container App calls API Container App, the API calls Foundry `gpt-4.1-mini`, both export to App Insights; Bicep, managed identity where possible, deployment name from an environment variable. See proposal.md for why.

Observed in the repo: the API is `uvicorn lineup_oracle.api:create_app --factory` with `/health`; seed data (`backend/data/events.jsonl`, `roster.json`) is committed. The UI is net10.0 and reads `LineupApi:BaseUrl` (env `LineupApi__BaseUrl`). The model is on only when `LINEUP_LLM_ENDPOINT` and `LINEUP_LLM_DEPLOYMENT` are set; with no `LINEUP_LLM_API_KEY` it uses `DefaultAzureCredential` (managed identity on Azure). The MCP adapter is a stdio process, so it cannot be a Container App. State is in memory, so one API replica (from the fastapi-and-mcp-server design).

## Goals / Non-Goals

**Goals:** one script from an empty resource group to a working public URL; no secrets in git; fallback behaviour unchanged when the model is missing; traces visible in App Insights.

**Non-Goals:** Event Hubs, authentication, custom domain, VNet, autoscaling, persistent state, hosting MCP, dashboards or alerts.

## Decisions

- **Layout:** `infra/main.bicep` (resource-group scope) plus one small module, `containerApp.bicep`, used twice; `infra/main.bicepparam` for defaults; `infra/deploy.ps1`. Alternative: `azd`. Rejected: adds a tool and a template format for two apps.
- **Compute:** Azure Container Apps (as ARCHITECTURE.md says). UI: external ingress, port 8080. API: internal ingress, port 8000. UI gets `LineupApi__BaseUrl=https://<api internal fqdn>`. API min and max replicas 1; UI also 1 (anti-forgery keys are in memory).
- **Identity:** one user-assigned managed identity shared by both apps, created before them so it can hold `AcrPull` on the registry and `Cognitive Services OpenAI User` on the Foundry account before the first revision starts. Alternative: system-assigned identity, rejected because the ACR pull role would not exist when the first revision pulls the image.
- **Model:** Bicep creates a `Microsoft.CognitiveServices/accounts` (kind `AIServices`, custom subdomain, local auth disabled) and one `gpt-4.1-mini` deployment; model name, version, SKU and capacity are parameters. The deployment name reaches the API only through `LINEUP_LLM_DEPLOYMENT`. Optional parameters `existingLlmEndpoint` and `existingLlmDeployment` skip creation for a subscription without quota (the role assignment is then left to the user, documented in `infra/README.md`). If the account is missing the API still starts (LLM off).
- **Secrets:** none needed because of managed identity, so no Container Apps secrets are created and `LINEUP_LLM_API_KEY` is never set. ARCHITECTURE.md says "secrets in Container Apps secrets"; it gets a note that there is nothing to store.
- **Images and the first-deploy cycle:** apps need an image that does not exist until ACR exists. `deploy.ps1` runs: (1) Bicep with a public placeholder image, (2) `az acr build` for both Dockerfiles tagged with the git short SHA, (3) Bicep again with the new tags. Same Bicep both times, so re-runs are idempotent.
- **Dockerfiles:** API: `python:3.12-slim`, `pip install ./backend`, copy `backend/data`, uvicorn on 0.0.0.0:8000. UI: multi-stage `dotnet/sdk:10.0` to `aspnet:10.0`, port 8080. Both run as non-root.
- **Health:** API uses an HTTP probe on `/health`; UI uses the default TCP probe (no new endpoint).
- **Telemetry:** a small `telemetry.py` in the backend calls `configure_azure_monitor()` and enables the Agent Framework's built-in tracing, both only if `APPLICATIONINSIGHTS_CONNECTION_STRING` is set; called once from `create_app`. UI: `UseAzureMonitor()` in `Program.cs`, only when the same variable is set. The distros instrument FastAPI, httpx and ASP.NET Core, which gives the UI-to-API trace link. The connection string is passed as a plain environment variable from the App Insights output. The exact Agent Framework switch is confirmed in task 3.1 before use.
- **CI:** one workflow, three jobs: `pytest` in `backend/`, `dotnet test` in `ui/`, `az bicep build` on `infra/main.bicep`. No deploy job; deployment stays manual.
- **Verification without spending money:** `az bicep build` and `az deployment group what-if` create no resources. The real deploy happens only at the approval gate.

## Risks / Trade-offs

- [No `gpt-4.1-mini` quota in the region] → region is a parameter; the existing-endpoint option; the app works without the model.
- [Deploying creates billable resources] → small SKUs (ACR Basic, Container Apps consumption, Log Analytics pay-as-you-go); `infra/README.md` documents `az group delete` teardown; the user approves the first real deploy.
- [In-memory sessions lost on restart or revision change] → accepted for the demo; replicas pinned to 1.
- [Role assignment propagation delay makes the first model call fail with 403] → the app falls back to templates; the README says to retry after a few minutes.
- [Placeholder image listens on a different port, so API probes would fail on the first pass] → the first pass omits the probe; the second pass, with real images, adds it.
- [Agent Framework tracing switch differs by version] → checked against the installed version in task 3.1.
