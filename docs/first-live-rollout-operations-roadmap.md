# First Live Rollout Operations Roadmap

## Goal
Extend the current completed first-live-rollout readiness baseline into a first protected production rollout that:
- proves the local repository and production server are still in a green, operator-ready state
- confirms provider, publisher, credential, and deployment configuration without exposing secrets
- executes at most one explicit live `X` publish after dry-run and smoke-check gates pass
- records post-publish observations, rollback or hold decisions, and follow-up hardening items

## Generated document naming
When instantiating this template, use a filename that clearly shows the document identity.

- Roadmap file: `docs/first-live-rollout-operations-roadmap.md`
- Execution guide file: `docs/first-live-rollout-operations-execution-guide.md`
- Progress tracker file: `docs/first-live-rollout-operations-progress-tracker.md`
- Vibe coding prompt file: `docs/first-live-rollout-operations-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `plan.md`, or `notes.md` when multiple initiatives may exist.

## Roadmap construction rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- Define only as many milestones and tasks as are needed to reach the rollout goal while keeping each unit safely executable.
- Choose task and milestone boundaries so the work can be completed without breaking the existing architecture, workflow semantics, safety gates, or operator experience.
- Prefer the smallest additive slices that reuse the current structure instead of forcing a broad redesign.
- Split a task when it would otherwise span unrelated local, server, credential, or live-publish surfaces.
- Merge adjacent tiny tasks when they share the same command surface, verification evidence, and rollback path.
- If the roadmap shape changes during execution, update this file and `docs/first-live-rollout-operations-progress-tracker.md` before continuing.

## Current implementation snapshot

### Already implemented
- The `First Live Rollout Readiness` roadmap is complete and recorded in `docs/first-live-rollout-readiness-progress-tracker.md`.
- The repository has a FastAPI app, scheduler runtime, CLI workflows, X publisher adapter, provider routing, env-only secret handling, and one-server deployment assets.
- `docs/single-server-deployment-guide.md` includes a first-rollout preflight sequence covering pytest, healthcheck, dry-run publish, secret scan, and smoke check.
- The scheduler `publish-due` path stays dry-run by default, while live publish requires an explicit `--live` flag.

### Current limitations relevant to the new goal
- The next step depends on real server state, real production env values, and edge smoke credentials that should not be committed or echoed into docs.
- The first live publish must not be attempted until dry-run queue output and smoke checks prove the production path is ready.
- Any live `X` publish is an irreversible external side effect, so it requires explicit operator confirmation in the active thread.
- Threads live rollout, LinkedIn direct publish, and richer publisher observability are intentionally outside this operational launch slice.

## Environment and execution assumptions
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands already available:
  - `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q`
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest -q`
  - `scripts/scan_secrets.sh check`
- Required local services:
  - `none for local repository verification`
  - `sns-web.service`, `sns-scheduler.service`, and `caddy.service` when running server-side smoke checks
- Required env files, secrets, or fixtures:
  - production `/opt/sns-content-engine/.env` on the server
  - production `/opt/sns-content-engine/config`
  - `SNS_SMOKE_EDGE_USER` and `SNS_SMOKE_EDGE_PASSWORD` for `scripts/single_server_smoke_check.sh`
  - real X publisher credential bundle only for explicitly approved live publish
- Package install policy: `ask_first`

## Target architecture

### Operational Gates
- `local repository gate`
  - run targeted and full tests before treating the checkout as launch-ready
  - run secret scan before any server or live operation
- `server readiness gate`
  - verify production config, healthcheck, systemd units, loopback health, edge console protection, and dry-run publish behavior

### Controlled Live Event
1. confirm dry-run output and due-job scope
2. request explicit operator approval for the live command
3. run at most one `X` live publish command
4. record command result, external observation, logs, and hold or continue decision

## Milestones

### Milestone M1: Local Launch Gate
- Goal: confirm the repository and launch plan are safe before touching production state.
- Includes:
  - current branch and worktree check
  - local regression and secret-scan checks
  - rollout input checklist and explicit live-approval boundary
- Excludes:
  - running production server commands
  - running any live publish command
- Verification target:
  - `./.venv/bin/pytest -q`
  - `scripts/scan_secrets.sh check`
- Ship when:
  - local checks pass or blockers are recorded
  - the operator knows exactly what credentials and server access are still needed

### Milestone M2: Server Dry-Run Gate
- Goal: prove the production server can run the rollout path safely while still in dry-run mode.
- Includes:
  - production config and env presence checks without exposing secret values
  - server-side `healthcheck`
  - server-side dry-run `scheduler publish-due`
  - checked-in single-server smoke helper
- Excludes:
  - any `--live` publish command
  - server infrastructure redesign
- Verification target:
  - `./.venv/bin/sns-engine rollout-summary --config-dir /opt/sns-content-engine/config`
  - `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config`
  - `./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config`
  - `scripts/single_server_smoke_check.sh`
- Ship when:
  - dry-run and smoke results are captured
  - live publish is either approved for the next milestone or blocked with a clear reason

### Milestone M3: First X Live Publish And Observation
- Goal: execute one protected live `X` publish and record the operational result.
- Includes:
  - final operator approval prompt
  - one explicit `scheduler publish-due --live` command scoped to the production config
  - post-publish log and external-result observation
- Excludes:
  - repeated live runs without a new approval
  - Threads or LinkedIn live expansion
- Verification target:
  - production command exit status
  - publish job state or publish log evidence
  - external X post visibility check performed by the operator or documented as unavailable
- Ship when:
  - the live attempt result is recorded as succeeded, failed, or intentionally held
  - any rollback, retry, or follow-up work is documented

