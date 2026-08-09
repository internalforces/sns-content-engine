# First Live Rollout Operations Vibe Coding Prompt

## Purpose
This document is the kickoff brief for an autonomous coding agent helping with the first protected live rollout from an existing repository.

Use it when you want the agent to absorb the current rollout intent quickly, inspect the checked-in deployment and safety assets, shape the smallest safe operational slice, and help execute or document the preflight flow with minimal back-and-forth.

The prompt below is intentionally opinionated:
- it starts from the current repository and completed readiness work instead of inventing a new deployment plan
- it treats the first live rollout as an operator-controlled production event, not a broad development initiative
- it preserves manual review, dry-run-first publishing, env-only secret handling, and explicit live-publish approval
- it turns the remaining rollout intent into a roadmap, execution guide, progress tracker, and first operational slice

## Generated document naming
When instantiating this template, keep the document names explicit so each file is easy to identify at a glance.

- Vibe coding prompt file: `docs/first-live-rollout-operations-vibe-coding-prompt.md`
- Roadmap file: `docs/first-live-rollout-operations-roadmap.md`
- Execution guide file: `docs/first-live-rollout-operations-execution-guide.md`
- Progress tracker file: `docs/first-live-rollout-operations-progress-tracker.md`
- Avoid ambiguous names like `prompt.md`, `brief.md`, `notes.md`, or `plan.md` when multiple initiatives may coexist.

## Initiative Brief
- Initiative name: `First Live Rollout Operations`
- One-sentence outcome: `Execute the first protected X live rollout from the completed readiness baseline by running preflight checks, confirming production configuration, performing one explicit live publish only after approval, and recording post-publish observations.`
- Why this matters now:
  - The `First Live Rollout Readiness` roadmap is complete, the repository is green, and the remaining work is operational verification rather than another code-hardening slice.
  - The first live event should be deliberate, observable, and easy to stop or retry without weakening the manual-review and dry-run-first safety model.
- Primary user, operator, or workflow owner:
  - the solo operator preparing the first protected production publish
  - an autonomous coding agent assisting with preflight verification, command sequencing, result capture, and blocker documentation
- Core workflow to improve:
  - confirm the local and server-side rollout baseline before touching live publishing
  - run regression, healthcheck, dry-run publish, secret scan, and smoke-check gates in a repeatable order
  - execute a single X live publish only after explicit operator approval
  - capture post-publish evidence, rollback or hold decisions, and follow-up hardening ideas
- Explicit non-goals:
  - Threads live rollout expansion
  - LinkedIn direct-publish adapter work
  - auth, multi-user permissions, Docker, Kubernetes, or broader infrastructure redesign
  - automatic live publishing without a human decision

## Repository Context
The repository already has:
- a FastAPI app, scheduler runtime, CLI workflows, and checked-in one-server deployment assets
- completed first-live-rollout readiness docs and progress tracking
- OpenAI-first provider guidance, blank-env-safe provider handling, and env-only secret conventions
- X live publishing support with dry-run as the default `publish-due` behavior

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/api/app.py`
- Existing workflows or services: `app/scheduler/runtime.py`, `app/scheduler/jobs.py`, `app/connectors/publishers/x.py`
- Data or schema surfaces: `app/storage/database.py`, `app/storage/bootstrap.py`
- Current placeholder, gap, or friction point: first production execution requires real server access, real env values, and operator confirmation outside the repository
- Existing tests to reuse first: `tests/test_cli.py`, `tests/test_scheduler.py`, `tests/test_x_publisher.py`, `tests/test_deploy_assets.py`
- Existing docs to align with: `README.md`, `docs/single-server-deployment-guide.md`, `docs/operator-console-guide.md`, `docs/first-live-rollout-readiness-progress-tracker.md`

## Product Intent And Quality Bar
The desired execution should:
- leave the repository green before any live operation
- make every preflight command and result auditable in `docs/first-live-rollout-operations-progress-tracker.md`
- keep the first live publish scoped to `X`
- stop safely and record the exact blocker if credentials, server state, smoke checks, or dry-run output are not ready

The agent should preserve:
- the manual review gate
- dry-run-first publish semantics
- environment-only secret handling
- explicit operator approval before any `--live` command

The agent should avoid:
- broad deployment redesign
- speculative new provider, publisher, or infrastructure abstractions
- expanding live-publish scope beyond `X`
- unsafe shortcuts that skip tests, smoke checks, secret scans, or operator approval

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands:
  - `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q`
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest -q`
  - `scripts/scan_secrets.sh check`
- Required local services:
  - `none for local docs and test preflight`
  - production server services only when running server-side smoke checks
- Required env files, secrets, or fixtures:
  - production `.env` on the server for live provider and publisher credentials
  - `SNS_SMOKE_EDGE_USER` and `SNS_SMOKE_EDGE_PASSWORD` only when running `scripts/single_server_smoke_check.sh`
  - real X publisher credentials only when the operator explicitly approves live verification
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Expected Agent Behavior
- Inspect the current code path and rollout docs before proposing or making edits.
- Reuse existing repository workflows, tests, deployment assets, and docs before introducing new scripts.
- Prefer the smallest safe operational slice that moves the rollout forward.
- Create or refine the roadmap, execution guide, and progress tracker before live execution if they do not already exist.
- Update the progress tracker when commands are run, results change, or blockers appear.
- Keep branch, commit, and staging scope limited to documentation or any explicitly requested hardening task.
- Record blockers clearly instead of forcing completion through unsafe shortcuts.

