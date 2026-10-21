# Azure deployment

`deploy.ps1` deploys the whole system with Bicep. See ARCHITECTURE.md (Azure deployment) for the design.

## Run

Needs the Azure CLI with Bicep, PowerShell 7 and `az login` to the target subscription.

```powershell
./infra/deploy.ps1 -ResourceGroup lineup-oracle-rg -Location swedencentral
```

Steps: create the resource group; deploy the infrastructure with a placeholder image (only when the registry does not exist yet); build `lineup-api` and `lineup-ui` in ACR, tagged with the git short SHA; deploy again with the real images; print the UI URL; run `smoke.ps1`. Re-running updates the same resources. The tag is the commit SHA, so commit before redeploying changed code.

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

## No model quota

If the subscription has no `gpt-4.1-mini` quota in the region, either try another `-Location`, or set `EXISTING_LLM_ENDPOINT` and `EXISTING_LLM_DEPLOYMENT` before running the script. Grant the identity named `<prefix>-id-*` in the resource group the `Cognitive Services OpenAI User` role on that account yourself. With no model at all the app still works, with template explanations.

## Troubleshooting

- **403 from the model right after the first deploy:** the role assignment can take a few minutes to propagate. The app falls back to templates; retry after a few minutes.
- **Sessions reset:** team news is in memory, so a restart or new revision clears it.
