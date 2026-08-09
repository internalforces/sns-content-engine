# API And Operations Readiness Vibe Coding Prompt

## Purpose
This document is the kickoff brief for an autonomous coding agent working in an existing repository.

Use it when you want the agent to absorb the product intent quickly, inspect the real codebase, shape the smallest safe implementation slice, and start coding with minimal back-and-forth.

The prompt below is intentionally opinionated:
- it starts from the current CLI-first implementation instead of inventing a blank-slate rewrite
- it prefers additive changes over broad redesigns
- it preserves finance-local and all-domain review-first behavior, plus the existing publish-safety model
- it turns vague product intent into a roadmap, execution guide, progress tracker, and first implementation slice

## Generated document naming
When instantiating this template, keep the document names explicit so each file is easy to identify at a glance.

- Vibe coding prompt file: `docs/api-operations-readiness-vibe-coding-prompt.md`
- Roadmap file: `docs/api-operations-readiness-roadmap.md`
- Execution guide file: `docs/api-operations-readiness-execution-guide.md`
- Progress tracker file: `docs/api-operations-readiness-progress-tracker.md`
- Avoid ambiguous names like `prompt.md`, `brief.md`, `notes.md`, or `plan.md` when multiple initiatives may coexist.

## Initiative Brief
- Initiative name: `API And Operations Readiness`
- One-sentence outcome: `Turn the CLI-first pipeline into a backend-ready operator surface with stable API routes, safe review-action parity, modest SQLite upgrades, and better operator-readiness checks.`
- Why this matters now:
  - future UI and automation work need stable HTTP surfaces instead of shell-only access
  - operators need safer upgrade and config-readiness behavior before expanding deployment scope
- Primary user, operator, or workflow owner:
  - local or single-server operators running review-first workflows
  - future UI or automation layers that need a stable backend contract
- Core workflow to improve:
  - inspect health and history without parsing CLI output
  - review or schedule drafts through validated backend surfaces
  - upgrade or verify local environments before real runs
- Explicit non-goals:
  - authentication or multi-user permissions
  - a full frontend implementation
  - a broad scraper-platform redesign or unsafe auto-publish shortcuts

## Repository Context
The repository already has:
- a working finance-local review-first pipeline
- an all-domain extension with source-policy support, provenance, and policy-aware history data
- CLI workflows for run-local execution, review actions, scheduler jobs, and history views
- operational healthcheck support, strict schema validation, and SQLite-backed persistence

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/operations.py`
- Existing workflows or services: `app/workflows/history_queries.py`, `app/workflows/review_queue.py`
- Data or schema surfaces: `app/storage/bootstrap.py`, `app/storage/models.py`
- Current placeholder, gap, or friction point at roadmap start: `app/api/__init__.py`
- Existing tests to reuse first: `tests/test_cli.py`, `tests/test_history_queries.py`, `tests/test_review_queue_workflow.py`, `tests/test_storage.py`
- Existing docs to align with: `README.md`, `docs/finance-local-ui-data-contract.md`, `docs/all-domain-news-operator-guide.md`

## Product Intent And Quality Bar
The desired implementation should:
- expose stable JSON surfaces for health, history, article status, and review work
- reuse existing workflows and repositories instead of adding a parallel backend layer
- preserve manual review, attribution, provenance, and publish-safety semantics
- make schema upgrades and config-readiness failures explicit before real runs

The agent should preserve:
- finance-local and all-domain review-first workflow behavior
- schedule-time validation and source-policy blockers
- the CLI path as a reliable operator fallback while backend surfaces are added

The agent should avoid:
- broad architecture rewrites
- a new migration framework or alternate storage platform
- new auth or frontend surface area
- unsafe auto-approve or auto-publish shortcuts

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_review_queue_workflow.py`
  - `PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py`
  - `PYTHONPATH=$PWD pytest tests/test_article_extractor.py tests/test_enrich_articles_workflow.py tests/test_config.py`
