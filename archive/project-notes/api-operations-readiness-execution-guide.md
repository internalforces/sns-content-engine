# API And Operations Readiness Autonomous Execution Guide

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in `docs/api-operations-readiness-roadmap.md`, inspect the repository, choose the smallest clean implementation shape for each gap, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current CLI-first implementation instead of inventing a new product from scratch
- they constrain API and operations work so the existing safety model stays intact
- they require reusing current workflows and repositories before adding new abstractions
- they preserve finance-local and all-domain review-first behavior unless a task explicitly expands a surface

Progress for live implementation should be tracked in:
- `docs/api-operations-readiness-progress-tracker.md`

## Generated document naming
When instantiating this template, use filenames that make each document's identity obvious at a glance.

- Roadmap file: `docs/api-operations-readiness-roadmap.md`
- Execution guide file: `docs/api-operations-readiness-execution-guide.md`
- Progress tracker file: `docs/api-operations-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/api-operations-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `prompt.md`, `guide.md`, or `progress.md` when multiple initiatives may coexist.

## Repository Context
This guide was shaped for the repository state that already had:
- a working finance-local review-first pipeline
- an all-domain extension with source-policy support, provenance, and policy-aware history data
- CLI workflows for run-local execution, review actions, scheduler jobs, and history views
- UI-facing data contract notes for run overview, article list, draft review, and failure views
- FastAPI listed as a project dependency, but no real API application or routers yet at roadmap start

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/operations.py`
- Core workflows and services: `app/workflows/history_queries.py`, `app/workflows/review_queue.py`, `app/workflows/enrich_articles.py`
- Storage and schema logic: `app/storage/bootstrap.py`, `app/storage/repositories.py`
- Current placeholder or integration gap at roadmap start: `app/api/__init__.py`
- Existing operator or UI docs: `README.md`, `docs/finance-local-ui-data-contract.md`, `docs/all-domain-news-operator-guide.md`
- Existing roadmap: `docs/api-operations-readiness-roadmap.md`

High-signal tests already exist and should be reused instead of inventing a new test structure:
- `tests/test_cli.py`
- `tests/test_history_queries.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_draft_validation.py`
- `tests/test_storage.py`
- `tests/test_operations.py`
- `tests/test_article_extractor.py`
- `tests/test_enrich_articles_workflow.py`

## Execution Environment
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands by area:
  - `PYTHONPATH=$PWD pytest tests/test_api.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_review_queue_workflow.py`
  - `PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py`
  - `PYTHONPATH=$PWD pytest tests/test_article_extractor.py tests/test_enrich_articles_workflow.py tests/test_config.py`
- Broader regression commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_cli.py tests/test_review_queue_workflow.py`
  - `PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py tests/test_enrich_articles_workflow.py`
- Required services:
  - `none for most read-only API, docs, and migration work`
  - `a local SQLite file when testing against non-fixture data`
- Required env files, secrets, or fixtures:
  - `config/ or another operator-approved config directory`
  - `temporary SQLite fixtures or sqlite:///data/sns_content_engine.db`
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path before editing.
- Read `docs/api-operations-readiness-progress-tracker.md` before choosing the next task.
- Prefer reusing workflow and repository logic over duplicating it in API handlers, migration wrappers, or extraction adapters.
- Keep each task self-contained and merge-friendly.
- Choose additive changes over broad redesigns.
- Preserve current CLI and workflow behavior unless a task explicitly updates a shared abstraction.

### Resume rules
- If `docs/api-operations-readiness-progress-tracker.md` shows a current task with status `in_progress` or `blocked`, resume or resolve that task before selecting a new one unless the roadmap was intentionally reprioritized.
- Only choose the next unfinished task when there is no active task that still owns the current branch or implementation state.
- If the active task was blocked by a fixable local issue and the scope is still the same, keep the same task ID and continue instead of creating a new task.

