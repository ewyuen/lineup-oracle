---
name: dev-start
description: Start the Lineup Oracle backend (API), frontend (UI) or both locally for development. Use when the user says "start the server", "run locally", "start backend", "start frontend", "start the UI", "run the app" or "dev start".
allowed-tools: Bash(python:*), Bash(uvicorn:*), Bash(dotnet:*), Bash(curl:*), PowerShell
---

One source for Claude Code and Copilot: this file lives in `.claude/skills/`, which both read.

## Ask (skip what the user already said)

Which to start: `backend`, `frontend` or `both` (default). The frontend needs the backend, so `frontend` alone only works if the API is already up on port 8000.

## Before starting

1. Check the ports are free: API 8000, UI 5281 (`Get-NetTCPConnection -LocalPort 8000,5281 -State Listen -ErrorAction SilentlyContinue`). If one is taken, tell the user what holds it and ask: reuse it (if it is the same app) or stop. Never kill a process unasked.
2. Backend only: `python -c "import lineup_oracle"` from `backend/`. If it fails, run `pip install -e .` there first.
3. `.env` in the repo root is optional. Without it, or without `LINEUP_LLM_API_KEY`, the API uses `az login` for the model or falls back to template explanations. Never print `.env` values.

## Start

Run each server in the background (`run_in_background`), so the session stays free, and start the backend first.

- **Backend**, from `backend/`: `uvicorn lineup_oracle.api:create_app --factory` (http://127.0.0.1:8000, docs at `/docs`). With no `data/events.jsonl` it generates the same data in memory, so nothing else is needed. If startup stops with an error about an old events file, regenerate it: `python -m lineup_oracle.events --seed 42 --out data/events.jsonl`.
- **Frontend**, from the repo root: `dotnet run --project ui/LineupOracle.Ui` (http://localhost:5281). It calls the API at `http://127.0.0.1:8000`; for another API address set `$env:LineupApi__BaseUrl` first.

Then check, once each and without a polling loop: `curl http://127.0.0.1:8000/health`, and the UI URL returns 200. Allow a few seconds for the `dotnet` build.

## Report

What is running, the URLs, and how to stop them (stop the background tasks; Ctrl+C in a terminal). Say plainly if a check failed, with the log output. The frontend runs the working tree as it is, uncommitted changes included.

## Not covered

MCP adapter (`python -m lineup_oracle.mcp_server`, stdio) and tests (`python -m pytest -q` in `backend/`, `dotnet test ui`); run them only when asked.
