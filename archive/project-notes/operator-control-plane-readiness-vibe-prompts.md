# Operator Control Plane Readiness Autonomous Vibe Coding Pack

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in [docs/operator-control-plane-readiness-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-readiness-todo.md), inspect the repository, choose the smallest clean implementation shape for each gap, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current backend-ready operator API instead of inventing a new platform from scratch,
- they constrain control-plane work so the current review-first and dry-run safety model stays intact,
- they require reusing current workflows, repositories, and scheduler helpers before adding new abstractions,
- they preserve manual review and explicit publish validation unless a task explicitly expands a surface.

Progress for live implementation should be tracked in:
- [docs/operator-control-plane-readiness-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-readiness-progress.md)

## Repository Context
The repository already has:
- a working FastAPI application with operator health, history, article, and pending-review routes,
- review action API routes that reuse the existing review workflow and validation path,
- scheduler workflows for discover, backfill, and publish-due with dry-run defaults,
- persisted review audit rows, publish jobs, and publish logs that are currently more visible through code and CLI than through the API.

Important current files and patterns:
- API entrypoint and serializers: [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- Review workflow and existing action errors: [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- Scheduler helpers: [app/scheduler/jobs.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/jobs.py), [app/scheduler/runtime.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/runtime.py)
- Storage models and repositories: [app/storage/models.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/models.py), [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- Existing UI/API notes: [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md)
- Existing roadmap: [docs/operator-control-plane-readiness-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-readiness-todo.md)

High-signal tests already exist and should be reused instead of inventing a new test structure:
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)
- [tests/test_scheduler.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_scheduler.py)
- [tests/test_storage.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_storage.py)
- [tests/test_cli.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_cli.py)

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path before editing.
- Prefer reusing workflow, repository, and scheduler helpers over duplicating behavior in API handlers.
- Keep each task self-contained and merge-friendly.
- Choose additive serialization and query helpers over broad redesigns.
- Preserve current CLI and scheduler behavior unless a task explicitly updates a shared abstraction.

### Scope control
- Do not expand this work into authentication, multi-user permissions, or frontend implementation unless a task explicitly requires it.
- Do not redesign scheduler planning, draft validation, or publish execution when existing helpers can be wrapped cleanly.
- Keep new query helpers practical and repository-backed; avoid building a parallel read model unless a very small adapter is clearly justified.

### Safety constraints
- Preserve the current manual-review gate.
- Do not introduce auto-approve or auto-publish behavior.
- Keep `publish-due` dry-run as the default API behavior.
- Preserve current validation, idempotency, attribution, and source-policy blockers when exposing new action surfaces.

### Testing rules
- Add or update targeted tests for every behavior change.
- Run the narrowest relevant test set first.
- If a shared storage, review, or scheduler surface changes, run one broader regression slice too.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-review-draft-detail-endpoint`
  - `codex/task-05-scheduler-action-api-wrappers`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Use a clear commit message tied to the task outcome, for example:
  - `Add review draft detail API endpoint`
  - `Expose publish job logs through API`
  - `Add scheduler action API wrappers`

### Completion rules
- Only finish after code changes and verification are done.
- Report:
  - what changed,
  - why that shape was chosen,
  - tests run,
  - any remaining follow-up intentionally deferred.

## Progress Tracking Rules
The agent must keep [docs/operator-control-plane-readiness-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-readiness-progress.md) updated while implementing this roadmap.

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
1. Task 01: Review-draft detail endpoint
2. Task 02: Review audit and sibling-variant visibility
3. Task 03: Publish-job list endpoint
4. Task 04: Publish-job detail and log timeline
5. Task 05: Scheduler action API wrappers
6. Task 06: Control-plane API docs and regression coverage

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the operator control plane readiness roadmap in this repository.

Start by reading:
- docs/operator-control-plane-readiness-todo.md
- docs/operator-control-plane-readiness-vibe-prompts.md
- docs/operator-control-plane-readiness-progress.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/operator-control-plane-readiness-vibe-prompts.md.

Your job:
1. Determine the next unfinished task in the recommended order.
2. Create or switch to a dedicated task branch using the git workflow rules in docs/operator-control-plane-readiness-vibe-prompts.md.
3. Update docs/operator-control-plane-readiness-progress.md to mark that task in progress and note the intended scope and active branch.
4. Implement only that task cleanly and completely.
5. Keep docs/operator-control-plane-readiness-progress.md updated during the work with changed files and key progress notes.
6. Add or update targeted tests.
7. Run relevant tests and record them in docs/operator-control-plane-readiness-progress.md.
8. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
9. Mark the task complete in docs/operator-control-plane-readiness-progress.md when verified, including branch and commit details.
10. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve manual review as the default gate
- keep dry-run as the default publish execution mode
- avoid broad architecture rewrites
- do not expand into auth, frontend implementation, or speculative platform work unless the task explicitly requires it

If the next task is ambiguous, choose the smallest sensible interpretation that best exposes already-persisted operator data or wraps existing scheduler behavior without weakening current safety defaults.
```

## Milestone Prompt
Use this when you want the agent to complete the first control-plane milestone instead of one isolated unit.

```text
Implement the first operator control plane basics milestone described in docs/operator-control-plane-readiness-todo.md.

Before editing:
- inspect the repository structure and current implementations
- identify which pieces of the milestone already exist and which are still missing
- create or switch to a dedicated milestone branch
- update docs/operator-control-plane-readiness-progress.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- a single-draft review detail API
- review audit and sibling-variant visibility
- publish-job list and detail reads
- scheduler discover/backfill/dry-run publish action endpoints

Constraints:
- preserve manual review and publish validation behavior
- keep publish-due dry-run by default
- no auth layer
- no frontend implementation
- no broad scheduler redesign
- prefer additive serialization and route wiring over new business-logic layers
- add focused API and scheduler-adjacent tests for each new surface
- keep docs/operator-control-plane-readiness-progress.md updated as work proceeds
- make intentional commits as milestone slices are completed

At the end, report:
- completed milestone scope
- changed files
- tests run
- branch and commit details
- remaining roadmap items not included
```

## Task 01: Review-Draft Detail Endpoint

### Objective
Expose one draft variant with the source, brief, enrichment, and review-state context needed for an operator detail screen.

### Relevant code
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)

### Expected result
- an API route exists for one review draft detail payload
- the payload includes current draft text, review state, provenance, and brief context
- handlers stay thin and reuse existing persistence/workflow logic

### Autonomous prompt
```text
Implement Task 01 from docs/operator-control-plane-readiness-todo.md.

Inspect:
- app/api/app.py
- app/workflows/review_queue.py
- app/storage/repositories.py

The gap to close is:
- pending-review listing exists
- but there is no single-draft detail API for a real review screen

Make the smallest clean change that exposes one review-draft detail route.

Requirements:
- reuse existing stored brief, source, and enrichment data
- keep response fields explicit and operator-friendly
- return a clear not-found API error for missing drafts
- do not add auth, caching, or frontend concerns

Testing requirements:
- add focused API tests for populated and missing-draft responses
- run a broader regression slice if shared review helpers are touched
```

## Task 02: Review Audit And Sibling-Variant Visibility

### Objective
Expose review-action history and related variants so an operator can understand how a draft changed and compare alternatives.

### Relevant code
- [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)

### Expected result
- review-action history is visible through the API
- sibling variants for the same brief/channel are available for comparison
- ordering and empty-state behavior are stable

### Autonomous prompt
```text
Implement Task 02 from docs/operator-control-plane-readiness-todo.md.

Inspect the current review queue workflow, review action repository, and draft-variant repository first.

Expose API data for:
- review-action history for one draft
- sibling variants for the same brief/channel

Requirements:
- prefer repository-backed reads over reconstructing history from logs
- keep action ordering chronological and predictable
- avoid changing review semantics or state transitions
- make the response shape practical for a future operator UI

Testing requirements:
- add focused API tests for empty and populated history
- add or reuse review-workflow coverage if helper behavior changes
```

## Task 03: Publish-Job List Endpoint

### Objective
Expose queued, in-flight, completed, and failed publish jobs through the API with modest operator-friendly filters.

### Relevant code
- [app/scheduler/jobs.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/jobs.py)
- [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- [app/storage/models.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/models.py)
- [tests/test_scheduler.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_scheduler.py)

### Expected result
- an API route exists for publish-job listing
- modest filters work for state, account, channel, and limit
- response rows reflect persisted job and linked draft metadata cleanly

### Autonomous prompt
```text
Implement Task 03 from docs/operator-control-plane-readiness-todo.md.

Inspect the current publish-job storage model, scheduler job helpers, and API patterns first.

Expose an API read endpoint for publish jobs.

Requirements:
- support only small practical filters that map cleanly to current data
- keep the first version additive and storage-backed
- include enough linked metadata that operators can identify each job without opening the database
- do not introduce speculative pagination or search systems unless the current code clearly needs a tiny helper

Testing requirements:
- add focused API tests for mixed job states and empty states
- run a broader scheduler or storage regression slice if shared query helpers are added
```

## Task 04: Publish-Job Detail And Log Timeline

### Objective
Expose one publish job with its execution timeline, linked draft context, and publish-log history.

### Relevant code
- [app/scheduler/jobs.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/jobs.py)
- [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- [tests/test_scheduler.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_scheduler.py)
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)

### Expected result
- an API route exists for one publish-job detail payload
- publish-log events are visible in order
- success and failure context are readable without CLI logs

### Autonomous prompt
```text
Implement Task 04 from docs/operator-control-plane-readiness-todo.md.

Inspect the existing publish job and publish log repositories first.

Expose an API detail view for one publish job including:
- job state and timestamps
- external post id and last error when present
- linked draft/source context
- publish-log timeline

Requirements:
- reuse current publish-log persistence instead of adding a new event model
- keep the route read-only
- return a clear API error for missing jobs
- avoid changing publish execution behavior

Testing requirements:
- add focused API tests for successful, failed, and no-log job detail cases
- run a broader scheduler regression slice if shared publish helpers are touched
```

## Task 05: Scheduler Action API Wrappers

### Objective
Expose thin API wrappers for discover, backfill, and publish-due while preserving the current dry-run and validation defaults.

### Relevant code
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [app/scheduler/jobs.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/jobs.py)
- [app/operations.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/operations.py)
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)

### Expected result
- scheduler discover, backfill, and publish-due can be triggered through the API
- publish-due stays dry-run by default
- handlers remain thin wrappers around existing scheduler helpers

### Autonomous prompt
```text
Implement Task 05 from docs/operator-control-plane-readiness-todo.md.

Inspect the current scheduler job helpers and API route patterns first.

Expose operator-safe action endpoints for:
- discover
- backfill
- publish-due

Requirements:
- reuse the current scheduler helper functions directly or through tiny adapters
- keep publish-due dry-run by default
- if any live flag is exposed, require explicit opt-in and preserve current validation behavior
- do not redesign scheduler runtime or background execution

Testing requirements:
- add focused API tests for action result payloads
- verify the default publish execution path stays dry-run
- run one broader scheduler regression slice if shared scheduler code changes
```

## Task 06: Control-Plane API Docs And Regression Coverage

### Objective
Document the new operator API contract clearly and ensure the new surfaces are protected by focused regression tests.

### Relevant code
- [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md)
- [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md)
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)
- [docs/operator-control-plane-readiness-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-readiness-progress.md)

### Expected result
- operator docs describe the new API surfaces clearly
- tests protect the most important detail and action routes
- docs keep the safety model explicit

### Autonomous prompt
```text
Implement Task 06 from docs/operator-control-plane-readiness-todo.md.

Inspect the current README, UI data-contract notes, and API tests first.

Close the remaining gap by documenting the new control-plane API surfaces and tightening regression coverage.

Requirements:
- keep docs concise and operator-facing
- explain which routes are read-only and which trigger scheduler work
- make it explicit that manual review and dry-run publish defaults remain in place
- avoid turning docs into a full deployment guide unless the repository already has that structure

Testing requirements:
- add or update focused API tests where the contract is still under-specified
- if the task is docs-only by the time you reach it, say so explicitly and record any tests you did or did not run
```