## Implementation roadmap

## Phase 1: Local Launch Gate

### Task 01: Confirm Rollout Inputs And Approval Boundary
- Goal: establish the exact launch context before running preflight commands.
- Actions:
  - inspect current branch, worktree status, and completed readiness tracker
  - confirm first rollout scope remains `X` only and Threads stays deferred or manual fallback
  - list required server access, smoke credentials, production env presence, and explicit approval requirements
- Dependencies:
  - completed `First Live Rollout Readiness` docs
  - current local checkout
- Verification commands:
  - `git status --short --branch`
  - `rg -n "First-rollout preflight|X-only|publish-due|--live" README.md docs/single-server-deployment-guide.md docs/operator-console-guide.md`
- Risk or rollback note:
  - avoid treating an operator-intent check as approval to run a live command; live publish still requires a separate explicit confirmation
- Done when:
  - launch scope and blockers are recorded in `docs/first-live-rollout-operations-progress-tracker.md`
  - no live commands have been run
  - a focused commit is created only if docs changed, or the reason no commit was created is recorded explicitly

### Task 02: Run Local Regression And Secret Gates
- Goal: prove the local checkout is still safe to use as the rollout baseline.
- Actions:
  - run targeted config, deployment, CLI, scheduler, and X publisher tests
  - run the full pytest suite
  - run the checked-in secret scan
- Dependencies:
  - Task `01`
  - local development dependencies installed
- Verification commands:
  - `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q`
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q`
  - `./.venv/bin/pytest -q`
  - `scripts/scan_secrets.sh check`
- Risk or rollback note:
  - do not proceed to server checks if local tests or secret scan fail unless the failure is clearly unrelated and explicitly accepted by the operator
- Done when:
  - all local gate results are recorded
  - any failure has a clear stop reason and next step

## Phase 2: Server Dry-Run Gate

### Task 03: Verify Production Config And Healthcheck
- Goal: confirm the production server is using the intended config and env shape without exposing secrets.
- Actions:
  - verify production `.env` and config paths exist on the server
  - confirm provider setup remains OpenAI-first and first rollout remains `X` live only
  - run server-side `healthcheck`
- Dependencies:
  - Task `02`
  - server shell access
  - production env file present
- Verification commands:
  - `./.venv/bin/sns-engine rollout-summary --config-dir /opt/sns-content-engine/config`
  - `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config`
- Risk or rollback note:
  - never print secret values; only record presence, absence, or command status
- Done when:
  - healthcheck result is captured
  - missing env, config, or credential blockers are recorded before any live operation

### Task 04: Run Server Dry-Run Publish And Smoke Helper
- Goal: prove the production publish path is safe in dry-run mode and the edge deployment is reachable.
- Actions:
  - run server-side dry-run `scheduler publish-due`
  - run `scripts/single_server_smoke_check.sh` with edge credentials supplied from the environment
  - capture dry-run queue shape, service status, and smoke helper result
- Dependencies:
  - Task `03`
  - production services running
  - `SNS_SMOKE_EDGE_USER` and `SNS_SMOKE_EDGE_PASSWORD` available in the shell environment
- Verification commands:
  - `./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config`
  - `scripts/single_server_smoke_check.sh`
- Risk or rollback note:
  - if dry-run shows an unexpected queue, channel, account, or payload, stop before live publish and record the mismatch
- Done when:
  - dry-run and smoke-check results are captured
  - the tracker explicitly says whether live approval can be requested

## Phase 3: First X Live Publish And Observation

### Task 05: Execute One Approved X Live Publish
- Goal: run exactly one live `X` publish after all gates pass and the operator explicitly approves the command.
- Actions:
  - summarize dry-run evidence and ask for explicit approval before running `--live`
  - run one live publish command only if approval is granted
  - capture exit status and publish-job or publish-log evidence
- Dependencies:
  - Task `04`
  - explicit operator approval in the active thread
  - real X publisher credentials configured on the server
- Verification commands:
  - `./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config --live`
- Risk or rollback note:
  - live publish is externally visible and cannot be undone by git rollback; if approval is absent or ambiguous, do not run it
- Done when:
  - live attempt result is recorded as `succeeded`, `failed`, or `not_run`
  - no second live command is run without a new approval

### Task 06: Capture Post-Publish Observation And Next Decision
- Goal: turn the live attempt into an auditable operating record.
- Actions:
  - record publish logs, job state, and operator-visible X result when available
  - document whether to continue, pause, retry, or roll back server state
  - capture follow-up hardening ideas as separate future initiatives
- Dependencies:
  - Task `05`
  - production logs or operator observation
- Verification commands:
  - `./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config`
  - production log inspection command chosen by the operator, if available
- Risk or rollback note:
  - do not convert a successful first publish into ongoing automation without a separate operating decision
- Done when:
  - post-publish evidence and next decision are recorded
  - follow-up work is separated from the completed rollout event

## Suggested execution order
List only the tasks that actually exist in dependency order. Add or remove lines as needed.

1. Task `01`: Confirm Rollout Inputs And Approval Boundary
2. Task `02`: Run Local Regression And Secret Gates
3. Task `03`: Verify Production Config And Healthcheck
4. Task `04`: Run Server Dry-Run Publish And Smoke Helper
5. Task `05`: Execute One Approved X Live Publish
6. Task `06`: Capture Post-Publish Observation And Next Decision

## Initial milestone recommendation
Start with Milestone `M1: Local Launch Gate`.

This keeps the next stage focused on local safety and launch-context clarity before expanding into server-side checks or any live external side effect.
