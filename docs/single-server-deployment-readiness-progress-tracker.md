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

- Current milestone: `M3_operational_rollout_and_recovery`
- Current task: `05_smoke_checks_backup_and_rollback_runbook`
- Active status: `done`
- Last updated: `2026-04-20 10:43 KST`
- Base branch: `master`
- Active branch: `codex/task-05-rollout-runbook`
- Latest task commit: `not created in this turn`
- Resume decision: `task_05_complete_first_pass_done_wait_for_next_request`
- Stop reason: `task_complete`

## Scope For Current Task

- Goal: `Add one repeatable one-server rollout and recovery slice: a checked-in smoke-check helper plus SQLite-first backup and rollback guidance aligned with the existing web, scheduler, and Caddy baseline`
- In scope: `one checked-in smoke-check script under scripts/, rollout plus recovery guidance in the single-server deployment guide and README, the smallest roadmap refresh needed to reflect the new baseline, and focused regression coverage for the script and docs`
- Out of scope: `In-app auth, runtime behavior changes, scheduler redesign, distributed deployment, backup automation, off-host retention systems, and live-publish behavior changes`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py -q`

## Roadmap Status

| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Deployment guide and production conventions | done | 2026-04-18 19:33 KST | Added the missing single-server docs set plus a dedicated deployment guide and linked it from existing operator docs |
| M1 | 02 | Runtime packaging and service units | done | 2026-04-20 09:12 KST | Added packaged uvicorn metadata, checked-in web and scheduler service units, a production env template, and deployment-asset regression coverage |
| M2 | 03 | Reverse proxy and domain assets for `sns.gilgop.cloud` | done | 2026-04-20 09:50 KST | Added checked-in Caddy plus Basic Auth assets, documented DNS or TLS expectations, and pinned the baseline with regression coverage |
| M2 | 04 | Remote console safety alignment | done | 2026-04-20 10:33 KST | README plus the operator console and control-plane API guides now all require the same loopback-only app binding and Caddy plus Basic Auth remote-access path |
| M3 | 05 | Smoke checks, backup, and rollback runbook | done | 2026-04-20 10:36 KST | Added a checked-in smoke helper plus SQLite-first backup and rollback guidance for the `/opt/sns-content-engine` server baseline |

## Changed Files For Active Task

- `README.md`
- `docs/single-server-deployment-guide.md`
- `docs/single-server-deployment-readiness-progress-tracker.md`
- `docs/single-server-deployment-readiness-roadmap.md`
- `scripts/single_server_smoke_check.sh`
- `tests/test_deploy_assets.py`
- `tests/test_scripts.py`

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
- 2026-04-20 10:18 KST: Switched from `codex/task-03-edge-proxy-assets` to `codex/task-04-remote-console-safety` and resumed Task `04` as the active implementation slice.
- 2026-04-20 10:19 KST: Verified that the console guide already points at the checked-in Caddy baseline, but the README and operator control-plane API guide still needed one explicit whole-surface rule for loopback-only app binding and protected remote access to the JSON routes.
- 2026-04-20 10:20 KST: Chose the smallest safe Task `04` shape: tighten README plus the console and API guides around the same `sns.gilgop.cloud` entry path, add one protected-route example for the control-plane API, and pin that documentation baseline in `tests/test_deploy_assets.py` without changing runtime behavior.
- 2026-04-20 10:23 KST: Updated `README.md`, `docs/operator-console-guide.md`, and `docs/operator-control-plane-api.md` so remote usage is consistently described as Caddy plus Basic Auth in front of a loopback-only FastAPI app, with `/health` remaining the only intentionally probeable unauthenticated route in the checked-in baseline.
- 2026-04-20 10:24 KST: Refreshed `docs/single-server-deployment-readiness-roadmap.md` and this tracker to record Task `04` completion and the narrower remaining gap around the rollout plus recovery runbook.
- 2026-04-20 10:33 KST: Added a documentation-alignment regression to `tests/test_deploy_assets.py` and reran the deployment-asset, API health, and full console slices successfully.
- 2026-04-20 10:34 KST: Prepared the Task `04` branch for commit, recorded the self-referential commit-note convention used by other initiative trackers, and kept the staged scope limited to the remote-access doc alignment plus deployment-asset regression coverage.
- 2026-04-20 10:36 KST: Switched from `codex/task-04-remote-console-safety` to `codex/task-05-rollout-runbook` and resumed Task `05` as the active implementation slice.
- 2026-04-20 10:36 KST: Verified that the checked-in deployment baseline now covers web, scheduler, and Caddy assets, but still stops short of one repeatable rollout smoke helper and an explicit SQLite backup or rollback order for the `/opt/sns-content-engine` server path.
- 2026-04-20 10:36 KST: Chose the smallest safe Task `05` shape: add one repo-backed smoke-check script that validates service status, loopback health, edge-protected console access, and dry-run `publish-due`, then document the matching backup, rollout, and rollback order without changing application behavior.
- 2026-04-20 10:36 KST: Added `scripts/single_server_smoke_check.sh`, updated `README.md` plus `docs/single-server-deployment-guide.md` with the new smoke helper and SQLite-first recovery runbook, and refreshed the roadmap snapshot so the final single-server readiness gap is now represented as intentionally manual operations rather than missing repository guidance.
- 2026-04-20 10:43 KST: Verified the new Task `05` baseline with focused scripts, operations, CLI, scheduler, and deployment-asset regressions. All targeted slices passed, so the first-pass single-server deployment-readiness roadmap can now be treated as complete.

## Test Log

- `2026-04-18 19:32 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k "healthcheck" -q` -> `passed` `5 passed, 33 deselected`
- `2026-04-18 19:32 KST` `PYTHONPATH=$PWD pytest tests/test_env.py -q` -> `passed` `2 passed`
- `2026-04-20 09:10 KST` `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py tests/test_api.py tests/test_console.py -q` -> `passed` `82 passed`
- `2026-04-20 09:10 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q` -> `passed` `59 passed`
- `2026-04-20 09:49 KST` `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py tests/test_api.py -k "health" -q` -> `passed` `1 passed, 41 deselected`
- `2026-04-20 09:50 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -q` -> `passed` `41 passed`
- `2026-04-20 10:31 KST` `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py -q` -> `passed`
- `2026-04-20 10:32 KST` `PYTHONPATH=$PWD pytest tests/test_api.py -k "health" -q` -> `passed`
- `2026-04-20 10:33 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -q` -> `passed`
- `2026-04-20 10:42 KST` `PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q` -> `passed` `7 passed`
- `2026-04-20 10:42 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py -q` -> `passed` `57 passed`
- `2026-04-20 10:42 KST` `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py -q` -> `passed` `6 passed`

## Open Questions

- `None currently`

## Blockers

- `None currently`

## Follow-up

- First-pass single-server deployment readiness is now in place. Future work, if needed, can automate backup retention or replace Basic Auth with a stricter edge-access pattern.

## Completion Summary

- Task `05` complete. The repository now carries a checked-in single-server smoke helper, a documented SQLite-first backup and rollback sequence, and an explicit non-destructive rollout order aligned with the existing web, scheduler, and Caddy deployment assets. The first-pass single-server deployment-readiness roadmap is complete, and no commit was created in this turn.
