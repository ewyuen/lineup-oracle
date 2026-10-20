# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## State of the repo

Implementation has started. Done and archived: `synthetic-data-and-replay` (the Python package `lineup_oracle` in `backend/`: seeded roster, event generator, async replay). Nothing else is built yet. The repo also holds [PLAN.md](PLAN.md) (agreed design, deadlines, risks), `openspec/` (specs and change proposals) and agent/skill config. Read PLAN.md before designing anything.

Backend commands, run from `backend/`: `python -m pytest -q` (all tests), `python -m pytest -q -k <name>` (one test), `python -m lineup_oracle.events --seed 42 --out data/events.jsonl` (generate events), `python -m lineup_oracle.roster` (rewrite the seeded `data/roster.json`). Details are in `backend/README.md`. No lint tooling yet.

Hackathon: Microsoft x Premier League "Inside the Game". Submission deadline is Oct 27, 2026, 11:59 PM PT. Solo build, so keep changes small.

## Workflow: OpenSpec

Work is organised as one OpenSpec change per step (spec-driven schema). Use the `/opsx:propose`, `/opsx:apply`, `/opsx:explore`, `/opsx:sync`, `/opsx:archive` commands (Claude commands in `.claude/commands/opsx`, Copilot equivalents in `.github/prompts`). Planned changes, in order: P(start) scoring and XI optimizer; FastAPI and MCP server; agent pipeline and LLM explanations; Razor/HTMX UI; Azure Bicep deployment.

Who builds what is in PLAN.md. Every change must:
- include unit tests for its new logic;
- be implemented on a feature branch `feature/<change-name>`, never on main;
- end with a human approval step after implementation and testing. Once the user approves, run the OpenSpec archive, then create a PR and merge it. Do not archive or merge before approval. `/opsx:apply` ends by suggesting `/opsx:archive`; ignore that and stop for approval instead.

Harness changes (CLAUDE.md, copilot-instructions, OpenSpec config, skills, prompts and other agent tooling) are not OpenSpec features. Make them on a branch `harness/<name>`, open a PR to main, and merge only after the user approves it. Feature branches merge to main the same way, never into each other.

These rules are enforced for OpenSpec artifacts in `openspec/config.yaml`.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system picture and contracts. A change that alters a contract or component must update it in the same PR.

## Gitignored

`.env`, `private/`, `__pycache__/`, `.venv/`, `bin/`, `obj/`.
