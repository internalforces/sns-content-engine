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

- Current milestone: `M2_edge_hardening_and_domain_routing`
- Current task: `03_reverse_proxy_and_domain_assets`
- Active status: `done`
- Last updated: `2026-04-20 10:05 KST`
- Base branch: `master`
- Active branch: `codex/task-03-edge-proxy-assets`
- Latest task commit: `not_created`
- Resume decision: `task_03_complete_pick_task_04_next`
- Stop reason: `none`

## Scope For Current Task

- Goal: `Add one preferred reverse-proxy path that exposes sns.gilgop.cloud over HTTPS while keeping the app private on loopback and preserving the manual-review safety model`
- In scope: `Checked-in reverse-proxy assets for sns.gilgop.cloud, one concrete edge-protection choice, the smallest doc alignment needed to explain that choice, and deployment-asset regression coverage`
- Out of scope: `In-app auth, scheduler redesign, distributed deployment, backup automation, live-publish behavior changes, and a broader operations rollback runbook`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py tests/test_api.py -k "health" -q`
  - `PYTHONPATH=$PWD pytest tests/test_console.py -q`

## Roadmap Status

| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Deployment guide and production conventions | done | 2026-04-18 19:33 KST | Added the missing single-server docs set plus a dedicated deployment guide and linked it from existing operator docs |
| M1 | 02 | Runtime packaging and service units | done | 2026-04-20 09:12 KST | Added packaged uvicorn metadata, checked-in web and scheduler service units, a production env template, and deployment-asset regression coverage |
| M2 | 03 | Reverse proxy and domain assets for `sns.gilgop.cloud` | done | 2026-04-20 09:50 KST | Added checked-in Caddy plus Basic Auth assets, documented DNS or TLS expectations, and pinned the baseline with regression coverage |
| M2 | 04 | Remote console safety alignment | pending | 2026-04-20 09:50 KST | Proxy path is now chosen; remaining work is the wider operator-doc sweep around that baseline |
| M3 | 05 | Smoke checks, backup, and rollback runbook | pending | 2026-04-18 19:27 KST | Final rollout and recovery slice |

## Changed Files For Active Task

- `README.md`
- `deploy/caddy/sns.gilgop.cloud.Caddyfile`
- `deploy/caddy/sns.gilgop.cloud.env.example`
- `docs/operator-console-guide.md`
- `docs/single-server-deployment-guide.md`
- `docs/single-server-deployment-readiness-progress-tracker.md`
- `docs/single-server-deployment-readiness-roadmap.md`
- `tests/test_deploy_assets.py`

## Progress Log

- 2026-04-18 19:27 KST: Switched from `master` to `codex/task-01-deployment-guide-baseline` and resumed Task `01` as the active implementation slice.
- 2026-04-18 19:27 KST: Verified the current deployment-sensitive behavior from code before editing docs: both the CLI and FastAPI app load the project `.env`, `DATABASE_URL` falls back to the repository default SQLite path, `/health` accepts `config_dir` and `database_url`, and readiness checks fail fast on placeholder config input.
- 2026-04-18 19:27 KST: Chose the smallest safe Task `01` shape: restore the missing single-server roadmap docs on `master`, add one dedicated single-server deployment guide, and defer service-unit, proxy, and rollback assets to later tasks.
- 2026-04-18 19:33 KST: Added the missing single-server initiative docs on `master`: vibe prompt, roadmap, execution guide, and progress tracker. Added `docs/single-server-deployment-guide.md` to standardize `/opt/sns-content-engine` layout, shared `.env` usage, SQLite-first guidance, loopback-only web binding, and the web/scheduler runtime split.
- 2026-04-18 19:33 KST: Linked the new deployment guide from `README.md` and `docs/operator-console-guide.md` so operators have one explicit entry point for personal-server rollout guidance.
- 2026-04-20 09:09 KST: Switched from `codex/task-01-deployment-guide-baseline` to `codex/task-02-runtime-packaging-assets` and resumed Task `02` as the active implementation slice.
- 2026-04-20 09:09 KST: Verified that `uvicorn` is still missing from `pyproject.toml`, the README only carries an inline scheduler unit example, and the deployment guide still treats checked-in service assets as deferred work.
- 2026-04-20 09:09 KST: Chose the smallest safe Task `02` shape: add runtime dependency metadata for `uvicorn`, check in dedicated `sns-web` and `sns-scheduler` units plus one production env template, and align the operator docs without changing runtime behavior.
- 2026-04-20 09:12 KST: Added `uvicorn` to the packaged runtime dependency set, checked in `deploy/systemd/sns-web.service` plus `deploy/systemd/sns-scheduler.service`, and added `.env.production.example` for the `/opt/sns-content-engine/.env` baseline described in the deployment guide.
- 2026-04-20 09:12 KST: Added `tests/test_deploy_assets.py` to pin the new deployment baseline and updated `.gitignore` so `.env.production.example` is versioned while private `.env.*` files remain ignored.
- 2026-04-20 09:12 KST: Aligned `README.md`, `docs/operator-console-guide.md`, and `docs/single-server-deployment-guide.md` so the one-server path now points at checked-in service assets instead of a manual `uvicorn` install or an inline scheduler-only unit example.
- 2026-04-20 09:46 KST: Switched from `codex/task-02-runtime-packaging-assets` to `codex/task-03-edge-proxy-assets` and resumed Task `03` as the active implementation slice.
- 2026-04-20 09:46 KST: Verified that the repository still lacks checked-in reverse-proxy assets and that the current docs stop at generic edge-protection guidance instead of one concrete `sns.gilgop.cloud` baseline.
- 2026-04-20 09:46 KST: Chose the smallest safe Task `03` shape: standardize on a checked-in Caddy reverse-proxy config with automatic HTTPS plus edge Basic Auth, keep the app on loopback, and add regression coverage for the new deployment assets.
- 2026-04-20 09:49 KST: Added `deploy/caddy/sns.gilgop.cloud.Caddyfile` and `deploy/caddy/sns.gilgop.cloud.env.example` as the repo-backed edge baseline. The checked-in config proxies only to `127.0.0.1:8000`, leaves `/health` open for simple probes, and protects every other route with edge Basic Auth.
- 2026-04-20 09:49 KST: Updated `README.md`, `docs/single-server-deployment-guide.md`, `docs/operator-console-guide.md`, and `docs/single-server-deployment-readiness-roadmap.md` so the repository now names Caddy plus Basic Auth as the preferred `sns.gilgop.cloud` path and documents DNS, TLS, and credential-file expectations.
- 2026-04-20 09:50 KST: Extended `tests/test_deploy_assets.py` to pin the new Caddy deployment assets and verified the health plus console regression slices after the docs and asset updates.
- 2026-04-20 10:05 KST: User requested a commit for the completed Task `03` slice, so the working tree is being closed out on `codex/task-03-edge-proxy-assets` without widening scope beyond the checked-in Caddy baseline, doc alignment, and deployment-asset regression coverage.

## Test Log

- `2026-04-18 19:32 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k "healthcheck" -q` -> `passed` `5 passed, 33 deselected`
- `2026-04-18 19:32 KST` `PYTHONPATH=$PWD pytest tests/test_env.py -q` -> `passed` `2 passed`
- `2026-04-20 09:10 KST` `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py tests/test_api.py tests/test_console.py -q` -> `passed` `82 passed`
- `2026-04-20 09:10 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q` -> `passed` `59 passed`
- `2026-04-20 09:49 KST` `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py tests/test_api.py -k "health" -q` -> `passed` `1 passed, 41 deselected`
- `2026-04-20 09:50 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -q` -> `passed` `41 passed`

## Open Questions

- `None currently`

## Blockers

- `None currently`

## Follow-up

- Task `04` should sweep the remaining operator-facing docs, especially API-facing guidance, so remote usage is always described as going through the chosen Caddy plus Basic Auth baseline.
- Task `05` should add the rollout smoke checklist, backup procedure, and rollback order on top of the now-checked-in web, scheduler, and proxy assets.

## Completion Summary

- Task `03` complete. The repository now carries a checked-in Caddy reverse-proxy baseline for `sns.gilgop.cloud`, keeps the FastAPI app private on loopback, uses edge Basic Auth for all non-health routes, documents the DNS and TLS expectations for automatic HTTPS, and pins the new assets with regression coverage. No commit was created in this turn.
