# Operator Console Readiness Autonomous Vibe Coding Pack

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in [docs/operator-console-readiness-roadmap.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-console-readiness-roadmap.md), inspect the repository, choose the smallest clean implementation shape for each gap, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current control-plane-ready FastAPI backend instead of inventing a separate product stack from scratch,
- they constrain console work so the current manual-review and dry-run safety model stays intact,
- they require reusing current workflows, repositories, query helpers, and scheduler wrappers before adding new abstractions,
- they preserve manual review and explicit live-publish opt-in unless a task explicitly expands a surface.

Progress for live implementation should be tracked in:
- [docs/operator-console-readiness-progress-tracker.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-console-readiness-progress-tracker.md)

## Repository Context
The repository already has:
- a working FastAPI application with operator health, history, article, review, publish-job, and scheduler API routes,
- workflow and repository-backed read helpers for runs, failures, article status, review detail, publish-job visibility, and scheduler execution,
- explicit operator-facing docs for API and UI-data expectations,
- an existing `jinja2` dependency that makes a server-rendered console feasible without adding a separate Node toolchain by default.

Important current files and patterns:
- API entrypoint and serializers: [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- Run and failure query helpers: [app/workflows/history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/history_queries.py)
- Review workflow and validation path: [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py), [app/services/draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/draft_validation.py)
- Scheduler helpers: [app/scheduler/jobs.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/jobs.py), [app/scheduler/runtime.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/runtime.py)
- Storage models and repositories: [app/storage/models.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/models.py), [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- Existing operator and UI notes: [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md), [docs/operator-control-plane-api.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-api.md)
- Existing roadmap and execution rules: [docs/operator-console-readiness-roadmap.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-console-readiness-roadmap.md), [docs/operator-console-readiness-execution-guide.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-console-readiness-execution-guide.md)

High-signal tests already exist and should be reused instead of inventing a new test structure:
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)
- [tests/test_history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_history_queries.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)
- [tests/test_scheduler.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_scheduler.py)

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path before editing.
- Read [docs/operator-console-readiness-progress-tracker.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-console-readiness-progress-tracker.md) before choosing the next task.
- Prefer reusing workflow, repository, and existing API-adjacent helpers over duplicating logic in page handlers.
- Keep each task self-contained and merge-friendly.
- Choose additive template rendering and page wiring over broad redesigns.
- Preserve current CLI and API behavior unless a task explicitly updates a shared abstraction.

### Scope control
- Do not expand this work into authentication, multi-user permissions, or a separate SPA unless a task explicitly requires it.
- Do not redesign the domain model when existing query and workflow types can be adapted cleanly for templates.
- Do not introduce a Node build chain by default when the existing FastAPI and Jinja stack can handle the intended scope.
- Keep first-version page behavior practical and operator-focused; avoid speculative polish that is not backed by current data.

### Safety constraints
- Preserve the current manual-review gate.
- Do not introduce auto-approve or auto-publish behavior.
- Keep `publish-due` dry-run as the default browser path.
- Preserve current validation, attribution, provenance, and source-policy blockers when exposing browser actions.
- If live publish is exposed at all, require an explicit opt-in path that is clearly visible in the UI.

### Testing rules
- Add or update targeted tests for every behavior change.
- Run the narrowest relevant test set first.
- If a shared app, review, scheduler, or storage surface changes, run one broader regression slice too.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.
- Prefer adding a dedicated browser-facing test file such as `tests/test_console.py` once page routes exist, instead of overloading unrelated API-only tests.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-console-shell`
  - `codex/task-05-review-action-console`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Use a clear commit message tied to the task outcome, for example:
  - `Add operator console shell`
  - `Add browser run and review queue pages`
  - `Expose scheduler controls in operator console`

### Completion rules
- Only finish after code changes and verification are done.
- Report:
  - what changed,
  - why that shape was chosen,
  - tests run,
  - branch and commit details,
  - any remaining follow-up intentionally deferred.

## Progress Tracking Rules
The agent must keep [docs/operator-console-readiness-progress-tracker.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-console-readiness-progress-tracker.md) updated while implementing this roadmap.

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
- current active milestone
- current active task
- base branch
- active branch
- latest commit for the task when available
- resume decision
- overall task status table
- files changed for the active task
- implementation notes
- test execution log
- open questions
- blockers or stop reasons
- follow-up items

### Tracking constraints
- Keep entries short and factual.
- Update the existing progress file instead of creating a new ad hoc log.
- Do not mark a task done before the relevant tests have run, unless testing is impossible and the reason is recorded explicitly.
- If the tracker already shows a task as `in_progress` or `blocked`, resume or resolve that task before choosing a new one unless the roadmap was intentionally reprioritized.

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
1. Task 01: Console shell and template infrastructure
2. Task 02: Run overview and failure dashboard pages
3. Task 03: Article status and pending-review queue pages
4. Task 04: Review draft detail page
5. Task 05: Review action forms and safe mutation feedback
6. Task 06: Publish job list and detail pages
7. Task 07: Scheduler action console with safe defaults
8. Task 08: Console operator docs and browser-facing regression coverage

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the operator console readiness roadmap in this repository.

Start by reading:
- docs/operator-console-readiness-roadmap.md
- docs/operator-console-readiness-execution-guide.md
- docs/operator-console-readiness-progress-tracker.md
- docs/operator-console-readiness-vibe-prompts.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/operator-console-readiness-vibe-prompts.md.

Your job:
1. Determine whether docs/operator-console-readiness-progress-tracker.md already shows an active task. If it is `in_progress` or `blocked`, resume or resolve that task unless the roadmap was intentionally reprioritized.
2. If there is no active task, determine the next unfinished task in the recommended order.
3. Create or switch to a dedicated task branch using the git workflow rules in docs/operator-console-readiness-vibe-prompts.md.
4. Update docs/operator-console-readiness-progress-tracker.md to mark that task in progress and note the intended scope, branch, and verification plan.
5. Implement only that task cleanly and completely.
6. Keep docs/operator-console-readiness-progress-tracker.md updated during the work with changed files and key progress notes.
7. Add or update targeted tests.
8. Run relevant tests and record them in docs/operator-console-readiness-progress-tracker.md.
9. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
10. Mark the task complete in docs/operator-console-readiness-progress-tracker.md when verified, including branch and commit details.
11. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve manual review as the default gate
- keep dry-run as the default publish execution mode
- avoid broad architecture rewrites
- do not expand into auth, multi-user permissions, or a separate SPA unless the task explicitly requires it

If the next task is ambiguous, choose the smallest sensible interpretation that best exposes current operator capabilities through a browser without changing workflow semantics.
```

## Milestone Prompt
Use this when you want the agent to complete the first console milestone instead of one isolated unit.

```text
Implement the first read-only operator console foundation milestone described in docs/operator-console-readiness-roadmap.md.

Before editing:
- inspect the repository structure and current implementations
- identify which pieces of the milestone already exist and which are still missing
- create or switch to a dedicated milestone branch
- update docs/operator-console-readiness-progress-tracker.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- a console shell served by the current FastAPI app
- a run and failure dashboard page
- article status and pending-review queue pages
- focused browser-facing tests for those read-only pages

Constraints:
- preserve manual review and publish safety behavior
- keep publish-due dry-run by default
- no auth layer
- no separate SPA by default
- no broad subsystem redesign
- prefer additive template rendering and shared helper reuse over new business-logic layers
- add focused browser-facing tests for each new surface
- keep docs/operator-console-readiness-progress-tracker.md updated as work proceeds
- make intentional commits as milestone slices are completed

At the end, report:
- completed milestone scope
- changed files
- tests run
- branch and commit details
- remaining roadmap items not included
```

## Task 01: Console Shell And Template Infrastructure

### Objective
Add the minimal FastAPI-served console shell, template loader, and static-asset structure needed for later operator pages.

### Relevant code
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [pyproject.toml](/Users/sonmyeong-gwan/Desktop/sns-content-engine/pyproject.toml)
- [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md)
- [docs/operator-console-readiness-progress-tracker.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-console-readiness-progress-tracker.md)

### Expected result
- a dedicated console route namespace exists
- base template, shared layout, and minimal static assets are wired without a separate Node stack
- focused route coverage protects the shell entrypoint

### Autonomous prompt
```text
Implement Task 01 from docs/operator-console-readiness-roadmap.md.

Inspect:
- app/api/app.py
- pyproject.toml
- docs/finance-local-ui-data-contract.md

The gap to close is:
- the repository already has operator API surfaces and Jinja2 as a dependency
- but there is no browser console shell, template path, or static asset wiring yet

Make the smallest clean change that introduces a reusable console shell.

Requirements:
- keep the implementation inside the current FastAPI application
- avoid introducing a separate frontend toolchain by default
- keep the shell additive so later page tasks can build on it

Testing requirements:
- add focused tests for the console landing route and shell rendering
- run a broader API regression slice if shared app wiring changes
```

## Task 02: Run Overview And Failure Dashboard Pages

### Objective
Render recent pipeline runs, policy-aware counts, failures, and policy skips into a browser-friendly dashboard.

### Relevant code
- [app/workflows/history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/history_queries.py)
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md)
- [tests/test_history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_history_queries.py)

