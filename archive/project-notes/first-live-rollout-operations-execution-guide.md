# First Live Rollout Operations Autonomous Execution Guide

## Purpose
This document is written for an autonomous coding agent assisting with an operational production rollout, not just for a code implementation task.

Use it when you want the agent to read the roadmap in `docs/first-live-rollout-operations-roadmap.md`, inspect the repository, choose the smallest safe execution slice, run or document relevant checks, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the completed readiness baseline instead of inventing a new deployment plan
- they constrain work so the existing safety model stays intact
- they require reusing current CLI, scheduler, smoke-check, and docs before adding new scripts
- they preserve manual review, dry-run-first publishing, env-only secrets, and explicit live approval unless a task states otherwise

Progress for live execution should be tracked in:
- `docs/first-live-rollout-operations-progress-tracker.md`

## Generated document naming
When instantiating this template, use filenames that make each document's identity obvious at a glance.

- Roadmap file: `docs/first-live-rollout-operations-roadmap.md`
- Execution guide file: `docs/first-live-rollout-operations-execution-guide.md`
- Progress tracker file: `docs/first-live-rollout-operations-progress-tracker.md`
- Vibe coding prompt file: `docs/first-live-rollout-operations-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `prompt.md`, `guide.md`, or `progress.md` when multiple initiatives may coexist.

## Repository Context
The repository already has:
- a working FastAPI app, scheduler runtime, CLI workflows, and operator console
- X publisher support plus dry-run-first scheduler publish behavior
- checked-in single-server deployment assets and a first-rollout preflight checklist
- completed readiness docs for local tests, provider setup, blank env handling, and X-only first rollout guardrails

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/api/app.py`
- Core workflows/services: `app/scheduler/jobs.py`, `app/scheduler/runtime.py`
- Publisher and routing surfaces: `app/connectors/publishers/x.py`, `app/connectors/publishers/resolver.py`, `app/connectors/routing/registry.py`
- Storage and schema logic: `app/storage/database.py`, `app/storage/bootstrap.py`
- Current operational gap: production server access, production env presence, smoke credentials, and explicit live-publish approval are external to the repository
- Existing operator or deployment docs: `README.md`, `docs/single-server-deployment-guide.md`, `docs/operator-console-guide.md`
- Existing roadmap: `docs/first-live-rollout-operations-roadmap.md`

High-signal tests already exist and should be reused instead of inventing a new test structure:
- `tests/test_config.py`
- `tests/test_deploy_assets.py`
- `tests/test_cli.py`
- `tests/test_scheduler.py`
- `tests/test_x_publisher.py`

