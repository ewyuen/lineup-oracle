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
3. Switch the language (English, Spanish, Traditional Chinese) and the mode (analyst or fan).

## Status

| Part | State |
|---|---|
| Synthetic roster, event generator and replay | Built |
| P(start) scoring and XI optimizer | Built |
| FastAPI service and MCP server | Built |
| Agent pipeline and LLM explanations | Planned |
| Razor Pages and HTMX UI | Planned |
| Azure deployment (Bicep) | Planned |

## Try it

The backend needs Python 3.12 or newer. From the `backend/` folder:

```bash
pip install -e ".[dev]"
python -m pytest -q
python -m lineup_oracle.events --seed 42 --out data/events.jsonl
```

Run the API with `uvicorn lineup_oracle.api:create_app --factory`. More in [backend/README.md](backend/README.md). Run steps for the whole system will be added once the API, UI and deployment are built.

## More

- [ARCHITECTURE.md](ARCHITECTURE.md): the system, the contracts between parts, open decisions.
- [PLAN.md](PLAN.md): the working plan, deadlines and risks.
- [openspec/](openspec/): the specifications and change proposals the project is built from, one change at a time.
