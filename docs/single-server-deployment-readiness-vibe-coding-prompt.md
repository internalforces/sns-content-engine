# Single-Server Deployment Readiness Vibe Coding Prompt

## Purpose
This document is the kickoff brief for an autonomous coding agent working in an existing repository.

Use it when you want the agent to absorb the product intent quickly, inspect the real codebase, shape the smallest safe implementation slice, and start coding with minimal back-and-forth.

The prompt below is intentionally opinionated:
- it starts from the current repository instead of inventing a blank-slate rewrite
- it prefers additive changes over broad redesigns
- it preserves the manual review gate, dry-run-first publish defaults, and env-only credential model
- it turns vague deployment intent into a roadmap, execution guide, progress tracker, and first implementation slice

## Generated document naming
When instantiating this template, keep the document names explicit so each file is easy to identify at a glance.

- Vibe coding prompt file: `docs/single-server-deployment-readiness-vibe-coding-prompt.md`
- Roadmap file: `docs/single-server-deployment-readiness-roadmap.md`
- Execution guide file: `docs/single-server-deployment-readiness-execution-guide.md`
- Progress tracker file: `docs/single-server-deployment-readiness-progress-tracker.md`
- Avoid ambiguous names like `prompt.md`, `brief.md`, `notes.md`, or `plan.md` when multiple initiatives may coexist.

## Initiative Brief
- Initiative name: `Single-Server Deployment Readiness`
- One-sentence outcome: `Make the current review-first SNS content engine deployable on one protected personal server at sns.gilgop.cloud without changing its workflow semantics.`
- Why this matters now:
  - The repository already has the core FastAPI console, scheduler, env handling, and healthcheck behavior needed for a personal-server deployment, but the deployment assets are still scattered or missing.
  - The next implementation stage should turn those pieces into a repeatable, documented, repo-backed deployment path before any live rollout happens.
- Primary user, operator, or workflow owner:
  - A single operator deploying and running the system on a personal server
  - Future maintainers extending deployment assets without weakening safety defaults
- Core workflow to improve:
  - prepare config, env, and database layout for the server
  - expose the web console safely through `sns.gilgop.cloud`
  - run the scheduler as a separate long-running service
  - verify the rollout with health, console, and dry-run publish checks
- Explicit non-goals:
  - in-app auth, multi-user permissions, or a frontend redesign
  - Docker, Kubernetes, or distributed deployment redesign
  - auto-approve, auto-publish, or any change to current safety gates

## Repository Context
The repository already has:
- a FastAPI app with `/health` and `/console/...` routes
- CLI commands for review, scheduling, publishing, healthcheck, and database bootstrap or upgrade
- environment-based secret handling plus `.env.example`
- local operator docs for `uvicorn` and a README example for scheduler `systemd`

Important current files and patterns:
- Core entrypoints: `app/api/app.py`, `app/api/console.py`, `app/cli.py`
- Existing workflows or services: `app/scheduler/runtime.py`, `app/scheduler/jobs.py`, `app/env.py`
- Data or schema surfaces: `app/storage/database.py`, `app/storage/bootstrap.py`
- Current placeholder, gap, or friction point: `pyproject.toml`, `README.md`, `docs/operator-console-guide.md`
- Existing tests to reuse first: `tests/test_api.py`, `tests/test_console.py`, `tests/test_cli.py`, `tests/test_scheduler.py`, `tests/test_env.py`, `tests/test_scripts.py`
- Existing docs to align with: `README.md`, `docs/operator-console-guide.md`, `docs/operator-control-plane-api.md`

## Product Intent And Quality Bar
The desired implementation should:
- make the single-server deployment path explicit and repeatable
- keep the web console and scheduler as separate roles
- ensure `sns.gilgop.cloud` deployment is documented as HTTPS and edge-protected
- give the operator a practical rollout, smoke-check, backup, and rollback path

The agent should preserve:
- the manual review gate
- dry-run-first publish behavior
- environment-only secret handling

The agent should avoid:
- a broad infrastructure rewrite
- in-app auth or permission work
- speculative deployment abstractions that are not required for one personal server
- unsafe shortcuts that imply the current browser console can be exposed publicly without protection

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q`
- Broader regression commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py tests/test_cli.py tests/test_scheduler.py -q`
  - `PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q`
- Required local services:
  - `none`
  - `local SQLite or operator-provided Postgres only when a task intentionally verifies non-fixture deployment flows`
- Required env files, secrets, or fixtures:
  - `.env.example` is the checked-in reference
  - `a real .env or EnvironmentFile is only needed when running non-fixture runtime checks`
  - `config/ and existing test fixtures already cover most code paths`
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Expected Agent Behavior
- Inspect the current code path before proposing or making edits.
- Reuse existing repository patterns, workflows, tests, and schema shapes before introducing new abstractions.
- Prefer the smallest clean implementation slice that moves the initiative forward safely.
- Create or refine the roadmap, execution guide, and progress tracker before large implementation work if they do not already exist.
- Update the roadmap and progress tracker when the implementation shape changes materially.
- Keep branch, commit, and staging scope limited to the active task.
- Record blockers clearly instead of forcing completion through unsafe shortcuts.