## Execution Environment
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands by area:
  - `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q`
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest -q`
  - `scripts/scan_secrets.sh check`
- Required services:
  - `none for local repository verification`
  - `sns-web.service`, `sns-scheduler.service`, and `caddy.service` for server-side smoke checks
- Required env files, secrets, or fixtures:
  - production `/opt/sns-content-engine/.env` on the server
  - production `/opt/sns-content-engine/config`
  - `SNS_SMOKE_EDGE_USER` and `SNS_SMOKE_EDGE_PASSWORD` for smoke checks
  - real X publisher credentials only after explicit live-publish approval
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path and rollout docs before editing or running commands.
- Read `docs/first-live-rollout-operations-progress-tracker.md` before choosing the next task.
- Prefer reusing CLI, scheduler, smoke-check, provider, publisher, and deployment logic over duplicating it in new helpers.
- Keep each task self-contained and merge-friendly.
- Choose additive docs or tiny safety fixes over broad redesigns.
- Preserve current behavior unless a task explicitly updates a shared abstraction.

### Resume rules
- If `docs/first-live-rollout-operations-progress-tracker.md` shows a current task with status `in_progress` or `blocked`, resume or resolve that task before selecting a new one unless the roadmap was intentionally reprioritized.
- Only choose the next unfinished task when there is no active task that still owns the current branch or execution state.
- If the active task was blocked by a fixable local issue and the scope is still the same, keep the same task ID and continue instead of creating a new task.

### Roadmap shaping rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- When creating or refining the roadmap, choose only as many milestones and tasks as are needed to make forward progress safely.
- Split work so it can be completed without breaking the current structure, safety model, workflow semantics, or operator experience.
- Prefer the smallest additive slices that fit the existing architecture and rollout sequence.
- Split a task or milestone when it would otherwise mix local verification, server verification, credentials, and live external side effects.
- Merge adjacent tiny items when they share the same command surface, evidence, and rollback path.
- If the roadmap shape changes during execution, update `docs/first-live-rollout-operations-roadmap.md` and `docs/first-live-rollout-operations-progress-tracker.md` before continuing.

### Scope control
- Do not expand work into authentication, multi-user permissions, Docker, Kubernetes, or a full frontend.
- Do not redesign the publish workflow, scheduler runtime, provider routing, or database model unless a task explicitly requires a safety fix.
- Keep the first live rollout centered on `X` only.
- Treat Threads live publish, LinkedIn direct publish, media upload, and richer publisher observability as separate follow-up initiatives.

### Dirty worktree rules
- Inspect the current branch and working tree before making substantive edits.
- Never overwrite, revert, or stage unrelated changes.
- If user or pre-existing changes conflict directly with the active task in the same files, stop, record the conflict in `docs/first-live-rollout-operations-progress-tracker.md`, and treat the task as blocked until the conflict is resolved.
- Keep branch, staging, and commit scope limited to the active task.

### Safety constraints
- Preserve the current manual-review gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Keep validation and policy blockers intact.
- Keep credentials in env only.
- Keep `publish-due` dry-run as the default path.
- Never run `scheduler publish-due --live` unless the operator explicitly approves that exact live step in the active thread.
- Do not print, commit, summarize, or transform secret values. Record only presence, absence, command status, or redacted identifiers.

### Blocked-task rules
- Try the smallest reasonable local investigation first when a blocker appears.
- If progress is blocked by missing configuration, unavailable services, missing credentials, conflicting local edits, unexpected dry-run output, failed smoke checks, or unrelated failing tests, record the exact blocker and stop reason in `docs/first-live-rollout-operations-progress-tracker.md`.
- Mark the task `blocked` when work cannot continue safely inside the intended scope.
- Do not mark blocked work as `done`.
- Do not create a normal task-completion commit for blocked work; only create a checkpoint commit if the partial state is independently safe, intentionally scoped, and clearly documented.

### Testing and command rules
- Use task-specific verification commands from `docs/first-live-rollout-operations-roadmap.md` when they are provided.
- Run the narrowest relevant local test set first.
- Run the full suite and secret scan before server-side or live publish work.
- Treat server-side checks as operational evidence and record exact command status without leaking secrets.
- If no explicit test command exists, infer the narrowest relevant command from the repository and record that reasoning in `docs/first-live-rollout-operations-progress-tracker.md`.
- Distinguish newly introduced failures from pre-existing failures or environment failures.
- If testing cannot run, record the exact command and reason as `not_run` or `pre_existing_failure`.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.

### Git workflow rules
- Create a dedicated branch before making substantive file changes.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-rollout-inputs`
  - `codex/task-02-local-launch-gate`
  - `codex/task-04-server-smoke-gate`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after relevant tests or docs checks pass, or explicitly record why a commit was not created.
- Do not push branches or open pull requests unless explicitly requested.
- Use a clear commit message tied to the task outcome, for example:
  - `Document first rollout launch context`
  - `Record local rollout gate results`
  - `Capture first live publish observation`

### Live command approval rules
- Before requesting live approval, summarize the dry-run result, due-job scope, channel, account, and any known risk.
- Approval must be specific to the live command, not inferred from general rollout intent.
- If the operator asks to proceed, run at most one live command and then stop for observation.
- If approval is ambiguous, absent, or stale after a material change, ask again and do not run `--live`.
- Never repeat a live command after failure or timeout without a new explicit approval and updated tracker entry.

### Completion rules
- Only finish after command execution, verification, and progress updates are done.
- Do not mark a task complete until `docs/first-live-rollout-operations-progress-tracker.md` includes the final status, changed files or command evidence, test log, and commit details or the reason a commit was not created.
- If the work cannot be finished safely, leave the task as `blocked` with a clear next step instead of forcing completion.
- Report:
  - what changed or what was verified
  - why that execution shape was chosen
  - commands run
  - branch and commit details
  - any remaining follow-up intentionally deferred

## Progress Tracking Rules
The agent must keep `docs/first-live-rollout-operations-progress-tracker.md` updated while implementing or executing this roadmap.

### When to update
- At the start of a task:
  - set the current task
  - mark status as `in_progress`
  - record the intended scope
  - record the active branch or server context
- During execution:
  - append meaningful progress notes when command results change, files are edited, or a blocker is discovered
  - update the changed-files or evidence list as files are touched or commands are run
