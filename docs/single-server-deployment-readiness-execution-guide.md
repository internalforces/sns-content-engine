# Single-Server Deployment Readiness Autonomous Execution Guide

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in `docs/single-server-deployment-readiness-roadmap.md`, inspect the repository, choose the smallest clean implementation shape for each gap, make code and docs changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current FastAPI, CLI, and review-first implementation instead of inventing a new deployment stack from scratch
- they constrain deployment work so the existing safety model stays intact
- they require reusing current workflows, environment handling, and operator docs before adding new abstractions
- they preserve the manual-review gate and dry-run-first publish behavior unless a task explicitly expands a surface

Progress for live implementation should be tracked in:
- `docs/single-server-deployment-readiness-progress-tracker.md`

## Generated document naming
When instantiating this template, use filenames that make each document's identity obvious at a glance.

- Roadmap file: `docs/single-server-deployment-readiness-roadmap.md`
- Execution guide file: `docs/single-server-deployment-readiness-execution-guide.md`
- Progress tracker file: `docs/single-server-deployment-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/single-server-deployment-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `prompt.md`, `guide.md`, or `progress.md` when multiple initiatives may coexist.

## Repository Context
This guide was shaped for the repository state that already has:
- a working FastAPI application with `/health` and server-rendered `/console/...` routes
- CLI workflows for `healthcheck`, `scheduler run`, `publish-due`, review actions, and DB bootstrap or upgrade
- environment-based secret handling plus a checked-in `.env.example`
- local operator docs for `uvicorn` console startup and a README example for a scheduler `systemd` service
- a current deployment gap where remote web-service, reverse-proxy, TLS, and access-protection assets are not yet carried by the repository

Important current files and patterns:
- Core entrypoints: `app/api/app.py`, `app/api/console.py`, `app/cli.py`
- Core workflows and services: `app/scheduler/runtime.py`, `app/scheduler/jobs.py`, `app/env.py`
- Storage and schema logic: `app/storage/database.py`, `app/storage/bootstrap.py`
- Current deployment gaps: `pyproject.toml`, `README.md`, `docs/operator-console-guide.md`
- Existing operator docs: `README.md`, `docs/operator-console-guide.md`, `docs/operator-control-plane-api.md`
- Existing roadmap: `docs/single-server-deployment-readiness-roadmap.md`

High-signal tests already exist and should be reused instead of inventing a new test structure:
- `tests/test_api.py`
- `tests/test_console.py`
- `tests/test_cli.py`
- `tests/test_scheduler.py`
- `tests/test_env.py`
- `tests/test_operations.py`
- `tests/test_scripts.py`

## Execution Environment
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands by area:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q`
- Broader regression commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py tests/test_cli.py tests/test_scheduler.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q`
- Required services:
  - `none for docs, static deployment assets, and most test paths`
  - `local SQLite or operator-provided Postgres only when a task intentionally adds non-fixture smoke validation`
- Required env files, secrets, or fixtures:
  - `.env.example` for checked-in env shape
  - `a real .env or EnvironmentFile only when testing non-fixture runtime commands`
  - `config/ or another operator-approved config directory`
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path before editing.
- Read `docs/single-server-deployment-readiness-progress-tracker.md` before choosing the next task.
- Prefer reusing current FastAPI, CLI, env, and operator-doc patterns over inventing a new deployment subsystem.
- Keep each task self-contained and merge-friendly.
- Choose additive deployment assets under `docs/`, `deploy/`, and existing project files over broad redesigns.
- Preserve current runtime behavior unless a task explicitly updates a shared abstraction.

### Resume rules
- If `docs/single-server-deployment-readiness-progress-tracker.md` shows a current task with status `in_progress` or `blocked`, resume or resolve that task before selecting a new one unless the roadmap was intentionally reprioritized.
- Only choose the next unfinished task when there is no active task that still owns the current branch or implementation state.
- If the active task was blocked by a fixable local issue and the scope is still the same, keep the same task ID and continue instead of creating a new task.

### Roadmap shaping rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- When creating or refining the roadmap, choose only as many milestones and tasks as are needed to make forward progress safely.
- The sizing rule is: split work so it can be completed without breaking the current structure, safety model, workflow semantics, or operator experience.
- Prefer the smallest additive slices that fit the existing architecture.
- Split a task or milestone when it would otherwise mix runtime packaging, service assets, reverse-proxy config, and recovery docs too broadly or make verification unclear.
- Merge adjacent tiny items when they share the same code path, tests, and commit scope.
- If the roadmap shape changes during implementation, update `docs/single-server-deployment-readiness-roadmap.md` and `docs/single-server-deployment-readiness-progress-tracker.md` before continuing.

### Scope control
- Do not redesign the application into Docker, Kubernetes, or a multi-node topology unless the task explicitly requires it.
- Do not add in-app authentication, multi-user permissions, or a new frontend; remote protection belongs at the edge layer in this initiative.
- Do not redesign the scheduler or publish pipeline when existing service separation and healthcheck semantics can be documented and packaged cleanly.
- Keep database guidance practical; the goal is single-server deployment readiness, not a full platform migration.

### Dirty worktree rules
- Inspect the current branch and working tree before making substantive edits when repository tooling is available.
- Never overwrite, revert, or stage unrelated changes.
- If user or pre-existing changes conflict directly with the active task in the same files, stop, record the conflict in `docs/single-server-deployment-readiness-progress-tracker.md`, and treat the task as blocked until the conflict is resolved.
- Keep branch, staging, and commit scope limited to the active task.

### Safety constraints
- Preserve the current manual-review gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Keep `publish-due` dry-run-first behavior intact by default.
- Keep credentials in environment variables only; do not move secrets into YAML or checked-in deployment files.
- Keep remote console protection at the reverse-proxy or network edge; do not imply that the current app can be exposed directly to the public internet.

### Blocked-task rules
- Try the smallest reasonable local investigation first when a blocker appears.
- If progress is blocked by missing configuration, unavailable services, missing credentials, conflicting local edits, or unrelated failing tests, record the exact blocker and stop reason in `docs/single-server-deployment-readiness-progress-tracker.md`.
- Mark the task `blocked` when work cannot continue safely inside the intended scope.
- Do not mark blocked work as `done`.
- Do not create a normal task-completion commit for blocked work; only create a checkpoint commit if the partial state is independently safe, intentionally scoped, and clearly documented.

### Testing rules
- Add or update targeted tests for every behavior change.
- Use task-specific verification commands from `docs/single-server-deployment-readiness-roadmap.md` when they are provided.
- Run the narrowest relevant test set first.
- If a shared CLI, env, API, or scheduler surface changes, run one broader regression slice too.
- If no explicit test command exists, infer the narrowest relevant command from the repository and record that reasoning in `docs/single-server-deployment-readiness-progress-tracker.md`.
- Distinguish newly introduced failures from pre-existing failures or environment failures.
- If testing cannot run, record the exact command and reason as `not_run` or `pre_existing_failure`.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-deployment-guide-baseline`
  - `codex/task-03-sns-gilgop-cloud-proxy`
  - `codex/task-05-deploy-smoke-runbook`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Do not push branches or open pull requests unless explicitly requested.
