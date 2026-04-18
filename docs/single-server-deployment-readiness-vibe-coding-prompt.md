# Single-Server Deployment Readiness Vibe Coding Prompt

## Purpose

This document is the kickoff brief for an autonomous coding agent working in the current repository.

Use it when you want the agent to:
- inspect the real codebase before editing
- preserve the current manual-review and dry-run safety model
- turn one-server deployment intent into small additive repository work
- keep roadmap, execution, and progress docs aligned while implementing

## Initiative Brief

- Initiative name: `Single-Server Deployment Readiness`
- One-sentence outcome: `Make the current review-first SNS content engine deployable on one protected personal server at sns.gilgop.cloud without changing its workflow semantics.`
- Why this matters now:
  - The repository already has the FastAPI app, scheduler runtime, env loader, and healthcheck behavior needed for one-server operation.
  - The deployment path is still scattered across README notes and local-only guidance instead of one repo-backed baseline.
- Core workflow to improve:
  - prepare config, env, and database layout for the server
  - run the web console and scheduler as separate roles
  - expose the console safely through `sns.gilgop.cloud`
  - verify rollout with health and dry-run publish checks
- Explicit non-goals:
  - in-app auth or multi-user permissions
  - Docker, Kubernetes, or distributed deployment redesign
  - auto-approve or auto-publish behavior changes

## Repository Context

The repository already has:
- a FastAPI app with `/health` and `/console/...` routes
- CLI commands for review, scheduling, publishing, healthcheck, and database bootstrap or upgrade
- environment-based secret handling plus `.env.example`
- local operator docs for `uvicorn` and a scheduler `systemd` example in `README.md`

Important current files and patterns:
- Core entrypoints: `app/api/app.py`, `app/api/console.py`, `app/cli.py`
- Existing runtime and env code: `app/env.py`, `app/scheduler/runtime.py`, `app/scheduler/jobs.py`
- Storage and schema surfaces: `app/storage/database.py`, `app/storage/bootstrap.py`
- Current deployment gaps: `README.md`, `docs/operator-console-guide.md`, `pyproject.toml`

## Quality Bar

Preserve:
- the manual review gate
- dry-run-first publish defaults
- environment-only secret handling

Prefer:
- additive changes under `docs/`, `deploy/`, and small packaging/runtime surfaces
- a separate web-service and scheduler-service runtime shape
- edge-layer protection instead of in-app auth

Avoid:
- a broad infrastructure rewrite
- unsafe shortcuts that imply the current console can be exposed publicly without protection
- speculative abstractions that are unnecessary for one personal server

## Execution Constraints

- Base branch: `master`
- Bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q`
- Required local services:
  - `none for docs and static deployment assets`
  - `local SQLite or operator-provided Postgres only when a task intentionally verifies non-fixture deployment flows`
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Expected Agent Behavior

- Inspect the current code path before editing.
- Reuse existing workflows, env handling, and tests before introducing new abstractions.
- Create or refine the roadmap, execution guide, and progress tracker if they are missing or stale.
- Update the progress tracker while working.
- Choose the smallest clean slice that moves the initiative forward safely.
- Record blockers instead of forcing completion through unsafe shortcuts.

## First-Pass Definition Of Done

For the first meaningful iteration, aim to finish when:
- `docs/single-server-deployment-readiness-roadmap.md` exists and reflects the current implementation shape
- `docs/single-server-deployment-readiness-execution-guide.md` exists and contains repo-specific execution rules
- `docs/single-server-deployment-readiness-progress-tracker.md` exists and is updated with current task status
- the first implementation slice is complete, or the exact blocker is documented clearly
- targeted tests have run, or the reason testing could not run is recorded explicitly
- the final report explains what changed, why that shape was chosen, and what remains deferred

## Prompt Template

```text
You are working in an existing repository, not a blank project.

Read these files first:
- docs/single-server-deployment-readiness-vibe-coding-prompt.md
- docs/single-server-deployment-readiness-roadmap.md
- docs/single-server-deployment-readiness-execution-guide.md
- docs/single-server-deployment-readiness-progress-tracker.md

Your job is to turn the initiative into the smallest clean implementation slice that can be shipped safely.

Preserve:
- manual review
- dry-run-first publish behavior
- environment-only secret handling

Prefer:
- additive deployment assets
- separate web and scheduler service roles
- protected remote access at the edge layer

Avoid:
- Docker or Kubernetes redesign
- in-app auth
- public unauthenticated exposure of the current console

Before finishing:
- update the progress tracker
- run the narrowest relevant tests
- report what changed, why it was chosen, what was tested, and what remains deferred
```