- After tests or operational checks:
  - record commands and pass, fail, not-run, or blocked status
- At task completion:
  - mark the task `done`
  - summarize final changed files or operational evidence
  - record the commit SHA and commit message if a commit was created
  - record follow-up items if any remain

### What to track
- current active task
- current active milestone
- base branch
- active branch
- latest commit for the task when available
- resume decision
- overall task status table
- files changed or command evidence for the active task
- implementation or execution notes
- test and command execution log
- stop reason or blockers
- open questions
- pre-existing failures or environment constraints
- blockers or follow-up items

### Tracking constraints
- Keep entries short and factual.
- Update the existing progress file instead of creating a new ad hoc log.
- Avoid duplicate log entries when rerunning the same step; update the existing note if it still describes the current state.
- Do not mark a task done before relevant checks have run, unless testing is impossible and the reason is recorded explicitly.
- Do not record secret values.

## Output Contract For The Agent
Unless the caller requests a different format, end each task with:

```text
Summary
- ...

Changed files or evidence
- ...

Commands run
- ...

Branch and commit
- ...

Follow-up
- ...
```

## Recommended Task Order
List the actual tasks defined in `docs/first-live-rollout-operations-roadmap.md` in dependency order.

1. Task `01`: Confirm Rollout Inputs And Approval Boundary
2. Task `02`: Run Local Regression And Secret Gates
3. Task `03`: Verify Production Config And Healthcheck
4. Task `04`: Run Server Dry-Run Publish And Smoke Helper
5. Task `05`: Execute One Approved X Live Publish
6. Task `06`: Capture Post-Publish Observation And Next Decision

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and execute it.

```text
You are implementing the First Live Rollout Operations roadmap in this repository.

Start by reading:
- docs/first-live-rollout-operations-roadmap.md
- docs/first-live-rollout-operations-execution-guide.md
- docs/first-live-rollout-operations-progress-tracker.md

Then inspect the current code and rollout docs before editing or running commands. Use the task boundaries and rules in docs/first-live-rollout-operations-execution-guide.md.

Your job:
1. Determine whether docs/first-live-rollout-operations-progress-tracker.md already shows an active task. If it is `in_progress` or `blocked`, resume or resolve that task unless the roadmap was intentionally reprioritized.
2. If there is no active task, determine the next unfinished task in the recommended order.
3. If the roadmap shape is incomplete, too large, or unsafe to execute cleanly, refine the task or milestone boundaries using the smallest additive slices that preserve the current structure, then update docs/first-live-rollout-operations-roadmap.md and docs/first-live-rollout-operations-progress-tracker.md before continuing.
4. Create or switch to a dedicated task branch if file edits are needed.
5. Update docs/first-live-rollout-operations-progress-tracker.md to mark that task in progress and note the intended scope, branch or server context, and verification plan.
6. Execute only that task cleanly and completely.
7. Keep docs/first-live-rollout-operations-progress-tracker.md updated during the work with changed files, command evidence, progress notes, blockers, or stop reasons.
8. Run task verification commands from docs/first-live-rollout-operations-roadmap.md and record the results.
9. Stage only task-relevant files and create a focused commit after checks pass if files changed, or explicitly record why a commit was not created.
10. Mark the task complete in docs/first-live-rollout-operations-progress-tracker.md when verified, including branch and commit details, or leave it `blocked` with a clear next step if it cannot be finished safely.
11. Summarize changes, commands, branch, commit, and follow-up.

Critical constraints:
- preserve manual review
- keep dry-run publish as the default gate
- keep secrets env-only and never print or commit them
- avoid broad architecture rewrites
- do not expand into Threads live publish, LinkedIn direct publish, auth, frontend implementation, or speculative platform work
- never run `scheduler publish-due --live` without explicit operator approval for that exact live step
- do not push or open a PR unless explicitly requested

If the next task is ambiguous, choose the smallest sensible interpretation that improves operator safety or advances the rollout without changing workflow semantics.
```

## Milestone Prompt
Use this when you want the agent to complete the current incomplete milestone instead of one isolated unit.

