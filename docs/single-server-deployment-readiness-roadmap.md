# Single-Server Deployment Readiness Roadmap

## Goal
Extend the current local-and-operator-first implementation into a single-server deployment-ready baseline that:
- can run the web console and scheduler safely on one personal server under `sns.gilgop.cloud`
- codifies repeatable runtime, environment, and service layout decisions inside the repository
- keeps the current manual-review gate, dry-run-first publish defaults, and env-only credential model intact
- documents edge protection, HTTPS, smoke checks, backup, and rollback expectations before the first live rollout

## Generated document naming
When instantiating this template, use a filename that clearly shows the document identity.

- Roadmap file: `docs/single-server-deployment-readiness-roadmap.md`
- Execution guide file: `docs/single-server-deployment-readiness-execution-guide.md`
- Progress tracker file: `docs/single-server-deployment-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/single-server-deployment-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `plan.md`, or `notes.md` when multiple initiatives may exist.

## Roadmap construction rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- Define only as many milestones and tasks as are needed to reach the goal while keeping each unit safely implementable.
- Choose task and milestone boundaries so the work can be completed without breaking the existing architecture, workflow semantics, safety gates, or operator experience.
- Prefer the smallest additive deployment slices that reuse the current FastAPI app, CLI scheduler, and env-driven configuration model instead of forcing a broad infrastructure redesign.
- Split a task when it would otherwise mix unrelated concerns such as runtime packaging, reverse proxy setup, edge security, and recovery procedures.
- Merge adjacent tiny tasks when they share the same files, verification surface, and commit scope.
- If the roadmap shape changes during implementation, update this file and `docs/single-server-deployment-readiness-progress-tracker.md` before continuing.

## Current implementation snapshot

### Already implemented
- The repository already exposes a FastAPI application with `/health` plus server-rendered `/console/...` operator pages.
- The CLI already supports `scheduler run`, `publish-due`, `healthcheck`, review actions, and database bootstrap or upgrade flows.
- The project already uses environment-driven secrets, includes `.env.example`, and ships a tiny project-local `.env` loader.
- README already includes a long-running scheduler `systemd` example, and the operator console guide already documents local `uvicorn` startup.

### Current limitations relevant to the new goal
- There is no dedicated deployment guide that covers one-server runtime layout, domain routing, HTTPS, access protection, and first-rollout checks together.
- The repository does not yet ship a dedicated web-service `systemd` unit, reverse-proxy config assets, or a production env template for remote operation.
- `uvicorn` is documented for local console use but is not currently part of the packaged runtime dependency set.
- The browser console does not add authentication, so exposing it remotely without an edge protection layer would be unsafe.
- README and current operator docs mention local and single-server pieces, but they do not yet provide one cohesive `sns.gilgop.cloud` deployment path or rollback checklist.
- The default SQLite path works for local operation, but the repository does not yet document a clear deployment decision boundary for staying on SQLite versus switching to Postgres on a personal server.

## Environment and execution assumptions
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands already available:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q`
- Broader regression commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py tests/test_cli.py tests/test_scheduler.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q`
- Required local services:
  - `none for docs and static deployment assets`
  - `local SQLite or operator-provided Postgres only when doing non-fixture smoke checks`
- Required env files, secrets, or fixtures:
  - `.env.example` as the checked-in reference template
  - `a real .env or EnvironmentFile on the target server`
  - `config/ or a future operator-approved prod config directory`
- Package install policy: `ask_first`

## Target architecture

### Edge layer
- `reverse_proxy`
  - Terminates HTTPS for `sns.gilgop.cloud`.
  - Enforces access protection before the request reaches the FastAPI console.
  - Proxies only web traffic to a local-only application port such as `127.0.0.1:8000`.
- `dns_and_tls`
  - Points `sns.gilgop.cloud` at the personal server IP.
  - Uses automated certificate issuance and renewal through the chosen reverse proxy.

### Runtime layer
1. `sns-web` runs `uvicorn` against `app.api.app:app` on a loopback-only port.
2. `sns-scheduler` runs `sns-engine scheduler run` as a separate long-running `systemd` service.
3. Both services load the same environment file and explicit config or database settings.
4. The database remains local SQLite by default unless the deployment guide calls for a Postgres upgrade path.

### Operations layer
1. Prepare config, `.env`, and database paths under a stable server directory such as `/opt/sns-content-engine`.
2. Initialize or upgrade the database before starting services.
3. Run `healthcheck` and dry-run publish verification before any live publish attempt.
4. Keep backup, restart, and rollback procedures documented and runnable by a single operator.

## Milestones
Use as many milestone blocks as needed. Keep each milestone small enough to be completed without breaking the current structure or requiring a broad redesign.

### Milestone M1: Deployment Baseline Assets
- Goal: Add the smallest repository-backed deployment baseline for one-server operation.
- Includes:
  - a dedicated deployment guide with server layout, env, DB, and startup decisions
  - packaged runtime support for the web console plus `systemd` assets for web and scheduler services
- Excludes:
  - reverse-proxy domain routing and TLS automation
  - backup, rollback, and rollout smoke-check automation
- Verification target:
  - focused API, console, CLI, scheduler, and env regression coverage
  - docs alignment review against README and operator-console guidance
- Ship when:
  - the repository contains enough assets to run the web console and scheduler like a production-shaped single-server deployment
  - operators know where service files, config, database, and env state belong on the server

### Milestone M2: Edge Hardening And Domain Routing
- Goal: Make `sns.gilgop.cloud` deployable behind an explicit HTTPS and access-protected edge layer.
- Includes:
  - one preferred reverse-proxy configuration for `sns.gilgop.cloud`
  - TLS and access-protection guidance that keeps the unauthenticated browser console off the open internet
- Excludes:
  - in-app auth, multi-user permissions, or a frontend redesign
  - CDN, WAF, or broad network-topology redesign
- Verification target:
  - docs and config review for domain, loopback, and access-protection correctness
  - focused console and API regression checks if shared URLs or guidance require code-adjacent changes
- Ship when:
  - the repository provides a concrete `sns.gilgop.cloud` edge configuration path
  - deployment docs explicitly forbid exposing `/console` without edge protection

### Milestone M3: Operational Rollout And Recovery
- Goal: Make the first production rollout and later recovery steps repeatable for one operator.
- Includes:
  - a smoke-check script or checklist for health, console access, scheduler status, and dry-run publish validation
  - backup and rollback instructions for the selected database path
  - final README and operator-guide alignment for remote operation
- Excludes:
  - distributed deployment, autoscaling, or observability-platform expansion
  - long-term secret-rotation automation or OAuth refresh redesign
- Verification target:
  - focused script, CLI, and operations coverage when scripts or commands are added
  - one broader API, console, and scheduler regression slice if shared surfaces change
- Ship when:
  - an operator can complete initial rollout, dry-run validation, and rollback using only repository-backed docs and assets
  - the repo no longer relies on scattered local-only notes for remote deployment

## Implementation roadmap

## Phase 1: Deployment Baseline Assets

### Task 01: Deployment guide and production conventions
- Goal: Add a dedicated single-server deployment guide that standardizes runtime paths, config layout, env handling, database choices, and operator decisions for `sns.gilgop.cloud`.
- Actions:
  - create a deployment guide that covers recommended server directory layout, config path conventions, `.env` handling, and SQLite versus Postgres guidance
  - document the split between the FastAPI web service and the background scheduler service
  - align deployment guidance with existing healthcheck, review-first, and dry-run publish semantics
- Dependencies:
  - `README.md`
  - `docs/operator-console-guide.md`
  - `app/api/app.py`, `app/cli.py`, and `app/storage/database.py`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_cli.py -k "healthcheck" -q`
  - `PYTHONPATH=$PWD pytest tests/test_env.py -q`