## First-Pass Definition Of Done
For the first meaningful iteration, aim to finish when:
- `docs/single-server-deployment-readiness-roadmap.md` exists and reflects the current implementation shape
- `docs/single-server-deployment-readiness-execution-guide.md` exists and contains repo-specific execution rules
- `docs/single-server-deployment-readiness-progress-tracker.md` exists and is updated with current task status
- the first implementation slice is complete, or the exact blocker is documented clearly
- targeted tests have run, or the reason testing could not run is recorded explicitly
- the final report explains what changed, why that shape was chosen, and what remains deferred

## Prompt Template
Copy, adapt, and send the block below to the agent when starting or resuming work.

```text
You are working in an existing repository, not a blank project.

Read this document first:
- docs/single-server-deployment-readiness-vibe-coding-prompt.md

Then inspect and use these companion docs when they exist:
- docs/single-server-deployment-readiness-roadmap.md
- docs/single-server-deployment-readiness-execution-guide.md
- docs/single-server-deployment-readiness-progress-tracker.md

Your job is to turn the initiative into the smallest clean implementation slice that can be shipped safely.

Initiative brief
- Name: Single-Server Deployment Readiness
- Outcome: Make the current review-first SNS content engine deployable on one protected personal server at sns.gilgop.cloud.
- Why now:
  - The codebase already has the app, scheduler, env loader, and operator workflows needed for a one-server deployment, but it lacks a concrete repository-backed deployment path.
  - We want deployment to be documented and repeatable before any live rollout.
- Core workflow to improve:
  - prepare config, env, and database layout
  - expose the console safely at sns.gilgop.cloud
  - run the scheduler as a separate service
  - verify the rollout with health and dry-run checks
- Explicit non-goals:
  - in-app auth or multi-user permission work
  - Docker, Kubernetes, or distributed deployment redesign

Repository context
- Existing capabilities:
  - FastAPI health and console routes already exist
  - CLI scheduler, review, and DB commands already exist
  - env-based secret handling and `.env.example` already exist
- Important files and patterns:
  - app/api/app.py
  - app/api/console.py
  - app/cli.py
  - app/env.py
  - pyproject.toml
  - README.md
  - docs/operator-console-guide.md

Quality bar
- Preserve:
  - the manual review gate
  - dry-run-first publish behavior
  - environment-only secret handling
- Prefer:
  - additive deployment assets under docs/ and deploy/
  - a separate web-service and scheduler-service runtime shape
  - edge-layer protection instead of in-app auth
- Avoid:
  - broad infrastructure redesign
  - unsafe shortcuts that imply the current console can be exposed directly to the public internet

Execution expectations
- Inspect the current implementation before editing.
- Reuse existing workflows, tests, and schema shapes where possible.
- Choose the smallest additive slice that satisfies the goal safely.
- Create or refine the roadmap, execution guide, and progress tracker if they are missing or stale.
- Update the progress tracker while working.
- Run the narrowest relevant tests first, then one broader regression slice if shared behavior changed.
- Do not push or open a PR unless explicitly asked.

Environment constraints
- Base branch: master
- Bootstrap commands:
  - python -m pip install -e ".[dev]"
  - sns-engine db init --database-url sqlite:///data/sns_content_engine.db
- Narrow verification commands:
  - PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py -q
  - PYTHONPATH=$PWD pytest tests/test_cli.py tests/test_scheduler.py tests/test_env.py -q
  - PYTHONPATH=$PWD pytest tests/test_operations.py tests/test_scripts.py -q
- Broader regression commands:
  - PYTHONPATH=$PWD pytest tests/test_api.py tests/test_console.py tests/test_cli.py tests/test_scheduler.py -q
  - PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q
- Required services:
  - none
  - local SQLite or operator-provided Postgres only when a task intentionally needs non-fixture checks
- Required env or fixtures:
  - .env.example already exists
  - a real .env or EnvironmentFile is only needed for real runtime checks
- Package install policy: ask_first
- Push and PR policy: do_not_push_without_explicit_request

Definition of done
- The next implementation slice is complete or blocked for a clearly recorded reason.
- Relevant docs are updated to match reality.
- Targeted tests are run, or the exact reason they could not run is documented.
- The final report includes:
  - what changed
  - why that implementation shape was chosen
  - tests run
  - branch and commit details
  - any intentionally deferred follow-up
```

## Recommended Instantiation Order
When using this template set for a new initiative, the usual order is:

1. Create `docs/single-server-deployment-readiness-vibe-coding-prompt.md`
2. Create `docs/single-server-deployment-readiness-roadmap.md`
3. Create `docs/single-server-deployment-readiness-execution-guide.md`
4. Create `docs/single-server-deployment-readiness-progress-tracker.md`

If some of these files already exist, refine them instead of creating duplicates.
