# Single-Server Deployment Readiness Roadmap

## Goal

Extend the current local-and-operator-first implementation into a single-server deployment-ready baseline that:
- can run the web console and scheduler safely on one personal server under `sns.gilgop.cloud`
- codifies repeatable runtime, environment, and service-layout decisions inside the repository
- keeps the current manual-review gate, dry-run-first publish defaults, and env-only credential model intact
- documents edge protection, HTTPS, smoke checks, backup, and rollback expectations before the first live rollout

## Current implementation snapshot

### Already implemented

- The repository already exposes a FastAPI application with `/health` plus server-rendered `/console/...` pages.
- The CLI already supports `scheduler run`, `publish-due`, `healthcheck`, review actions, and database bootstrap or upgrade flows.
- The project already uses environment-driven secrets, includes `.env.example`, and ships a small project-local `.env` loader.
- The repository now ships checked-in single-server runtime assets: `sns-web` and `sns-scheduler` `systemd` units, `.env.production.example`, and a Caddy reverse-proxy baseline for `sns.gilgop.cloud`.
- README plus the operator-facing console and API guides now align on the same loopback-only app binding and Caddy plus Basic Auth remote-access baseline.
- The deployment guide now includes a checked-in one-server smoke-check helper plus a first-pass SQLite backup and rollback runbook for the same `/opt/sns-content-engine` layout.

### Current limitations relevant to the new goal

- The browser console and JSON operator routes still do not add in-app authentication, so remote deployment remains dependent on the chosen edge protection layer.
- Backup and rollback remain operator-invoked runbook steps rather than automated platform features.

## Milestones

### M1: Deployment Baseline Assets

Goal:
- Add the smallest repository-backed baseline for one-server runtime layout and operator conventions.

Tasks:
- `01` Deployment guide and production conventions
- `02` Runtime packaging and service units

### M2: Edge Hardening And Domain Routing

Goal:
- Make `sns.gilgop.cloud` deployable behind explicit HTTPS and access protection.

Tasks:
- `03` Reverse proxy and domain assets for `sns.gilgop.cloud`
- `04` Remote console safety alignment

### M3: Operational Rollout And Recovery

Goal:
- Make the first production rollout and later recovery steps repeatable for one operator.

Tasks:
- `05` Smoke checks, backup, and rollback runbook

## Phase 1: Deployment Baseline Assets

### Task 01: Deployment guide and production conventions

Goal:
- Add a dedicated deployment guide that standardizes single-server layout, env handling, database decisions, and service split expectations for `sns.gilgop.cloud`.

Actions:
- create a deployment guide that covers recommended server directory layout, config path conventions, `.env` handling, and SQLite versus Postgres guidance
- document the split between the FastAPI web service and the background scheduler service
- align deployment guidance with existing healthcheck, review-first, and dry-run publish semantics

Verification:
- `PYTHONPATH=$PWD pytest tests/test_cli.py -k "healthcheck" -q`
- `PYTHONPATH=$PWD pytest tests/test_env.py -q`

Done when:
- the repository has one dedicated deployment guide for the personal-server target
- deployers can infer a stable server layout without guessing from scattered docs
- the guide preserves the current review and publish safety model

### Task 02: Runtime packaging and service units

Goal:
- Make the repository carry the minimum runtime and service assets needed to run the web console and scheduler on a real server.

Actions:
- add `uvicorn` runtime support in the smallest clean shape that fits the current packaging policy
- add dedicated `systemd` unit files for `sns-web` and `sns-scheduler`
- add a checked-in production env template such as `.env.production.example`

Verification:
- `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py -q`
- `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q`

## Phase 2: Edge Hardening And Domain Routing

### Task 03: Reverse proxy and domain assets for `sns.gilgop.cloud`

Goal:
- Add one preferred Caddy reverse-proxy configuration path that safely exposes the operator surface over HTTPS at `sns.gilgop.cloud`.

Actions:
- add repository-backed Caddy configuration assets for `sns.gilgop.cloud`
- keep the application port private and proxied from the edge layer only
- protect all non-health routes with edge Basic Auth and document TLS, certificate renewal, and DNS expectations for the chosen proxy

Verification:
- `PYTHONPATH=$PWD pytest tests/test_api.py -k health -q`
- `PYTHONPATH=$PWD pytest tests/test_console.py -q`

### Task 04: Remote console safety alignment

Goal:
- Align README and operator-facing docs so remote console deployment and JSON operator routes are always described as edge-protected and never as directly public.

Actions:
- update README, console docs, and API-facing operator docs with explicit access-protection requirements for remote operation
- explain acceptable edge protections such as basic auth, IP allowlists, VPN, or a zero-trust gateway
- keep non-goals explicit by clarifying that this initiative does not add in-app auth

Verification:
- `PYTHONPATH=$PWD pytest tests/test_deploy_assets.py -q`
- `PYTHONPATH=$PWD pytest tests/test_console.py -q`
- `PYTHONPATH=$PWD pytest tests/test_api.py -k health -q`

## Phase 3: Operational Rollout And Recovery

### Task 05: Smoke checks, backup, and rollback runbook

Goal:
- Add the smallest repeatable rollout and recovery workflow for first deployment and later maintenance.

Actions:
- add a smoke-check script or operator checklist for service status, `/health`, protected console access, and `publish-due` dry-run validation
- document backup and rollback steps for the selected database path and service restart sequence
- align README and deployment docs so rollout order is explicit and non-destructive

Verification:
- `PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q`
- `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py -q`
