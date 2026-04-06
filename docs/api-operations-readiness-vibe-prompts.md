# API And Operations Readiness Autonomous Vibe Coding Pack

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in [docs/api-operations-readiness-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/api-operations-readiness-todo.md), inspect the repository, choose the smallest clean implementation shape for each gap, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current CLI-first implementation instead of inventing a new product from scratch,
- they constrain API and operations work so the existing safety model stays intact,
- they require reusing current workflows and repositories before adding new abstractions,
- they preserve the finance-local and all-domain review-first behavior unless a task explicitly expands a surface.

Progress for live implementation should be tracked in:
- [docs/api-operations-readiness-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/api-operations-readiness-progress.md)

## Repository Context
The repository already has:
- a working finance-local review-first pipeline,
- an all-domain extension with source-policy support, provenance, and policy-aware history data,
- CLI workflows for run-local execution, review actions, scheduler jobs, and history views,
- UI-facing data contract notes for run overview, article list, draft review, and failure views,
- FastAPI listed as a project dependency, but no real API application or routers yet.

Important current files and patterns:
- CLI/workflow entrypoints: [app/cli.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/cli.py), [app/workflows/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows)
- Review actions and validation: [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py), [app/services/draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/draft_validation.py)
- History/query helpers: [app/workflows/history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/history_queries.py)
- Storage and schema checks: [app/storage/models.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/models.py), [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py), [app/storage/bootstrap.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/bootstrap.py)
- Current API placeholder: [app/api/__init__.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/__init__.py)
- Existing operator/UI docs: [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md), [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md), [docs/all-domain-news-operator-guide.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-operator-guide.md)
- Existing roadmap: [docs/api-operations-readiness-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/api-operations-readiness-todo.md)

High-signal tests already exist and should be reused instead of inventing a new test structure:
- [tests/test_cli.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_cli.py)
- [tests/test_history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_history_queries.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)
- [tests/test_draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_draft_validation.py)
- [tests/test_storage.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_storage.py)
- [tests/test_article_extractor.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_article_extractor.py)
- [tests/test_enrich_articles_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_enrich_articles_workflow.py)
- [tests/test_operations.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_operations.py)

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path before editing.
- Prefer reusing workflow and repository logic over duplicating it in API handlers.
- Keep each task self-contained and merge-friendly.
- Choose additive changes over broad redesigns.
- Preserve current CLI behavior unless a task explicitly updates a shared abstraction.

### Scope control
- Do not expand API work into authentication, multi-user permissions, or a full frontend unless the task explicitly requires it.
- Do not redesign the domain model when existing workflow/query types can be serialized cleanly.
- Keep migration work modest and practical; the goal is upgrade safety, not a full platform rebuild.

### Safety constraints
- Preserve the current review-first publish gate.
- Do not introduce auto-approve or auto-publish behavior.
- Keep schedule-time validation and source-policy blockers intact.
- Prefer read-only API surfaces first, then action surfaces that reuse existing validation.

### Testing rules
- Add or update targeted tests for every behavior change.
- Run the narrowest relevant test set first.
- If a shared storage or workflow surface changes, run one broader regression slice too.
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
- Use a clear commit message tied to the task outcome, for example:
  - `Add FastAPI app with health and history routes`
  - `Expose review queue actions through API handlers`
  - `Add SQLite schema migration baseline`

### Completion rules
- Only finish after code changes and verification are done.
- Report:
  - what changed,
  - why that shape was chosen,
  - tests run,
  - any remaining follow-up intentionally deferred.

## Progress Tracking Rules
The agent must keep [docs/api-operations-readiness-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/api-operations-readiness-progress.md) updated while implementing this roadmap.

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
  - record test commands and pass/fail status
- At task completion:
  - mark the task `done`
  - summarize the final changed files
  - record the commit SHA and commit message if a commit was created
  - record follow-up items if any remain

### What to track
- current active task
- active branch
- latest commit for the task when available
- overall task status table
- files changed for the active task
- implementation notes
- test execution log
- blockers or follow-up items

### Tracking constraints
- Keep entries short and factual.
- Update the existing progress file instead of creating a new ad hoc log.
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