- Use a clear commit message tied to the task outcome, for example:
  - `Add single-server deployment guide`
  - `Add web and scheduler deployment units`
  - `Add sns.gilgop.cloud proxy config`

### Completion rules
- Only finish after code or docs changes, verification, and progress updates are done.
- Do not mark a task complete until `docs/single-server-deployment-readiness-progress-tracker.md` includes the final status, changed files, test log, and commit details or the reason a commit was not created.
- If the work cannot be finished safely, leave the task as `blocked` with a clear next step instead of forcing completion.
- Report:
  - what changed
  - why that shape was chosen
  - tests run
  - branch and commit details
  - any remaining follow-up intentionally deferred

## Progress Tracking Rules
The agent must keep `docs/single-server-deployment-readiness-progress-tracker.md` updated while implementing this roadmap.

### When to update
- At the start of a task:
  - set the current task
  - mark status as `in_progress`
  - record the intended scope
  - record the active branch
- During implementation:
  - append meaningful progress notes when the implementation shape changes, key files are edited, or a blocker is discovered
  - update the changed-files list as files are touched
- After tests:
  - record test commands and pass or fail status
- At task completion:
  - mark the task `done`
  - summarize the final changed files
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
- files changed for the active task
- implementation notes
- test execution log
- stop reason or blockers
- open questions
- pre-existing failures or environment constraints
- blockers or follow-up items

