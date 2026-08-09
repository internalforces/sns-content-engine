# Multichannel Manual Publish Readiness Vibe Coding Prompt

## Purpose
This document is the kickoff brief for an autonomous coding agent working in an existing repository.

Use it when you want the agent to absorb the product intent quickly, inspect the real codebase, shape the smallest safe implementation slice, and start coding with minimal back-and-forth.

The prompt below is intentionally opinionated:
- it starts from the current repository instead of inventing a blank-slate rewrite,
- it prefers additive changes over broad redesigns,
- it preserves the manual review gate, current X publish safety behavior, and operator-visible workflow semantics,
- it turns vague product intent into a roadmap, execution guide, progress tracker, and first implementation slice.

## Generated document naming
When instantiating this template, keep the document names explicit so each file is easy to identify at a glance.

- Vibe coding prompt file: `docs/multichannel-manual-publish-readiness-vibe-coding-prompt.md`
- Roadmap file: `docs/multichannel-manual-publish-readiness-roadmap.md`
- Execution guide file: `docs/multichannel-manual-publish-readiness-execution-guide.md`
- Progress tracker file: `docs/multichannel-manual-publish-readiness-progress-tracker.md`
- Avoid ambiguous names like `prompt.md`, `brief.md`, `notes.md`, or `plan.md` when multiple initiatives may coexist.

## Initiative Brief
- Initiative name: `Multichannel Manual Publish Readiness`
- One-sentence outcome: `Turn existing non-X draft generation into an operator-trackable manual publish workflow while restoring a clean repository baseline first.`
- Why this matters now:
  - The repository already generates LinkedIn and Threads drafts, but only X has a supported publish lifecycle.
  - The current test baseline is not green, so the next stage should start by removing the known readiness regressions before new behavior lands.
- Primary user, operator, or workflow owner:
  - Operators using the CLI, API, and browser console to review and publish content
  - Future maintainers extending publish workflow behavior without weakening safety defaults
- Core workflow to improve:
  - approve reviewed draft
  - hand off non-X content for manual upload
  - record publish outcome and show it in operator surfaces
- Explicit non-goals:
  - direct LinkedIn or Threads API integrations in this initiative
  - auth, multi-user permissions, or a SPA frontend redesign
  - auto-approve or auto-publish behavior

## Repository Context
The repository already has:
- config-driven multichannel draft generation for `x`, `linkedin`, and `threads`
- review queue, publish job, and publish log persistence
- FastAPI operator routes and a server-rendered browser console
- a live X publisher plus manual upload guidance for approved non-X drafts

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/api/app.py`
- Existing workflows or services: `app/workflows/review_queue.py`, `app/scheduler/jobs.py`
- Data or schema surfaces: `app/storage/models.py`, `app/storage/repositories.py`
- Current placeholder, gap, or friction point: `app/connectors/publishers/resolver.py`, `app/api/console.py`
- Existing tests to reuse first: `tests/test_operations.py`, `tests/test_api.py`
- Existing docs to align with: `docs/operator-console-guide.md`, `docs/operator-control-plane-api.md`

## Product Intent And Quality Bar
The desired implementation should:
- restore a clean readiness baseline before expanding behavior
- reuse the existing publish job and log model where practical
- give operators an explicit, trackable non-X handoff lifecycle
- keep X live publish behavior and dry-run-safe defaults intact

The agent should preserve:
- the manual review gate
- current validation and policy blockers
- the current server-rendered console interaction model unless a task explicitly says otherwise

The agent should avoid:
- a broad publish subsystem redesign
- a second parallel persistence model for manual publishes unless clearly required
- speculative platform integrations that the roadmap does not call for
- unsafe shortcuts that weaken readiness checks or publishing safety

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands:
  - `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest -q`
- Required local services:
  - `none`
  - `local SQLite only`
- Required env files, secrets, or fixtures:
  - `.env is optional unless live-provider or live-X behavior is under test`
  - `tests/fixtures and temporary SQLite databases already cover most workflow paths`
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
- `docs/multichannel-manual-publish-readiness-roadmap.md` exists and reflects the current implementation shape
- `docs/multichannel-manual-publish-readiness-execution-guide.md` exists and contains repo-specific execution rules
- `docs/multichannel-manual-publish-readiness-progress-tracker.md` exists and is updated with current task status
- the first implementation slice is complete, or the exact blocker is documented clearly
- targeted tests have run, or the reason testing could not run is recorded explicitly
- the final report explains what changed, why that shape was chosen, and what remains deferred

## Prompt Template
Copy, adapt, and send the block below to the agent when starting or resuming work.

```text
You are working in an existing repository, not a blank project.

Read this document first:
- docs/multichannel-manual-publish-readiness-vibe-coding-prompt.md

Then inspect and use these companion docs when they exist:
- docs/multichannel-manual-publish-readiness-roadmap.md
- docs/multichannel-manual-publish-readiness-execution-guide.md
- docs/multichannel-manual-publish-readiness-progress-tracker.md

Your job is to turn the initiative into the smallest clean implementation slice that can be shipped safely.

Initiative brief
- Name: Multichannel Manual Publish Readiness
- Outcome: Turn existing LinkedIn and Threads draft generation into an operator-trackable manual publish workflow while restoring a clean repository baseline first.
- Why now:
  - Non-X drafts already exist, but only X has a supported publish lifecycle.
  - The repository currently has 2 failing readiness-related tests, so a green baseline should come first.
- Core workflow to improve:
  - approve reviewed draft
  - hand off non-X content for manual upload
  - record publish outcome and expose it in operator surfaces
- Explicit non-goals:
  - direct LinkedIn or Threads API integrations
  - auth or multi-user permission work

Repository context
- Existing capabilities:
  - multichannel draft generation already exists
  - review queue, publish jobs, and publish logs already exist
  - API and console operator surfaces already exist
- Important files and patterns:
  - app/cli.py
  - app/workflows/review_queue.py
  - app/storage/models.py
  - app/connectors/publishers/resolver.py
  - tests/test_api.py

Quality bar
- Preserve:
  - the manual review gate
  - current X live-publish and dry-run-safe scheduler behavior
- Prefer:
  - reuse of publish jobs and publish logs for manual handoff tracking
  - thin API or console surfaces that call shared workflow helpers
- Avoid:
  - broad publish subsystem redesign
  - unsafe shortcuts that weaken readiness validation or publishing safety

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
  - ./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q
  - ./.venv/bin/pytest tests/test_api.py tests/test_console.py -q
- Broader regression commands:
  - ./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q
  - ./.venv/bin/pytest -q
- Required services:
  - none
  - local SQLite only
- Required env or fixtures:
  - .env optional unless live-provider or live-X behavior is under test
  - tests/fixtures and temp SQLite databases already exist
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

1. Create `docs/multichannel-manual-publish-readiness-vibe-coding-prompt.md`
2. Create `docs/multichannel-manual-publish-readiness-roadmap.md`
3. Create `docs/multichannel-manual-publish-readiness-execution-guide.md`
4. Create `docs/multichannel-manual-publish-readiness-progress-tracker.md`

If some of these files already exist, refine them instead of creating duplicates.
