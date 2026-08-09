# Threads API Publish Readiness Vibe Coding Prompt

## Purpose
This document is the kickoff brief for an autonomous coding agent working in an existing repository.

Use it when you want the agent to absorb the product intent quickly, inspect the real codebase, shape the smallest safe implementation slice, and start coding with minimal back-and-forth.

The prompt below is intentionally opinionated:
- it starts from the current repository instead of inventing a blank-slate rewrite,
- it prefers additive changes over broad redesigns,
- it preserves the manual review gate, dry-run publish defaults, and LinkedIn manual semantics,
- it turns vague product intent into a roadmap, execution guide, progress tracker, and first implementation slice.

## Generated document naming
When instantiating this template, keep the document names explicit so each file is easy to identify at a glance.

- Vibe coding prompt file: `docs/threads-api-publish-readiness-vibe-coding-prompt.md`
- Roadmap file: `docs/threads-api-publish-readiness-roadmap.md`
- Execution guide file: `docs/threads-api-publish-readiness-execution-guide.md`
- Progress tracker file: `docs/threads-api-publish-readiness-progress-tracker.md`
- Avoid ambiguous names like `prompt.md`, `brief.md`, `notes.md`, or `plan.md` when multiple initiatives may coexist.

## Initiative Brief
- Initiative name: `Threads API Publish Readiness`
- One-sentence outcome: `Make Threads direct publishing a config-gated path that an operator can enable through one env-referenced credential bundle while preserving the current review and scheduler safety model.`
- Why this matters now:
  - Threads drafts and publish-job tracking already exist, so manual upload is now the main operator friction point instead of missing pipeline structure.
  - The repository already has a working X live-publish path that should be reused before more channel-specific drift accumulates.
- Primary user, operator, or workflow owner:
  - local operator running the content engine through CLI, API, or browser console
  - repository maintainer extending publisher adapters without destabilizing X or LinkedIn behavior
- Core workflow to improve:
  - approve a Threads draft under the existing review gate
  - schedule or backfill a Threads publish job through the current workflow
  - publish the due job through a configured Threads credential bundle and record the result in existing publish-job surfaces
- Explicit non-goals:
  - direct LinkedIn live publishing
  - auth or frontend redesign
  - media upload, reply chains, or broad platform redesign in the first pass

## Repository Context
The repository already has:
- config-driven multichannel draft generation for `x`, `linkedin`, and `threads`
- persisted review, publish-job, and publish-log state
- a live X publisher adapter with config-backed resolution
- API and server-rendered console surfaces for review, publish-job visibility, and scheduler actions

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/api/app.py`
- Existing workflows or services: `app/workflows/review_queue.py`, `app/scheduler/jobs.py`
- Data or schema surfaces: `app/storage/repositories.py`, `app/storage/models.py`
- Current placeholder, gap, or friction point: `app/connectors/publishers/resolver.py`, `app/api/console.py`
- Existing tests to reuse first: `tests/test_x_publisher.py`, `tests/test_scheduler.py`
- Existing docs to align with: `README.md`, `docs/operator-console-guide.md`, `docs/operator-control-plane-api.md`

## Product Intent And Quality Bar
The desired implementation should:
- keep operator setup centered on one env-referenced credential bundle rather than multiple manual toggles
- reuse existing scheduler, publish-log, review, API, and console paths instead of adding a parallel Threads-only workflow
- fall back to the current manual Threads handoff when live publishing is not configured
- surface readable success and failure results through the existing publish-job detail views

The agent should preserve:
- the current manual review gate before any external publish
- `publish-due` dry-run-by-default behavior
- the existing X live-publish path and LinkedIn manual-only path unless a task explicitly changes them

The agent should avoid:
- broad scheduler or persistence redesign
- a second publisher-resolution system separate from `publisher.credential_ref`
- new auth or frontend surfaces
- unsafe shortcuts that bypass review or publish validation

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands:
  - `./.venv/bin/pytest tests/test_x_publisher.py tests/test_scheduler.py -q`
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_scheduler.py tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest -q`
- Required local services:
  - `none for adapter and workflow tests`
  - `optional Threads API connectivity only for explicit live smoke verification`
- Required env files, secrets, or fixtures:
  - `.env is optional unless a live Threads publish test is being exercised`
  - `temporary SQLite fixtures and per-test config helpers already exist in the repository`
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
- `docs/threads-api-publish-readiness-roadmap.md` exists and reflects the current implementation shape
- `docs/threads-api-publish-readiness-execution-guide.md` exists and contains repo-specific execution rules
- `docs/threads-api-publish-readiness-progress-tracker.md` exists and is updated with current task status
- the first implementation slice is complete, or the exact blocker is documented clearly
- targeted tests have run, or the reason testing could not run is recorded explicitly
- the final report explains what changed, why that shape was chosen, and what remains deferred

## Prompt Template
Copy, adapt, and send the block below to the agent when starting or resuming work.

```text
You are working in an existing repository, not a blank project.

Read this document first:
- docs/threads-api-publish-readiness-vibe-coding-prompt.md

Then inspect and use these companion docs when they exist:
- docs/threads-api-publish-readiness-roadmap.md
- docs/threads-api-publish-readiness-execution-guide.md
- docs/threads-api-publish-readiness-progress-tracker.md

Your job is to turn the initiative into the smallest clean implementation slice that can be shipped safely.

Initiative brief
- Name: Threads API Publish Readiness
- Outcome: Make Threads direct publishing a config-gated path that an operator can enable through one env-referenced credential bundle while preserving the current review and scheduler safety model.
- Why now:
  - Threads drafts and manual handoff tracking already exist, so direct publishing is now the next highest-friction gap.
  - The repository already has a reusable X live-publish architecture.
- Core workflow to improve:
  - approve a Threads draft
  - schedule or backfill a Threads publish job
  - publish that due job through configured credentials and record the result
- Explicit non-goals:
  - LinkedIn direct integration
  - auth or frontend redesign

Repository context
- Existing capabilities:
  - multichannel draft generation
  - persisted publish jobs and logs
  - X live publishing through the scheduler path
- Important files and patterns:
  - app/cli.py
  - app/workflows/review_queue.py
  - app/scheduler/jobs.py
  - app/connectors/publishers/resolver.py
  - tests/test_x_publisher.py

Quality bar
- Preserve:
  - the manual review gate
  - dry-run publish default
- Prefer:
  - additive adapter or resolver work
  - one env-referenced credential bundle for operator setup
- Avoid:
  - broad redesign
  - hidden review or publish bypasses

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
  - ./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db
- Narrow verification commands:
  - ./.venv/bin/pytest tests/test_x_publisher.py tests/test_scheduler.py -q
  - ./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q
- Broader regression commands:
  - ./.venv/bin/pytest tests/test_scheduler.py tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q
  - ./.venv/bin/pytest -q
- Required services:
  - none for adapter and workflow tests
  - optional Threads API connectivity for explicit smoke verification
- Required env or fixtures:
  - .env optional unless live Threads testing is requested
  - temp SQLite fixtures and test config helpers already exist
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

1. Create `docs/threads-api-publish-readiness-vibe-coding-prompt.md`
2. Create `docs/threads-api-publish-readiness-roadmap.md`
3. Create `docs/threads-api-publish-readiness-execution-guide.md`
4. Create `docs/threads-api-publish-readiness-progress-tracker.md`

If some of these files already exist, refine them instead of creating duplicates.
