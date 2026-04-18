# Single-Server Deployment Readiness Progress Tracker

## Usage

This file is the live implementation tracker for the Single-Server Deployment Readiness roadmap.

Update it:
- before starting a task
- during meaningful implementation progress
- after running tests
- when a blocker appears
- when the task is complete

## Current Status

- Current milestone: `M1_deployment_baseline_assets`
- Current task: `01_deployment_guide_and_production_conventions`
- Active status: `done`
- Last updated: `2026-04-18 19:33 KST`
- Base branch: `master`
- Active branch: `codex/task-01-deployment-guide-baseline`
- Latest task commit: `not_created`
- Resume decision: `task_01_complete_pick_task_02_next`
- Stop reason: `none`

## Scope For Current Task

- Goal: `Add a dedicated deployment guide that standardizes single-server layout, env handling, database decisions, and service split expectations for sns.gilgop.cloud`
- In scope: `A deployment guide, concrete runtime and storage conventions, and alignment with current healthcheck, review, and dry-run publish semantics`
- Out of scope: `Reverse-proxy implementation, in-app auth, scheduler redesign, distributed deployment, and live-publish behavior changes`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_cli.py -k "healthcheck" -q`
  - `PYTHONPATH=$PWD pytest tests/test_env.py -q`

## Roadmap Status

| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Deployment guide and production conventions | done | 2026-04-18 19:33 KST | Added the missing single-server docs set plus a dedicated deployment guide and linked it from existing operator docs |
| M1 | 02 | Runtime packaging and service units | pending | 2026-04-18 19:27 KST | Waiting for Task 01 |
| M2 | 03 | Reverse proxy and domain assets for `sns.gilgop.cloud` | pending | 2026-04-18 19:27 KST | Waiting for runtime and deployment conventions |
| M2 | 04 | Remote console safety alignment | pending | 2026-04-18 19:27 KST | Waiting for a concrete edge-proxy path |
| M3 | 05 | Smoke checks, backup, and rollback runbook | pending | 2026-04-18 19:27 KST | Final rollout and recovery slice |

## Changed Files For Active Task

- `README.md`
- `docs/operator-console-guide.md`
- `docs/single-server-deployment-guide.md`
- `docs/single-server-deployment-readiness-vibe-coding-prompt.md`
- `docs/single-server-deployment-readiness-roadmap.md`
- `docs/single-server-deployment-readiness-execution-guide.md`
- `docs/single-server-deployment-readiness-progress-tracker.md`

## Progress Log

- 2026-04-18 19:27 KST: Switched from `master` to `codex/task-01-deployment-guide-baseline` and resumed Task `01` as the active implementation slice.
- 2026-04-18 19:27 KST: Verified the current deployment-sensitive behavior from code before editing docs: both the CLI and FastAPI app load the project `.env`, `DATABASE_URL` falls back to the repository default SQLite path, `/health` accepts `config_dir` and `database_url`, and readiness checks fail fast on placeholder config input.
- 2026-04-18 19:27 KST: Chose the smallest safe Task `01` shape: restore the missing single-server roadmap docs on `master`, add one dedicated single-server deployment guide, and defer service-unit, proxy, and rollback assets to later tasks.
- 2026-04-18 19:33 KST: Added the missing single-server initiative docs on `master`: vibe prompt, roadmap, execution guide, and progress tracker. Added `docs/single-server-deployment-guide.md` to standardize `/opt/sns-content-engine` layout, shared `.env` usage, SQLite-first guidance, loopback-only web binding, and the web/scheduler runtime split.
- 2026-04-18 19:33 KST: Linked the new deployment guide from `README.md` and `docs/operator-console-guide.md` so operators have one explicit entry point for personal-server rollout guidance.

## Test Log

- `2026-04-18 19:32 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k "healthcheck" -q` -> `passed` `5 passed, 33 deselected`
- `2026-04-18 19:32 KST` `PYTHONPATH=$PWD pytest tests/test_env.py -q` -> `passed` `2 passed`

## Open Questions

- `Which edge protection path should be the preferred documented default for sns.gilgop.cloud: basic auth, IP allowlist, VPN, or a zero-trust gateway?`

## Blockers

- `None currently`

## Follow-up

- Task `02` should package `uvicorn`, add dedicated `sns-web` and `sns-scheduler` service units, and add a production-oriented env template that matches the new deployment guide.
- Task `03` should choose one concrete edge-protection path for `sns.gilgop.cloud` and add repo-backed reverse-proxy assets.

## Completion Summary

- Task `01` complete. The repository now carries the single-server deployment initiative docs on `master`, one dedicated deployment guide for the current one-server shape, and aligned entry points from the README and operator console guide. No commit was created in this turn.