Follow-up
- ...
```

## Recommended Task Order
1. Task 01: FastAPI application wiring and read-only history
2. Task 02: Article and pending-review read endpoints
3. Task 03: Review action API parity
4. Task 04: SQLite migration baseline
5. Task 05: Config readiness guidance and validation
6. Task 06: Source-specific extraction tuning hooks

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the API and operations readiness roadmap in this repository.

Start by reading:
- docs/api-operations-readiness-todo.md
- docs/api-operations-readiness-vibe-prompts.md
- docs/api-operations-readiness-progress.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/api-operations-readiness-vibe-prompts.md.

Your job:
1. Determine the next unfinished task in the recommended order.
2. Create or switch to a dedicated task branch using the git workflow rules in docs/api-operations-readiness-vibe-prompts.md.
3. Update docs/api-operations-readiness-progress.md to mark that task in progress and note the intended scope and active branch.
4. Implement only that task cleanly and completely.
5. Keep docs/api-operations-readiness-progress.md updated during the work with changed files and key progress notes.
6. Add or update targeted tests.
7. Run relevant tests and record them in docs/api-operations-readiness-progress.md.
8. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
9. Mark the task complete in docs/api-operations-readiness-progress.md when verified, including branch and commit details.
10. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve the current finance-local and all-domain review-first behavior
- keep manual review as the default gate
- avoid broad architecture rewrites
- do not expand into auth, frontend implementation, or speculative platform work unless the task explicitly requires it

If the next task is ambiguous, choose the smallest sensible interpretation that best exposes current capabilities to an API or improves operator safety without changing workflow semantics.
```

## Milestone Prompt
Use this when you want the agent to complete the first backend-ready milestone instead of one isolated unit.

```text
Implement the first backend-ready operator API milestone described in docs/api-operations-readiness-todo.md.

Before editing:
- inspect the repository structure and current implementations
- identify which pieces of the milestone already exist and which are still missing
- create or switch to a dedicated milestone branch
- update docs/api-operations-readiness-progress.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- a real FastAPI application entrypoint
- read-only health/history/article/review endpoints
- review action endpoints that reuse the existing review_queue validation path

Constraints:
- preserve current review and publish safety behavior
- no auth layer
- no frontend implementation
- no scheduler redesign
- prefer additive serialization and route wiring over new business-logic layers
- add focused API tests for each new surface
- keep docs/api-operations-readiness-progress.md updated as work proceeds
- make intentional commits as milestone slices are completed

At the end, report:
- completed milestone scope
- changed files
- tests run
- branch and commit details
- remaining roadmap items not included
```

## Task 01: FastAPI Application Wiring And Read-Only History

### Objective
Add a real FastAPI application and expose safe read-only health and history data as JSON without duplicating current workflow logic.

### Relevant code
- [app/api/__init__.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/__init__.py)
- [app/operations.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/operations.py)
- [app/workflows/history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/history_queries.py)
- [tests/test_operations.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_operations.py)

### Expected result
- the repository has a concrete FastAPI app entrypoint
- `/health`, `/runs`, and `/failures` return stable JSON
- API handlers reuse existing helper/query logic cleanly

### Autonomous prompt
```text
Implement Task 01 from docs/api-operations-readiness-todo.md.

Inspect:
- app/api/__init__.py
- app/operations.py
- app/workflows/history_queries.py

The gap to close is:
- the repository already has health and history logic
- but there is no actual API application exposing those capabilities

Make the smallest clean change that introduces a FastAPI app and read-only routes for:
- /health
- /runs
- /failures

Requirements:
- reuse existing workflow/query helpers
- keep response shapes practical and explicit
- do not duplicate business logic in route handlers
- do not add auth or deployment concerns

Testing requirements:
- add focused API tests for route status and representative JSON fields
- run one broader regression slice if shared query helpers are touched
```

## Task 02: Article And Pending-Review Read Endpoints

### Objective
Expose article/enrichment status and pending-review draft data through API routes aligned with the current UI data contract.

### Relevant code
- [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md)
- [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)

### Expected result
- API routes exist for article status rows and pending drafts
- response fields map cleanly onto current stored data
- future UI work can use API reads instead of CLI parsing

### Autonomous prompt
```text
Implement Task 02 from docs/api-operations-readiness-todo.md.

Inspect the current UI data-contract notes, review_queue listing logic, and relevant repositories first.

Expose API read endpoints for:
- article/enrichment status rows
- pending-review drafts

Requirements:
- prefer repository or workflow reuse over inventing a new query layer unless a tiny helper is clearly justified
- keep field names readable and stable
- align the response shape with the current data contract as closely as practical
- avoid speculative UI-only fields that are not backed by current data

Testing requirements:
- add focused API tests for empty and non-empty responses
- keep any new repository helper changes narrowly covered
```

## Task 03: Review Action API Parity

### Objective
Expose approve, reject, edit, and schedule operations through API handlers while preserving the current review semantics and validation behavior.