- Risk or rollback note:
  - keep the guide additive and specific to the current architecture instead of turning it into a broad platform redesign document
- Done when:
  - the repository has one dedicated deployment guide for the personal-server target
  - deployers can infer a stable server layout without guessing from scattered docs
  - the guide preserves the current review and publish safety model
  - `docs/single-server-deployment-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 02: Runtime packaging and service units
- Goal: Make the repository carry the minimum runtime and service assets needed to run the web console and scheduler on a real server.
- Actions:
  - add `uvicorn` runtime support in the smallest clean shape that fits the current packaging policy
  - add dedicated `systemd` unit files for `sns-web` and `sns-scheduler`
  - add a checked-in production env template such as `.env.production.example` that matches current secret and database expectations
- Dependencies:
  - Task 01
  - `pyproject.toml`
  - existing scheduler `systemd` example in `README.md`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q`
- Risk or rollback note:
  - keep the web service bound to loopback and preserve current scheduler semantics rather than coupling both processes into one service
- Done when:
  - the repository contains dedicated service units for web and scheduler roles
  - runtime packaging no longer relies on undocumented manual `uvicorn` installation for remote deployment
  - env examples reflect current credential and database conventions
  - `docs/single-server-deployment-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 2: Edge Hardening And Domain Routing

### Task 03: Reverse proxy and domain assets for `sns.gilgop.cloud`
- Goal: Add one preferred reverse-proxy configuration path that safely exposes the web console over HTTPS at `sns.gilgop.cloud`.
- Actions:
  - add repository-backed reverse-proxy configuration assets for `sns.gilgop.cloud`
  - keep the application port private and proxied from the edge layer only
  - document TLS, certificate renewal, and DNS expectations for the chosen proxy
- Dependencies:
  - Task 02
  - `app/api/app.py` health and console routes
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py -k health -q`
  - `PYTHONPATH=$PWD pytest tests/test_console.py -q`
