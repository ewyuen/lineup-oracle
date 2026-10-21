---
name: deploy-latest
description: Deploy the latest Lineup Oracle code to Azure. Backend only, client (UI) only, or both; from main, the current working tree, or a named branch. Use when the user says "deploy", "deploy latest", "deploy main", "deploy the backend", "deploy the UI" or "redeploy".
allowed-tools: Bash(pwsh:*), Bash(az:*), Bash(git:*), PowerShell
---

One source for Claude Code and Copilot: this file lives in `.claude/skills/`, which both read. All logic is in `infra/deploy.ps1`; this skill only picks its arguments.

## Ask (skip what the user already said)

1. **What**: `Backend` (the API image), `Client` (the UI image) or `Both`.
2. **Which code**:
   - `main`: latest main on origin.
   - current: the working tree as it is, uncommitted changes included. Warn if `git status --porcelain` is not empty.
   - a branch name or commit.
3. **Where**: default resource group `lineup-oracle2-rg`, location `westus3` (the live deployment). Confirm with `az group list -o table` if unsure.

Deploying is outward-facing and updates the live site. State the plan in one line (target, ref, resource group) and get a yes before running.

## Run

From the repo root, in PowerShell 7 (`az login` to the target subscription first):

```powershell
./infra/deploy.ps1 -ResourceGroup lineup-oracle2-rg -Location westus3 -Target <Both|Backend|Client> [-Ref <main|branch|sha>]
```

Leave `-Ref` out for the current working tree. With `-Ref`, the script fetches origin, builds from a temporary worktree and removes it afterwards, so the user's checkout and uncommitted work are not touched.

- It builds only the chosen image(s) in ACR (takes minutes; do not poll in a loop), then redeploys. The app that is not rebuilt keeps the image it runs now.
- It ends by running `infra/smoke.ps1`. Report its result as is. If it fails, say so and show the output; do not retry in a loop.
- Image tag is the short commit SHA; uncommitted builds get `-dirty-<timestamp>`.
- `Backend` or `Client` needs an existing deployment. On a fresh resource group use `Both`.

## Report

Target, ref and commit built, UI URL, smoke result. Say plainly if anything was not run.

## Not covered

Infra-only changes (Bicep edits) also go through this script, but it always rebuilds the chosen image. Teardown is `az group delete`, which only runs on an explicit request.
