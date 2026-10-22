# Azure deployment

`deploy.ps1` deploys the whole system with Bicep. See ARCHITECTURE.md (Azure deployment) for the design.

## Run

Needs the Azure CLI with Bicep, PowerShell 7 and `az login` to the target subscription.

```powershell
./infra/deploy.ps1 -ResourceGroup lineup-oracle-rg -Location swedencentral
```

Steps: create the resource group; deploy the infrastructure with a placeholder image (only when the registry does not exist yet); build `lineup-api` and `lineup-ui` in ACR, tagged with the git short SHA; deploy again with the real images; print the UI URL; run `smoke.ps1`. Re-running updates the same resources. The tag is the commit SHA, so commit before redeploying changed code.

Deploy only part, or other code: `-Target Backend|Client|Both` (default `Both`) rebuilds only that image and leaves the other app on the image it runs now; `-Ref <branch|sha>` builds that ref from a temporary worktree (default: the working tree, uncommitted changes included, tagged `<sha>-dirty-<time>`). The `deploy-latest` skill in `.claude/skills/` wraps this for Claude Code and Copilot.

Preview without creating anything:

```powershell
az deployment group what-if --resource-group <name> --template-file infra/main.bicep --parameters infra/main.bicepparam
```

Teardown: `az group delete --name lineup-oracle-rg`.

## Parameters (`main.bicep`)

| Parameter | Default | Meaning |
|---|---|---|
| `location` | resource group location | Region of all resources |
| `namePrefix` | `lineup` | Prefix of resource names |
| `apiImageTag`, `uiImageTag` | empty | Image tags; empty deploys the placeholder. Set by `deploy.ps1` through `API_IMAGE_TAG` and `UI_IMAGE_TAG` |
| `modelName`, `modelVersion` | `gpt-4.1-mini`, `2025-04-14` | Model to deploy |
| `modelSkuName`, `modelCapacity` | `GlobalStandard`, `30` | Deployment SKU and capacity (thousand tokens per minute) |
| `existingLlmEndpoint`, `existingLlmDeployment` | empty | Use a model you already have; no Foundry account is created. Environment variables `EXISTING_LLM_ENDPOINT` and `EXISTING_LLM_DEPLOYMENT` |

## Player-history graph (optional)

Off by default: without it `POST /player_history` answers from memory. To add the Postgres Flexible Server with Apache AGE (Burstable `Standard_B1ms`, PostgreSQL 16, public endpoint with TLS), set `GRAPH_ADMIN_PASSWORD` (letters and digits only, it goes into a URL) before `deploy.ps1`. The template then allow-lists and preloads `AGE`, and gives the API the `LINEUP_PG_URL` Container Apps secret. Not yet deployed or checked in a real subscription: confirm AGE is offered for the region and SKU first (otherwise leave it off; the demo then runs from memory).

After the first deployment:

1. `az postgres flexible-server restart --resource-group <rg> --name <graphHost output prefix>`: changing `shared_preload_libraries` needs a restart.
2. Load the graph from a machine that can reach the server (add your IP with `az postgres flexible-server firewall-rule create`): `LINEUP_PG_URL=<url with sslmode=require> python -m lineup_oracle.graph --load` from `backend/`. The loader creates the `age` extension itself.
3. Reload the same way after the roster or events change.

## No model quota

If the subscription has no `gpt-4.1-mini` quota in the region, either try another `-Location`, or set `EXISTING_LLM_ENDPOINT` and `EXISTING_LLM_DEPLOYMENT` before running the script. Grant the identity named `<prefix>-id-*` in the resource group the `Cognitive Services OpenAI User` role on that account yourself. With no model at all the app still works, with template explanations.

## Troubleshooting

- **403 from the model right after the first deploy:** the role assignment can take a few minutes to propagate. The app falls back to templates; retry after a few minutes.
- **Sessions reset:** team news is in memory, so a restart or new revision clears it.
