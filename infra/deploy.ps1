<#
.SYNOPSIS
  Deploys Lineup Oracle to Azure: infrastructure, both images built in ACR, apps on the new images.
.EXAMPLE
  ./infra/deploy.ps1 -ResourceGroup lineup-oracle-rg -Location swedencentral
  Re-running updates the same resources. Teardown: az group delete --name <ResourceGroup>
#>
param(
    [string]$ResourceGroup = 'lineup-oracle-rg',
    [string]$Location = 'swedencentral'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Invoke-Az {
    $out = & az @args
    if ($LASTEXITCODE -ne 0) { throw "az $($args -join ' ') failed" }
    $out
}

function Deploy-Infra {
    $text = (Invoke-Az deployment group create --resource-group $ResourceGroup --name lineup `
        --template-file "$PSScriptRoot/main.bicep" --parameters "$PSScriptRoot/main.bicepparam" `
        --query properties.outputs --output json) -join "`n"
    # az can print Bicep notices ("Bicep CLI is already installed...") before the JSON.
    $text.Substring($text.IndexOf('{')) | ConvertFrom-Json
}

Invoke-Az group create --name $ResourceGroup --location $Location --output none

# Pass 1 (placeholder images) only when the registry does not exist yet, so a re-run never
# swaps running apps back to the placeholder.
$registry = Invoke-Az acr list --resource-group $ResourceGroup --query '[0].name' --output tsv
if (-not $registry) {
    $env:API_IMAGE_TAG = ''; $env:UI_IMAGE_TAG = ''
    $registry = (Deploy-Infra).registryName.value
}

$tag = (git -C $root rev-parse --short HEAD).Trim()
# Queue without streaming the log (the CLI crashes printing it on a cp1252 Windows console), then poll.
function Build-Image($image, $context) {
    Invoke-Az acr build --registry $registry --image $image $context --no-logs --output none | Out-Null
    $run = Invoke-Az acr task list-runs --registry $registry --top 1 --query '[0].runId' --output tsv
    do {
        Start-Sleep -Seconds 10
        $status = Invoke-Az acr task show-run --registry $registry --run-id $run --query status --output tsv
    } while ($status -in 'Queued', 'Started', 'Running')
    if ($status -ne 'Succeeded') {
        throw "Build of $image ended as $status. Log: az acr task logs --registry $registry --run-id $run"
    }
    Write-Host "built $image ($run)"
}
Build-Image "lineup-api:$tag" "$root/backend"
Build-Image "lineup-ui:$tag" "$root/ui"

# Pass 2: same template, real images (adds the API health probes).
$env:API_IMAGE_TAG = $tag; $env:UI_IMAGE_TAG = $tag
$outputs = Deploy-Infra
$uiUrl = $outputs.uiUrl.value
Write-Host "UI: $uiUrl"

& "$PSScriptRoot/smoke.ps1" $uiUrl
exit $LASTEXITCODE