## First-Pass Definition Of Done
For the first meaningful iteration, aim to finish when:
- `docs/first-live-rollout-operations-roadmap.md` exists and reflects the current operational rollout shape
- `docs/first-live-rollout-operations-execution-guide.md` exists and contains repo-specific execution rules
- `docs/first-live-rollout-operations-progress-tracker.md` exists and is initialized with current task status
- the first operational slice is complete, or the exact blocker is documented clearly
- targeted tests and checks have run, or the reason testing could not run is recorded explicitly
- the final report explains what changed, why that shape was chosen, and what remains deferred

## Prompt Template
Copy, adapt, and send the block below to the agent when starting or resuming work.

```text
You are working in an existing repository, not a blank project.

Read this document first:
- docs/first-live-rollout-operations-vibe-coding-prompt.md

Then inspect and use these companion docs when they exist:
- docs/first-live-rollout-operations-roadmap.md
- docs/first-live-rollout-operations-execution-guide.md
- docs/first-live-rollout-operations-progress-tracker.md

Your job is to turn the first live rollout operations initiative into the smallest clean execution slice that can be completed safely.

Initiative brief
- Name: First Live Rollout Operations
- Outcome: Execute the first protected X live rollout from the completed readiness baseline by running preflight checks, confirming production configuration, performing one explicit live publish only after approval, and recording post-publish observations.
- Why now:
  - First Live Rollout Readiness is complete and the remaining work is operational verification.
  - The first live event should be deliberate, observable, and easy to stop or retry without weakening safety defaults.
- Core workflow to improve:
  - confirm local and server-side rollout baseline
  - run regression, healthcheck, dry-run publish, secret scan, and smoke-check gates
  - execute one X live publish only after explicit operator approval
  - capture post-publish evidence and follow-up decisions
- Explicit non-goals:
  - Threads live rollout
  - LinkedIn direct publish
  - auth or infrastructure redesign

Repository context
- Existing capabilities:
  - FastAPI app, CLI workflows, scheduler runtime, X publisher, and checked-in one-server deployment assets
  - completed first-live-rollout readiness docs
  - OpenAI-first provider setup and blank-env-safe provider handling
  - dry-run-first scheduler publish behavior
- Important files and patterns:
  - app/cli.py
  - app/scheduler/jobs.py
  - app/connectors/publishers/x.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_x_publisher.py
  - docs/single-server-deployment-guide.md

Quality bar
- Preserve:
  - manual review
  - dry-run-first publish behavior
  - env-only secret handling
  - explicit operator approval before live publish
- Prefer:
  - existing CLI, scheduler, smoke-check, and documentation surfaces
  - additive docs or tiny safety fixes if blockers are found
- Avoid:
  - broad deployment redesign
  - expanding live publish beyond X
  - running `--live` without explicit approval

Execution expectations
- Inspect the current implementation and rollout docs before editing or running commands.
- Reuse existing workflows, tests, and deployment assets where possible.
- Choose the smallest safe slice that satisfies the current operational goal.
- Update the progress tracker while working.
- Run the narrowest relevant checks first, then broader regression before live execution.
- Do not push or open a PR unless explicitly asked.

Environment constraints
- Base branch: master
- Bootstrap commands:
  - python -m pip install -e ".[dev]"
  - ./.venv/bin/python -m app.cli version
- Narrow verification commands:
  - ./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q
  - ./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q
- Broader regression commands:
  - ./.venv/bin/pytest -q
  - scripts/scan_secrets.sh check
- Required services:
  - none for local tests and docs
  - production server services for smoke checks
- Required env or fixtures:
  - production .env on the server
  - SNS_SMOKE_EDGE_USER and SNS_SMOKE_EDGE_PASSWORD for smoke checks
  - real X credentials only for explicitly approved live publish
- Package install policy: ask_first
- Push and PR policy: do_not_push_without_explicit_request

Definition of done
- The next operational slice is complete or blocked for a clearly recorded reason.
- Relevant docs are updated to match reality.
- Targeted tests or checks are run, or the exact reason they could not run is documented.
- The final report includes:
  - what changed or what was verified
  - why that execution shape was chosen
  - commands run
  - branch and commit details if files changed
  - any intentionally deferred follow-up
```

## Recommended Instantiation Order
When using this template set for a new initiative, the usual order is:

1. Create `docs/first-live-rollout-operations-vibe-coding-prompt.md`
2. Create `docs/first-live-rollout-operations-roadmap.md`
3. Create `docs/first-live-rollout-operations-execution-guide.md`
4. Create `docs/first-live-rollout-operations-progress-tracker.md`

If some of these files already exist, refine them instead of creating duplicates.