### Tracking constraints
- Keep entries short and factual.
- Update the existing progress file instead of creating a new ad hoc log.
- Avoid duplicate log entries when rerunning the same step; update the existing note if it still describes the current state.
- Do not mark a task done before the relevant tests have run, unless testing is impossible and the reason is recorded explicitly.

## Output Contract For The Agent
Unless the caller requests a different format, end each task with:

```text
Summary
- ...

Changed files
- ...

Tests run
- ...

Branch and commit
- ...

Follow-up
- ...
```

## Recommended Task Order
List the actual tasks defined in `docs/single-server-deployment-readiness-roadmap.md` in dependency order. Add or remove lines as needed; the task count is not fixed.

1. Task 01: Deployment guide and production conventions
2. Task 02: Runtime packaging and service units
3. Task 03: Reverse proxy and domain assets for `sns.gilgop.cloud`
4. Task 04: Remote console safety alignment
5. Task 05: Smoke checks, backup, and rollback runbook

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the Single-Server Deployment Readiness roadmap in this repository.

Start by reading:
- docs/single-server-deployment-readiness-roadmap.md
- docs/single-server-deployment-readiness-execution-guide.md
- docs/single-server-deployment-readiness-progress-tracker.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/single-server-deployment-readiness-execution-guide.md.

Your job:
1. Determine whether docs/single-server-deployment-readiness-progress-tracker.md already shows an active task. If it is `in_progress` or `blocked`, resume or resolve that task unless the roadmap was intentionally reprioritized.
2. If there is no active task, determine the next unfinished task in the recommended order.
3. If the roadmap shape is incomplete, too large, or unsafe to execute cleanly, refine the task or milestone boundaries using the smallest additive slices that preserve the current structure, then update docs/single-server-deployment-readiness-roadmap.md and docs/single-server-deployment-readiness-progress-tracker.md before coding.
4. Create or switch to a dedicated task branch using the git workflow rules in docs/single-server-deployment-readiness-execution-guide.md.
5. Update docs/single-server-deployment-readiness-progress-tracker.md to mark that task in progress and note the intended scope, branch, and verification plan.
6. Implement only that task cleanly and completely.
7. Keep docs/single-server-deployment-readiness-progress-tracker.md updated during the work with changed files, progress notes, blockers, or stop reasons.
8. Add or update targeted tests.
9. Run the task verification commands from docs/single-server-deployment-readiness-roadmap.md, plus one broader regression slice if shared behavior changed, and record the results in docs/single-server-deployment-readiness-progress-tracker.md.
10. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
11. Mark the task complete in docs/single-server-deployment-readiness-progress-tracker.md when verified, including branch and commit details, or leave it `blocked` with a clear next step if it cannot be finished safely.
12. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve the manual review gate
- keep dry-run-first publish behavior as the default gate
- avoid broad infrastructure rewrites
- do not add in-app auth, a frontend redesign, or speculative platform work unless the task explicitly requires it
- do not push or open a PR unless explicitly requested

If the next task is ambiguous, choose the smallest sensible interpretation that best makes the current backend deployable on one protected server without changing workflow semantics.
```