### Roadmap shaping rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- When creating or refining the roadmap, choose only as many milestones and tasks as are needed to make forward progress safely.
- The sizing rule is: split work so it can be completed without breaking the current structure, safety model, workflow semantics, or operator experience.
- Prefer the smallest additive slices that fit the existing architecture.
- Split a task or milestone when it would otherwise mix API routing, schema migration, config-readiness, and extraction concerns too broadly or make verification unclear.
- Merge adjacent tiny items when they share the same code path, tests, and commit scope.
- If the roadmap shape changes during implementation, update `docs/api-operations-readiness-roadmap.md` and `docs/api-operations-readiness-progress-tracker.md` before continuing.

### Scope control
- Do not expand API work into authentication, multi-user permissions, or a full frontend unless the task explicitly requires it.
- Do not redesign the domain model when existing workflow and query types can be serialized cleanly.
- Keep migration work modest and practical; the goal is upgrade safety, not a full platform rebuild.

### Dirty worktree rules
- Inspect the current branch and working tree before making substantive edits when repository tooling is available.
- Never overwrite, revert, or stage unrelated changes.
- If user or pre-existing changes conflict directly with the active task in the same files, stop, record the conflict in `docs/api-operations-readiness-progress-tracker.md`, and treat the task as blocked until the conflict is resolved.
- Keep branch, staging, and commit scope limited to the active task.

### Safety constraints
- Preserve the current review-first publish gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Keep schedule-time validation, provenance, attribution, and source-policy blockers intact.
- Prefer read-only surfaces first, then action surfaces that reuse existing validation.

### Blocked-task rules
- Try the smallest reasonable local investigation first when a blocker appears.
- If progress is blocked by missing configuration, unavailable services, missing credentials, conflicting local edits, or unrelated failing tests, record the exact blocker and stop reason in `docs/api-operations-readiness-progress-tracker.md`.
- Mark the task `blocked` when work cannot continue safely inside the intended scope.
- Do not mark blocked work as `done`.
- Do not create a normal task-completion commit for blocked work; only create a checkpoint commit if the partial state is independently safe, intentionally scoped, and clearly documented.

### Testing rules
- Add or update targeted tests for every behavior change.
- Use task-specific verification commands from `docs/api-operations-readiness-roadmap.md` when they are provided.
- Run the narrowest relevant test set first.
- If a shared storage, workflow, or healthcheck surface changes, run one broader regression slice too.
- If no explicit test command exists, infer the narrowest relevant command from the repository and record that reasoning in `docs/api-operations-readiness-progress-tracker.md`.
- Distinguish newly introduced failures from pre-existing failures or environment failures.
- If testing cannot run, record the exact command and reason as `not_run` or `pre_existing_failure`.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-fastapi-readonly-history`
  - `codex/task-04-sqlite-migration-baseline`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Do not push branches or open pull requests unless explicitly requested.
- Use a clear commit message tied to the task outcome, for example:
  - `Add FastAPI app with health and history routes`
  - `Expose review queue actions through API handlers`
  - `Add SQLite schema migration baseline`

### Completion rules
- Only finish after code changes, verification, and progress updates are done.
- Do not mark a task complete until `docs/api-operations-readiness-progress-tracker.md` includes the final status, changed files, test log, and commit details or the reason a commit was not created.
- If the work cannot be finished safely, leave the task as `blocked` with a clear next step instead of forcing completion.
- Report:
  - what changed
  - why that shape was chosen
  - tests run
  - branch and commit details
  - any remaining follow-up intentionally deferred

## Progress Tracking Rules
The agent must keep `docs/api-operations-readiness-progress-tracker.md` updated while implementing this roadmap.

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
List the actual tasks defined in `docs/api-operations-readiness-roadmap.md` in dependency order. Add or remove lines as needed; the task count is not fixed.

1. Task 01: FastAPI application wiring and read-only history
2. Task 02: Article and pending-review read endpoints
3. Task 03: Review action API parity
4. Task 04: SQLite migration baseline
5. Task 05: Config readiness guidance and validation
6. Task 06: Source-specific extraction tuning hooks