### Expected result
- the console has a dashboard page for recent runs and failure visibility
- the page reuses existing run and failure query helpers
- empty and populated dashboard states are covered by focused tests

### Autonomous prompt
```text
Implement Task 02 from docs/operator-console-readiness-roadmap.md.

Inspect:
- app/workflows/history_queries.py
- app/api/app.py
- docs/finance-local-ui-data-contract.md

The gap to close is:
- the run and failure data contracts already exist
- but there is no browser page that makes those summaries usable without the CLI or raw JSON

Make the smallest clean change that adds a read-only operator dashboard page.

Requirements:
- reuse existing history query helpers
- keep page shaping presentational
- include policy-aware run and failure data where already available

Testing requirements:
- add focused browser-page tests for empty and populated dashboard states
- run a broader history/API regression slice if shared query wiring changes
```

## Task 03: Article Status And Pending-Review Queue Pages

### Objective
Add read-only browser pages for article status and the pending review queue.

### Relevant code
- [app/workflows/history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/history_queries.py)
- [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md)

### Expected result
- operators can browse article enrichment state in the console
- operators can browse pending review drafts in the console
- list behavior stays aligned with current stored data and workflow helpers

### Autonomous prompt
```text
Implement Task 03 from docs/operator-console-readiness-roadmap.md.

Inspect:
- app/workflows/history_queries.py
- app/workflows/review_queue.py
- app/api/app.py

The gap to close is:
- article and pending-review reads already exist in backend form
- but there are no browser pages that render those list views for operators

Make the smallest clean change that adds article and pending-review list pages.

Requirements:
- reuse existing query and review-list helpers
- keep filters and ordering modest in the first version
- align visible fields with docs/finance-local-ui-data-contract.md

Testing requirements:
- add focused page tests for empty and populated list states
- run a broader API/review regression slice if shared helpers change
```

