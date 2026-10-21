## 1. Setup

- [x] 1.1 Create the feature branch `feature/azure-bicep-deployment` from main (it already exists if you are reading this on it). Verify: `git branch --show-current` prints it. (Done on a detached HEAD at the branch tip, because the branch is checked out in another worktree; pushed by refspec, so `git branch --show-current` prints nothing here.)
- [x] 1.2 Read ARCHITECTURE.md (Azure section) and check `az bicep version` and `docker --version` work. Verify: both print a version.

## 2. Container images

- [x] 2.1 Add `backend/Dockerfile` (python 3.12 slim, installs the package, includes `backend/data`, non-root, uvicorn on 0.0.0.0:8000) and `backend/.dockerignore`. Verify: `docker build backend` succeeds and `docker run -p 8000:8000` answers `GET /health` with 200 and the matches endpoint with the fixture list.
- [x] 2.2 Add `ui/Dockerfile` (multi-stage dotnet sdk 10 to aspnet 10, non-root, port 8080) and `ui/.dockerignore`. Verify: `docker build ui` succeeds; running it with `LineupApi__BaseUrl` pointing at the API container serves the page at `/`.
- [x] 2.3 Add `infra/smoke.ps1 <ui-url>`, which GETs `/` and fails unless a fixture name is in the HTML. Verify: it passes against the two local containers.

## 3. Telemetry (with tests)

- [ ] 3.1 Add `azure-monitor-opentelemetry` to `backend/pyproject.toml`; confirm in the installed Agent Framework version how its built-in tracing is switched on. Verify: the import and the switch name are stated in the commit message.
- [ ] 3.2 Add `backend/lineup_oracle/telemetry.py` (`setup_telemetry(env)`: no-op unless `APPLICATIONINSIGHTS_CONNECTION_STRING` is set; otherwise `configure_azure_monitor()` plus the Agent Framework switch) and call it from `create_app`. Verify: unit tests with a fake env and a patched `configure_azure_monitor` show it is not called when the variable is unset and called once when set.
- [ ] 3.3 Add `Azure.Monitor.OpenTelemetry.AspNetCore` to the UI and call `UseAzureMonitor()` in `Program.cs` only when the variable is set. Verify: a `WebApplicationFactory` test starts the app with the variable unset and the page loads; `dotnet test ui` passes.
- [ ] 3.4 Run `python -m pytest -q` and `dotnet test ui`. Verify: all existing and new tests pass.

## 4. Bicep

- [ ] 4.1 Write `infra/main.bicep` with Log Analytics, App Insights, ACR (Basic, admin off), the Container Apps environment, a user-assigned identity with `AcrPull`, and parameters (location, name prefix, image tags, model name, version, capacity, optional existing endpoint and deployment). Verify: `az bicep build --file infra/main.bicep` has no errors or warnings.
- [ ] 4.2 Add the Foundry account (AIServices, local auth disabled), the `gpt-4.1-mini` deployment and the `Cognitive Services OpenAI User` role for the identity, all skipped when the existing-endpoint parameters are set. Verify: `az bicep build` is clean and the endpoint and deployment name appear as outputs in the compiled template.
- [ ] 4.3 Add `infra/containerApp.bicep` and the two apps: UI external on 8080 with `LineupApi__BaseUrl` and the App Insights connection string; API internal on 8000 with `LINEUP_LLM_ENDPOINT`, `LINEUP_LLM_DEPLOYMENT`, the connection string, min and max replicas 1 and a `/health` probe (real images only); no `LINEUP_LLM_API_KEY`, no secrets. Verify: `az bicep build` is clean; `grep -ri "api_key\|secret" infra/` finds only comments.
- [ ] 4.4 Add `infra/main.bicepparam` with defaults and `infra/deploy.ps1` (create the resource group, Bicep with the placeholder image, `az acr build` for both images tagged with the git short SHA, Bicep again, print the UI URL, run `smoke.ps1`). Verify: `az deployment group what-if` against a new resource group name runs and lists the expected resources (nothing is created).
- [ ] 4.5 Add `.github/workflows/ci.yml` with three jobs (pytest, dotnet test, bicep build). Verify: the workflow runs green on the PR.

## 5. Docs

- [ ] 5.1 Update ARCHITECTURE.md (Azure section: built, ingress, identity, no secrets needed, MCP is stdio and not hosted, OpenTelemetry wiring) and the README status row and deploy and teardown steps, and add `infra/README.md` (parameters, the no-quota option, the 403 retry note). Verify: every documented command was run as written or is marked "not run".

## 6. Full run and approval

- [ ] 6.1 Run `python -m pytest -q`, `dotnet test ui` and `az bicep build --file infra/main.bicep`. Verify: all pass.
- [ ] 6.2 Live deploy gate: ask the user to approve a real deploy to the Azure Sponsorship subscription. If approved, run `infra/deploy.ps1` and verify that the UI URL loads, a prediction returns an XI, a free-text news message is parsed by the model, and a trace appears in App Insights; record the results in the PR. If not approved, say plainly that the live deployment is untested.
- [ ] 6.3 Human approval gate (HITL): summarize results and stop for the user's approval. After approval, run the OpenSpec archive, then open a PR and merge it. Do not archive or merge before approval.