### Relevant code
- [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- [app/services/draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/draft_validation.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)
- [tests/test_draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_draft_validation.py)

### Expected result
- review actions can be triggered by API calls
- validation failures remain readable and policy-aware
- API behavior matches existing CLI semantics

### Autonomous prompt
```text
Implement Task 03 from docs/api-operations-readiness-todo.md.

Inspect current review_queue action handlers and validation behavior first.

Expose API endpoints for:
- approve
- reject
- edit
- schedule

Requirements:
- reuse existing review_queue functions and their validation path
- preserve current manual-review and schedule-time semantics
- return clear failure messages for invalid state transitions or policy blockers
- do not redesign the review model

Testing requirements:
- add focused API tests for at least one successful action and one validation failure
- run the existing review_queue tests if any shared validation path changes
```

## Task 04: SQLite Migration Baseline

### Objective
Introduce a practical upgrade path for schema evolution so operators are not forced to recreate local databases whenever the model changes.

### Relevant code
- [app/storage/bootstrap.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/bootstrap.py)
- [app/storage/database.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/database.py)
- [scripts/create_db.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/scripts/create_db.py)
- [tests/test_storage.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_storage.py)

### Expected result
- the repository has an explicit schema-upgrade path
- version detection and upgrade execution are intentional and testable
- current bootstrap/readiness behavior stays clear for operators

### Autonomous prompt
```text
Implement Task 04 from docs/api-operations-readiness-todo.md.

Inspect the current schema bootstrap and validation path first.

The gap to close is:
- schema validation is strict
- but operators still have to recreate the SQLite database for upgrades

Add the smallest practical migration baseline that supports intentional local upgrades.

Requirements:
- keep the design modest and compatible with the current SQLite-first environment
- avoid overengineering a full platform migration framework if a smaller baseline works
- keep operator failure messages explicit
- preserve existing schema checks wherever practical

Testing requirements:
- add focused tests for schema version detection and at least one upgrade path
- run broader storage regression coverage if bootstrap behavior changes substantially
```

## Task 05: Config Readiness Guidance And Validation

### Objective
Make it easier for operators to distinguish sample config from real config and catch placeholder or readiness issues before runtime.

### Relevant code
- [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md)
- [app/operations.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/operations.py)
- [config/examples/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/config/examples)
- [tests/test_operations.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_operations.py)

### Expected result
- readiness feedback is clearer for sample config and placeholder URLs
- common operator setup mistakes fail fast with actionable guidance
- example configs remain usable as samples

### Autonomous prompt
```text
Implement Task 05 from docs/api-operations-readiness-todo.md.

Inspect the current healthcheck/readiness behavior, README setup guidance, and bundled example config shape first.

Improve operator readiness feedback around:
- sample config directories
- placeholder source URLs
- configuration that is valid syntactically but not production-ready

Requirements:
- prefer explicit warnings or readiness failures over silent assumptions
- keep sample configs available for development and testing
- avoid blocking legitimate local test setups unless the readiness signal is clearly justified

Testing requirements:
- add focused readiness or operations tests for the new detection behavior
- keep docs in sync if the healthcheck semantics change
```

## Task 06: Source-Specific Extraction Tuning Hooks

### Objective
Add narrowly scoped extraction escape hatches for hard publisher layouts without replacing the current lightweight extractor architecture.

### Relevant code
- [app/services/article_extractor.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/article_extractor.py)
- [app/workflows/enrich_articles.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/enrich_articles.py)
- [tests/test_article_extractor.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_article_extractor.py)
- [tests/test_enrich_articles_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_enrich_articles_workflow.py)

### Expected result
- the extraction path supports at least one source-specific tuning hook or override shape
- workflow compatibility is preserved
- complex publisher layouts can be handled incrementally

### Autonomous prompt
```text
Implement Task 06 from docs/api-operations-readiness-todo.md.

Inspect the current article extractor and enrich workflow first.

Add a small, additive mechanism for source-specific extraction tuning so hard layouts can be handled without redesigning the extractor.

Requirements:
- prefer opt-in hooks, parser hints, or small override rules over a broad scraping subsystem
- keep the current default extractor behavior intact
- preserve workflow-level failure handling and policy gating
- do not expand into a generalized crawler or browser automation system

Testing requirements:
- add focused extractor coverage for the new tuning mechanism
- run at least one enrichment workflow slice if the integration path changes
```

## Suggested Working Pattern
When using this document operationally:
1. Run the Master Prompt to let the agent pick the next unfinished task.
2. If tighter control is needed, run a single task prompt directly.
3. Keep work scoped to one task per branch or commit when possible.
4. During active implementation, keep [docs/api-operations-readiness-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/api-operations-readiness-progress.md) current.
5. After each completed task, update the roadmap or progress notes.

## Operator Note
If you want the agent to continue through multiple tasks without asking each time, pair the Master Prompt with a simple instruction such as:

```text
Continue task-by-task in roadmap order. After each task, commit only if tests pass and the scope is still clean.
```