- Broader regression commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_cli.py tests/test_review_queue_workflow.py`
  - `PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py tests/test_enrich_articles_workflow.py`
- Required local services:
  - `none for most read-only API and docs work`
  - `a local SQLite file when testing against non-fixture data`
- Required env files, secrets, or fixtures:
  - `config/ or another operator-approved config directory`
  - `temporary SQLite fixtures or sqlite:///data/sns_content_engine.db`
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Expected Agent Behavior
- Inspect the current code path before editing.
- Reuse existing repository patterns, workflows, tests, and schema shapes before introducing new abstractions.
- Prefer the smallest clean implementation slice that moves the initiative forward safely.
- Create or refine the roadmap, execution guide, and progress tracker before large implementation work if they do not already exist.
- Update the roadmap and progress tracker when the implementation shape changes materially.
- Keep branch, commit, and staging scope limited to the active task.
- Record blockers clearly instead of forcing completion through unsafe shortcuts.

## First-Pass Definition Of Done
For the first meaningful iteration, aim to finish when:
- `docs/api-operations-readiness-roadmap.md` exists and reflects the current implementation shape
- `docs/api-operations-readiness-execution-guide.md` exists and contains repo-specific execution rules
- `docs/api-operations-readiness-progress-tracker.md` exists and is updated with current task status
- the first implementation slice is complete, or the exact blocker is documented clearly
- targeted tests have run, or the reason testing could not run is recorded explicitly
- the final report explains what changed, why that shape was chosen, and what remains deferred

## Prompt Template
Copy, adapt, and send the block below to the agent when starting or resuming work.

```text
You are working in an existing repository, not a blank project.

Read this document first:
- docs/api-operations-readiness-vibe-coding-prompt.md

Then inspect and use these companion docs when they exist:
- docs/api-operations-readiness-roadmap.md
- docs/api-operations-readiness-execution-guide.md
- docs/api-operations-readiness-progress-tracker.md

Your job is to turn the initiative into the smallest clean implementation slice that can be shipped safely.

Initiative brief
- Name: API And Operations Readiness
- Outcome: Turn the CLI-first pipeline into a backend-ready operator surface with stable API routes, safe review-action parity, modest SQLite upgrades, and better operator-readiness checks.
- Why now:
  - future UI and automation work need stable HTTP surfaces instead of shell-only access
  - operators need safer upgrade and config-readiness behavior before expanding deployment scope
- Core workflow to improve:
  - inspect health and history without parsing CLI output
  - review or schedule drafts through validated backend surfaces
  - upgrade or verify local environments before real runs
- Explicit non-goals:
  - authentication or multi-user permissions
  - a full frontend implementation

Repository context
- Existing capabilities:
  - working finance-local and all-domain review-first workflow layers
  - history, review, and healthcheck helpers that can back a real API
  - strict SQLite schema validation and operator docs that already describe the current workflow
- Important files and patterns:
  - app/cli.py
  - app/operations.py
  - app/workflows/history_queries.py
  - app/workflows/review_queue.py
  - app/storage/bootstrap.py
  - app/api/__init__.py
  - tests/test_cli.py

Quality bar
- Preserve:
  - manual review as the default publish gate
  - attribution, provenance, and source-policy blockers
- Prefer:
  - thin API handlers and shared helper reuse
  - additive SQLite upgrade and config-readiness work
- Avoid:
  - broad architecture rewrites
  - unsafe auto-approve or auto-publish shortcuts

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
  - PYTHONPATH=$PWD pytest tests/test_api.py
  - PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_review_queue_workflow.py
  - PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py
  - PYTHONPATH=$PWD pytest tests/test_article_extractor.py tests/test_enrich_articles_workflow.py tests/test_config.py
- Broader regression commands:
  - PYTHONPATH=$PWD pytest tests/test_api.py tests/test_cli.py tests/test_review_queue_workflow.py
  - PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py tests/test_enrich_articles_workflow.py
- Required services:
  - none for most read-only API and docs work
  - a local SQLite file when testing against non-fixture data
- Required env or fixtures:
  - config/ or another operator-approved config directory
  - temporary SQLite fixtures or sqlite:///data/sns_content_engine.db
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

1. Create `docs/api-operations-readiness-vibe-coding-prompt.md`
2. Create `docs/api-operations-readiness-roadmap.md`
3. Create `docs/api-operations-readiness-execution-guide.md`
4. Create `docs/api-operations-readiness-progress-tracker.md`

If some of these files already exist, refine them instead of creating duplicates.
