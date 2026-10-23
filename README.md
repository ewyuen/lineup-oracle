# Lineup Oracle

Lineup Oracle predicts which 11 players a club will start, before kick-off, and explains the pick in plain language. When late team news arrives (an injury, a suspension, a fitness doubt), the predicted XI updates.

Built for the Microsoft x Premier League "Inside the Game" hackathon, aiming at **Best Multi-Agent System** and **Best Azure Cloud Native Integration**.

## Why

Team news decides lineups, and it arrives late and as free text. A fan or analyst wants two things: the likely XI now, and a reason they can check. Lineup Oracle gives both, and it never lets an AI model make the pick itself.

## How it works

- **Deterministic code picks the XI.** Each player gets a transparent P(start) score from squad quality, recent starts and availability. An optimizer (a SciPy mixed-integer program) then picks the best legal XI for each formation and keeps the best one. No trained model.
- **The LLM only reads and explains.** It turns free-text team news into structured availability and writes the explanation. If it fails, the XI is still returned, with a template explanation.
- **A multi-agent pipeline on the Microsoft Agent Framework** runs the stages: ingest, interpret team news, pick the XI, explain, personalize.
- **Azure Container Apps and Microsoft Foundry** host the service and the model, with OpenTelemetry traces in Application Insights.

## All data is synthetic

The clubs, players, matches and team news are invented and generated from a seed. There are no real names, crests, logos or photos anywhere. The generator records the true XI of every match, so predictions can be scored honestly. The evaluation compares correct starters out of 11 with a "same XI as last match" baseline on held-out synthetic matches. It shows the pipeline works, not real-world accuracy.

## The demo

1. Pick a fixture and see the predicted XI with an explanation for each player.
2. Inject a late injury and watch the XI update.
3. Change the UI language (English, Spanish, or Traditional Chinese) and inspect the lineup probabilities and alternatives.

## Status

| Part | State |
|---|---|
| Synthetic roster, event generator and replay | Built |
| P(start) scoring and XI optimizer | Built |
| FastAPI service | Built |
| Agent pipeline and LLM explanations | Built |
| Razor Pages and HTMX UI | Built |
| Azure deployment (Bicep) | Deployed to Azure |

## Run locally

Prerequisites:
- Python 3.12 or newer
- .NET 10 SDK
- Windows PowerShell

### 1. Set up and start the backend

In a PowerShell terminal from the repository root:

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\uvicorn.exe lineup_oracle.api:create_app --factory
```

Leave this terminal running. The API starts on `http://127.0.0.1:8000`; it generates the seeded synthetic roster and match events in memory when data files are absent.

### 2. Start the UI

Open a second PowerShell terminal at the repository root:

```powershell
dotnet run --project .\ui\LineupOracle.Ui
```

Open [http://localhost:5281](http://localhost:5281). The UI uses the local API URL by default.

### 3. Check the API

In a third terminal, run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

The response should report `status: ok`.

The model is optional. If `LINEUP_LLM_ENDPOINT` and `LINEUP_LLM_DEPLOYMENT` are unset, the deterministic lineup still works and explanations use the built-in English template. To enable LLM-based free-text team-news parsing and model-written explanations, copy [.env.example](.env.example) to `.env`, replace the endpoint and deployment placeholders with valid values, then restart the API. An API key is optional when using Azure sign-in (`az login`). `.env` is gitignored; do not commit it.

### Run tests

From the repository root, with the backend virtual environment created above:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -q
dotnet test ui
```

## Walkthrough

1. In the UI, choose a fixture, then select its home or away club.
2. Review the predicted formation and starting XI. The analyst view shows each player's P(start) and explanation, along with available alternatives.
3. Use a player's **Injure**, **Suspend**, or **Doubt** action to submit structured team news. The lineup updates for your browser session; another visitor's personal update does not change yours.
4. Watch the shared news ticker. **Restart feed** replays the sample feed; feed items are applied to availability only when the model is configured.
5. Use the language selector to switch between English, Spanish, and Traditional Chinese. Without a configured model, the UI changes language but fallback explanations remain in English.

Typed free-text team news requires a configured model; without one, use the structured player actions above. For deeper backend commands, API details, and evaluation, see [backend/README.md](backend/README.md). For UI-specific setup and tests, see [ui/README.md](ui/README.md).

## Deploy to Azure

Needs the Azure CLI (with Bicep), PowerShell 7 and a signed-in subscription (`az login`). From the repo root:

```powershell
./infra/deploy.ps1 -ResourceGroup lineup-oracle-rg -Location westus3
```

It creates the resource group and infrastructure, builds both images in the registry, updates the apps and prints the public UI URL. Re-running updates the same resources. Teardown: `az group delete --name lineup-oracle-rg`. Parameters, the no-quota option and troubleshooting are in [infra/README.md](infra/README.md).

## More

- [ARCHITECTURE.md](ARCHITECTURE.md): the system, the contracts between parts, open decisions.
- [PLAN.md](PLAN.md): the working plan, deadlines and risks.
- [openspec/](openspec/): the specifications and change proposals the project is built from, one change at a time.

Live demo: [Lineup Oracle](https://lineup-ui.gentlepond-10ae1ea8.westus3.azurecontainerapps.io).