- Risk or rollback note:
  - prefer one concrete proxy path instead of maintaining parallel Caddy and Nginx implementations unless a later task intentionally expands that scope
- Done when:
  - the repository contains a concrete proxy configuration for `sns.gilgop.cloud`
  - the guide keeps the app on loopback and terminates HTTPS at the edge layer
  - DNS and TLS responsibilities are explicit enough for one operator to follow without improvisation
  - `docs/single-server-deployment-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 04: Remote console safety alignment
- Goal: Align README and operator-facing docs so remote console deployment is always described as edge-protected and never as directly public.
- Actions:
  - update README and console docs with explicit access-protection requirements for remote operation
  - explain which protections are acceptable at the edge layer, such as basic auth, IP allowlists, VPN, or a zero-trust gateway
  - keep non-goals explicit by clarifying that this initiative does not add in-app auth
- Dependencies:
  - Task 03
  - existing operator console docs and browser safety notes
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_api.py -k health -q`
- Risk or rollback note:
  - avoid implying that the current FastAPI app is safe for public unauthenticated exposure without a protecting proxy layer
- Done when:
  - remote-access docs consistently require edge protection
  - the initiative still avoids in-app auth and multi-user expansion
  - operator-facing guidance stays aligned with the shipped console behavior
  - `docs/single-server-deployment-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 3: Operational Rollout And Recovery

### Task 05: Smoke checks, backup, and rollback runbook
- Goal: Add the smallest repeatable rollout and recovery workflow for first deployment and later maintenance.
- Actions:
  - add a smoke-check script or operator checklist for service status, `/health`, protected console access, and `publish-due` dry-run validation
  - document backup and rollback steps for the selected database path and service restart sequence
  - align README and deployment docs so rollout order is explicit and non-destructive
- Dependencies:
  - Task 04
  - existing `healthcheck`, `scheduler publish-due`, and `db upgrade` flows
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_scripts.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_operations.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py tests/test_scheduler.py -q`
- Risk or rollback note:
  - keep rollout checks focused on current shipped flows instead of inventing a new deployment orchestration layer
- Done when:
  - the repo contains one repeatable rollout and rollback path for a single operator
  - smoke checks verify safe defaults before live publish is attempted
  - docs clearly separate dry-run validation from the first deliberate live publish
  - `docs/single-server-deployment-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Suggested execution order
List only the tasks that actually exist in dependency order. Add or remove lines as needed.

1. Task 01
2. Task 02
3. Task 03
4. Task 04
5. Task 05

## Initial milestone recommendation
Start with the smallest milestone that:
- creates a dedicated deployment guide instead of relying on scattered local notes
- formalizes the web and scheduler service split already implied by the codebase
- adds packaged runtime and service assets without changing review or publish semantics
- can be implemented and verified without breaking the current structure

This keeps the next stage focused on making the current backend deployable on one protected server before expanding into domain edge hardening, smoke-check automation, or broader operations maturity.
