# Single-Server Deployment Readiness Execution Guide

## Purpose

This document tells an autonomous coding agent how to implement the roadmap safely in the current repository.

Use it when you want the agent to:
- read the roadmap before choosing the next task
- inspect the existing code path before editing
- prefer the smallest additive slice
- keep the progress tracker current while working

Progress for live implementation should be tracked in:
- `docs/single-server-deployment-readiness-progress-tracker.md`

## Repository context

This guide assumes the repository already has:
- a working FastAPI application with `/health` and server-rendered `/console/...` routes
- CLI workflows for `healthcheck`, `scheduler run`, `publish-due`, review actions, and DB bootstrap or upgrade
- environment-based secret handling plus a checked-in `.env.example`
- local operator docs for `uvicorn` console startup and a scheduler `systemd` example in `README.md`

High-signal tests to reuse first:
- `tests/test_api.py`
- `tests/test_console.py`
- `tests/test_cli.py`
- `tests/test_scheduler.py`
- `tests/test_env.py`
- `tests/test_operations.py`
- `tests/test_scripts.py`

## Execution environment

- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q`
- Required services:
  - `none for docs and static deployment assets`
  - `local SQLite or operator-provided Postgres only when a task intentionally verifies non-fixture deployment flows`
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global execution rules

### Working style

- Inspect the current code path before editing.
- Read `docs/single-server-deployment-readiness-progress-tracker.md` before choosing the next task.
- Prefer reusing current FastAPI, CLI, env, and operator-doc patterns over inventing a new deployment subsystem.
- Keep each task self-contained and merge-friendly.
- Choose additive deployment assets under `docs/`, `deploy/`, and existing project files over broad redesigns.

### Scope control

- Do not redesign the application into Docker, Kubernetes, or a multi-node topology.
- Do not add in-app authentication, multi-user permissions, or a new frontend.
- Do not redesign the scheduler or publish pipeline when the current service split can be documented and packaged cleanly.
- Keep database guidance practical; the goal is single-server deployment readiness, not a platform migration.

### Safety constraints

- Preserve the current manual-review gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Keep `publish-due` dry-run-first behavior intact by default.
- Keep credentials in environment variables only.
- Keep remote console protection at the reverse proxy or network edge.

### Dirty worktree rules

- Inspect the current branch and working tree before making substantive edits.
- Never overwrite, revert, or stage unrelated changes.
- Keep branch, staging, and commit scope limited to the active task.

### Testing rules

- Add or update targeted tests for every behavior change.
- Use task-specific verification commands from the roadmap when they are provided.
- Run the narrowest relevant test set first.
- If no code behavior changed, record that the task was docs-only and run the narrowest useful regression slice instead of inventing tests.

### Completion rules

- Only finish after code or docs changes, verification, and progress updates are done.
- Do not mark a task complete until the progress tracker includes the final status, changed files, test log, and commit details or the reason a commit was not created.
- If the work cannot be finished safely, leave the task as `blocked` with a clear next step instead of forcing completion.

## Progress tracking rules

Update `docs/single-server-deployment-readiness-progress-tracker.md`:
- at the start of a task
- after meaningful progress
- after tests
- when a blocker or stop reason appears
- when the task is complete

Track:
- current task and milestone
- active branch
- changed files
- implementation notes
- test execution log
- blockers or follow-up items

## Recommended task order

1. Task `01`: Deployment guide and production conventions
2. Task `02`: Runtime packaging and service units
3. Task `03`: Reverse proxy and domain assets for `sns.gilgop.cloud`
4. Task `04`: Remote console safety alignment
5. Task `05`: Smoke checks, backup, and rollback runbook