## Task 04: Review Draft Detail Page

### Objective
Expose one operator-ready review detail page in the console.

### Relevant code
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)

### Expected result
- one draft detail page shows draft text, provenance, brief context, enrichment, audit history, and sibling variants
- missing drafts return a clear browser-friendly not-found response
- handlers stay thin and reuse existing detail helpers

### Autonomous prompt
```text
Implement Task 04 from docs/operator-console-readiness-roadmap.md.

Inspect:
- app/api/app.py
- app/workflows/review_queue.py
- app/storage/repositories.py

The gap to close is:
- review detail data already exists for API consumers
- but there is no browser detail page that uses it for a real operator workspace

Make the smallest clean change that adds one draft detail page.

Requirements:
- reuse existing stored brief, source, enrichment, audit, and sibling-variant data
- keep route handlers thin
- return a clear not-found page state for missing drafts

Testing requirements:
- add focused page tests for populated and missing-draft responses
- run a broader review/API regression slice if shared helpers are touched
```

## Task 05: Review Action Forms And Safe Mutation Feedback

### Objective
Let operators perform approve, reject, edit, and schedule actions from the browser without changing review semantics.

### Relevant code
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- [app/services/draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/draft_validation.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)

### Expected result
- all four review actions are available through browser interactions
- validation and conflict errors render as readable operator feedback
- current attribution, provenance, and policy blockers remain intact