```text
Implement the current incomplete milestone described in docs/first-live-rollout-operations-roadmap.md.

Before editing or running commands:
- inspect the repository structure, rollout docs, and current tracker state
- identify which pieces of the milestone already exist and which are still missing
- if the milestone is too large to complete safely, split it into smaller tasks and update docs/first-live-rollout-operations-roadmap.md and docs/first-live-rollout-operations-progress-tracker.md before continuing
- create or switch to a dedicated branch if file edits are needed
- update docs/first-live-rollout-operations-progress-tracker.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- run or document the relevant local or server-side checks
- capture command outcomes without leaking secrets
- stop and record blockers when safety gates fail
- request explicit approval before any live command

Constraints:
- preserve current safety behavior
- no auth layer
- no frontend implementation
- no broad subsystem redesign
- keep the milestone bounded so it can be completed without breaking the current structure
- add focused tests only if code changes are needed
- keep docs/first-live-rollout-operations-progress-tracker.md updated as work proceeds
- make intentional commits only for file changes
- do not push or open a PR unless explicitly requested

At the end, report:
- completed milestone scope
- changed files or operational evidence
- commands run
- branch and commit details
- remaining roadmap items not included
```

## Task Detail Blocks

## Task 01: Confirm Rollout Inputs And Approval Boundary

### Objective
Establish the exact launch context and confirm that no live command will run without explicit approval.

### Relevant code
- `README.md`
- `docs/single-server-deployment-guide.md`
- `docs/operator-console-guide.md`
- `docs/first-live-rollout-readiness-progress-tracker.md`

### Expected result
- The tracker records branch state, launch scope, required credentials, and the explicit live-approval boundary.
- The first rollout remains scoped to `X`.
- No production or live command has been run.

### Verification
- `git status --short --branch`
- `rg -n "First-rollout preflight|X-only|publish-due|--live" README.md docs/single-server-deployment-guide.md docs/operator-console-guide.md`

## Task 02: Run Local Regression And Secret Gates

### Objective
Prove the local checkout is safe before any server-side operation.

### Relevant code
- `tests/test_config.py`
- `tests/test_deploy_assets.py`
- `tests/test_cli.py`
- `tests/test_scheduler.py`
- `tests/test_x_publisher.py`
- `scripts/scan_secrets.sh`

### Expected result
- Targeted tests, full pytest, and secret scan results are recorded.
- Any failure stops the rollout unless the operator explicitly accepts it as unrelated.

### Verification
- `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q`
- `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q`
- `./.venv/bin/pytest -q`
- `scripts/scan_secrets.sh check`

## Task 03: Verify Production Config And Healthcheck

### Objective
Confirm server-side config readiness without exposing secrets.

### Relevant code
- `app/cli.py`
- `app/operations.py`
- `config/providers.yaml`
- `.env.production.example`

### Expected result
- Production config and env presence are confirmed in redacted form.
- Server-side healthcheck result is recorded.
- Missing credentials or config stop the rollout before live publish.

### Verification
- `./.venv/bin/sns-engine rollout-summary --config-dir /opt/sns-content-engine/config`
- `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config`

## Task 04: Run Server Dry-Run Publish And Smoke Helper

### Objective
Prove the production path behaves correctly in dry-run mode and the server deployment is reachable.

### Relevant code
- `scripts/single_server_smoke_check.sh`
- `deploy/systemd/sns-web.service`
- `deploy/systemd/sns-scheduler.service`
- `docs/single-server-deployment-guide.md`

### Expected result
- Dry-run publish output is recorded.
- Smoke helper status is recorded.
- Smoke helper stops before dry-run publish if the config summary is not X-only.
- Unexpected queue, channel, or payload shape blocks live publish.

### Verification
- `./.venv/bin/pytest tests/test_scripts.py -q`
- `./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config`
- `scripts/single_server_smoke_check.sh`

## Task 05: Execute One Approved X Live Publish

### Objective
Run one live `X` publish only after explicit operator approval.

### Relevant code
- `app/scheduler/jobs.py`
- `app/connectors/publishers/x.py`
- `app/connectors/publishers/resolver.py`
- `app/storage/repositories.py`

### Expected result
- The tracker records approval, exact command, result, and publish-job evidence.
- No second live command is run without a new approval.

### Verification
- `./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config --live`

## Task 06: Capture Post-Publish Observation And Next Decision

### Objective
Record the operational outcome and decide whether to continue, pause, retry, or create follow-up work.

### Relevant code
- `app/workflows/history_queries.py`
- `app/storage/repositories.py`
- `docs/operator-console-guide.md`
- `docs/first-live-rollout-operations-progress-tracker.md`

### Expected result
- Publish logs, job state, operator-visible result, and next decision are recorded.
- Follow-up work is separated from the completed rollout event.

### Verification
- `./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config`
- production log inspection command chosen by the operator, if available
