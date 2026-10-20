# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## State of the repo

Pre-implementation. There is no source code, build, lint or test tooling yet. The repo holds only [PLAN.md](PLAN.md) (agreed design, deadlines, risks), `openspec/` (specs and change proposals) and agent/skill config. Read PLAN.md before designing anything. The first change, `synthetic-data-and-replay`, is proposed in `openspec/changes/` but not built.

Hackathon: Microsoft x Premier League "Inside the Game". Submission deadline is Oct 27, 2026, 11:59 PM PT. Solo build, so keep changes small.

## Workflow: OpenSpec

Work is organised as one OpenSpec change per step (spec-driven schema). Use the `/opsx:propose`, `/opsx:apply`, `/opsx:explore`, `/opsx:sync`, `/opsx:archive` commands (Claude commands in `.claude/commands/opsx`, Copilot equivalents in `.github/prompts`). Planned changes, in order: data generator and replay; P(start) scoring and XI optimizer; FastAPI and MCP server; agent pipeline and LLM explanations; Razor/HTMX UI; Azure Bicep deployment.

Who builds what is in PLAN.md. Every change must:
- include unit tests for its new logic;
- be implemented on a feature branch `feature/<change-name>`, never on main;
- end with a human approval step after implementation and testing. Once the user approves, run the OpenSpec archive, then create a PR and merge it. Do not archive or merge before approval.

Harness changes (CLAUDE.md, copilot-instructions, OpenSpec config, skills, prompts and other agent tooling) are not OpenSpec features. Make them on a branch `harness/<name>` and merge that branch to main by PR. Feature branches merge to main the same way, never into each other.

These rules are enforced for OpenSpec artifacts in `openspec/config.yaml`.

## Architecture (planned)

- **Data**: entirely synthetic. A seeded Python generator emits match, injury and suspension events for about 6 clubs over about 10 matchdays, from a swappable roster file. Names are invented aliases. The real-to-synthetic mapping lives in gitignored `private/` and must never be committed. No crests, logos or photos.
- **Pipeline**: Microsoft Agent Framework only (no LangGraph or AutoGen). Events replay through an in-process async queue with speed control. Stages: ingest, interpret, pick XI, explain, personalize.
- **Prediction**: P(start) is a transparent weighted score, with no trained model. A SciPy MILP runs once per formation, weighted by the club's formation prior. Deterministic code picks the XI. The LLM only parses team news and writes explanations. If the LLM fails, the API must still return an XI with a template explanation.
- **LLM**: gpt-4.1-mini on Foundry. The deployment name comes from an environment variable.
- **Backend**: FastAPI returns the formation, 11 players with P(start), alternatives per slot and explanations as JSON. Postgres for storage. A small MCP server exposes `predict_lineup`.
- **UI**: ASP.NET Razor Pages + HTMX, with an SVG pitch, live event feed and explanation panel. Analyst and casual-fan modes, English, Spanish and Traditional Chinese.
- **Azure**: Container Apps (two services), Postgres, Foundry, App Insights, Bicep. Secrets go in Container Apps secrets and an uncommitted `.env`.
- **Evaluation**: correct starters out of 11 versus a "same XI as last match" baseline, on held-out synthetic matches. It shows the pipeline works, not real-world accuracy.

## Gitignored

`.env`, `private/`, `__pycache__/`, `.venv/`, `bin/`, `obj/`.