### Autonomous prompt
```text
Implement Task 05 from docs/operator-console-readiness-roadmap.md.

Inspect:
- app/api/app.py
- app/workflows/review_queue.py
- app/services/draft_validation.py

The gap to close is:
- review actions already exist through the API and CLI
- but there is no browser workflow for operators to use them safely

Make the smallest clean change that adds browser review actions.

Requirements:
- route all mutations through existing validation paths
- preserve current conflict and validation semantics
- keep manual review as the required gate before scheduling

Testing requirements:
- add focused page-action tests for success and representative failure paths
- run a broader review workflow regression slice if shared mutation logic changes
```

## Task 06: Publish Job List And Detail Pages

### Objective
Add browser visibility for publish-job queue and publish-log timelines.

### Relevant code
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- [docs/operator-control-plane-api.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-api.md)
- [tests/test_scheduler.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_scheduler.py)

### Expected result
- the console has publish-job list and detail pages
- linked draft/source context and publish logs are visible in the browser
- the first version stays read-only

### Autonomous prompt
```text
Implement Task 06 from docs/operator-console-readiness-roadmap.md.

Inspect:
- app/api/app.py
- app/storage/repositories.py
- docs/operator-control-plane-api.md

The gap to close is:
- publish job list and detail data already exist in the backend
- but operators cannot inspect them in a browser console yet

Make the smallest clean change that adds read-only publish-job pages.

Requirements:
- reuse the current publish-job list and detail helpers
- keep the first version read-only
- preserve the current linked draft/source context

Testing requirements:
- add focused page tests for empty, success, and failure states
- run a broader publish/API regression slice if shared helpers change
```

## Task 07: Scheduler Action Console With Safe Defaults

### Objective
Expose discover, backfill, and publish-due actions in the browser while keeping dry-run publish as the default.

### Relevant code
- [app/api/app.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/api/app.py)
- [app/scheduler/jobs.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/jobs.py)
- [app/scheduler/runtime.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/scheduler/runtime.py)
- [tests/test_scheduler.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_scheduler.py)

### Expected result
- discover, backfill, and publish-due actions can be triggered from the console
- publish-due stays dry-run by default and live publish requires explicit operator intent
- action summaries are readable in the browser

### Autonomous prompt
```text
Implement Task 07 from docs/operator-console-readiness-roadmap.md.

Inspect:
- app/api/app.py
- app/scheduler/jobs.py
- app/scheduler/runtime.py

The gap to close is:
- safe scheduler action wrappers already exist in the API
- but operators still need raw HTTP or CLI access to use them

Make the smallest clean change that adds scheduler controls to the console.

Requirements:
- keep discover and backfill straightforward
- keep publish-due dry-run by default
- if live publish is exposed, require explicit opt-in and make that state obvious in the UI

Testing requirements:
- add focused page-action tests for discover, backfill, default dry-run, and explicit live opt-in
- run a broader scheduler/API regression slice if shared action wiring changes
```

## Task 08: Console Operator Docs And Browser-Facing Regression Coverage

### Objective
Document the shipped console and protect its main flows with browser-facing regression tests.

### Relevant code
- [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md)
- [docs/operator-control-plane-api.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-api.md)
- [docs/operator-console-readiness-progress-tracker.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-console-readiness-progress-tracker.md)
- [tests/test_api.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_api.py)

### Expected result
- the repository has one clear guide for starting and using the console locally
- browser-facing regression coverage exists for the main console screens and actions
- docs keep manual-review and dry-run safety explicit

### Autonomous prompt
```text
Implement Task 08 from docs/operator-console-readiness-roadmap.md.

Inspect:
- README.md
- docs/operator-control-plane-api.md
- the current console tests

The gap to close is:
- the backend API is documented
- but there is no dedicated guide for the browser console and no final browser-facing regression sweep

Make the smallest clean change that documents the shipped console and protects its main contract.

Requirements:
- keep docs concise and operator-facing
- document how to start and use the console only after those flows are implemented
- keep manual review and dry-run publish defaults explicit

Testing requirements:
- run the focused console test suite
- run a broader API/review/scheduler regression slice if console work touched shared surfaces
```
