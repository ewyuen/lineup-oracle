param([Parameter(Mandatory)][string]$UiUrl)
# Fails unless the UI page lists a fixture (a seeded club name appears in the HTML).
$html = (Invoke-WebRequest -Uri $UiUrl -UseBasicParsing -TimeoutSec 60).Content
if ($html -notmatch 'Harbor City') { Write-Error "Fixture name not found at $UiUrl"; exit 1 }
Write-Host "smoke ok: $UiUrl"
