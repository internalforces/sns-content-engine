# Operator Console Readiness Autonomous Execution Guide

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in `docs/operator-console-readiness-roadmap.md`, inspect the repository, choose the smallest clean implementation shape for each gap, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current FastAPI and control-plane API implementation instead of inventing a new product from scratch,
- they constrain work so the existing safety model stays intact,
- they require reusing current workflows, queries, repositories, and scheduler helpers before adding new abstractions,
- they preserve manual review and dry-run publish defaults unless a task explicitly expands a surface.

Progress for live implementation should be tracked in:
- `docs/operator-console-readiness-progress-tracker.md`

## Generated document naming
When instantiating this template, use filenames that make each document's identity obvious at a glance.

- Roadmap file: `docs/operator-console-readiness-roadmap.md`
- Execution guide file: `docs/operator-console-readiness-execution-guide.md`
- Progress tracker file: `docs/operator-console-readiness-progress-tracker.md`
- Avoid ambiguous names like `todo.md`, `prompt.md`, `guide.md`, or `progress.md` when multiple initiatives may coexist.

## Repository Context
The repository already has:
- a working FastAPI application with operator health, history, article, review, publish-job, and scheduler endpoints
- existing workflow and repository-backed query helpers for runs, failures, articles, review detail, publish-job detail, and scheduler execution
- explicit operator-facing docs for the API and UI data contract expectations
- an existing `jinja2` dependency that makes a server-rendered console feasible without adding a Node stack by default

Important current files and patterns:
- Core entrypoints: `app/api/app.py`, `app/cli.py`
- Core workflows/services: `app/workflows/history_queries.py`, `app/workflows/review_queue.py`, `app/scheduler/jobs.py`
- Storage and schema logic: `app/storage/repositories.py`, `app/storage/models.py`
- Current placeholder or integration gap: `there is no template/static/page-route structure yet; the browser console does not exist`
- Existing operator or UI docs: `docs/finance-local-ui-data-contract.md`, `docs/operator-control-plane-api.md`
- Existing roadmap: `docs/operator-console-readiness-roadmap.md`

High-signal tests already exist and should be reused instead of inventing a new test structure:
- `tests/test_api.py`
- `tests/test_history_queries.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_scheduler.py`

## Execution Environment
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands by area:
  - `PYTHONPATH=$PWD pytest tests/test_api.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_review_queue_workflow.py tests/test_scheduler.py`
- Broader regression commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py tests/test_review_queue_workflow.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_cli.py`
- Required services:
  - `none for read-only and dry-run console work`
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
- Read `docs/operator-console-readiness-progress-tracker.md` before choosing the next task.
- Prefer reusing workflow and repository logic over duplicating it in new handlers, internal clients, or adapters.
- Keep each task self-contained and merge-friendly.
- Choose additive changes over broad redesigns.
- Preserve current behavior unless a task explicitly updates a shared abstraction.

### Resume rules
- If `docs/operator-console-readiness-progress-tracker.md` shows a current task with status `in_progress` or `blocked`, resume or resolve that task before selecting a new one unless the roadmap was intentionally reprioritized.
- Only choose the next unfinished task when there is no active task that still owns the current branch or implementation state.
- If the active task was blocked by a fixable local issue and the scope is still the same, keep the same task ID and continue instead of creating a new task.

### Roadmap shaping rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- When creating or refining the roadmap, choose only as many milestones and tasks as are needed to make forward progress safely.
- The sizing rule is: split work so it can be completed without breaking the current structure, safety model, workflow semantics, or operator experience.
- Prefer the smallest additive slices that fit the existing architecture.
- Split a task or milestone when it would otherwise require a separate frontend platform, mix unrelated browser surfaces, or make verification unclear.
- Merge adjacent tiny items when they share the same code path, tests, and commit scope.
- If the roadmap shape changes during implementation, update `docs/operator-console-readiness-roadmap.md` and `docs/operator-console-readiness-progress-tracker.md` before continuing.

### Scope control
- Do not expand work into authentication, multi-user permissions, or a separate SPA unless a task explicitly requires it.
- Do not redesign the domain model when existing workflow/query types can be adapted cleanly for page rendering.
- Do not add a Node build chain by default when the existing FastAPI and Jinja stack can handle the intended scope.

### Dirty worktree rules
- Inspect the current branch and working tree before making substantive edits when repository tooling is available.
- Never overwrite, revert, or stage unrelated changes.
- If user or pre-existing changes conflict directly with the active task in the same files, stop, record the conflict in `docs/operator-console-readiness-progress-tracker.md`, and treat the task as blocked until the conflict is resolved.
- Keep branch, staging, and commit scope limited to the active task.

### Safety constraints
- Preserve the current manual review gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Keep validation, provenance, and policy blockers intact.
- Keep dry-run publish as the default browser path and require explicit operator intent for any live publish path.

### Blocked-task rules
- Try the smallest reasonable local investigation first when a blocker appears.
- If progress is blocked by missing configuration, unavailable services, missing credentials, conflicting local edits, or unrelated failing tests, record the exact blocker and stop reason in `docs/operator-console-readiness-progress-tracker.md`.
- Mark the task `blocked` when work cannot continue safely inside the intended scope.
- Do not mark blocked work as `done`.
- Do not create a normal task-completion commit for blocked work; only create a checkpoint commit if the partial state is independently safe, intentionally scoped, and clearly documented.

### Testing rules
- Add or update targeted tests for every behavior change.
- Use task-specific verification commands from `docs/operator-console-readiness-roadmap.md` when they are provided.
- Run the narrowest relevant test set first.
- If a shared storage, workflow, or scheduler surface changes, run one broader regression slice too.
- If no explicit test command exists, infer the narrowest relevant command from the repository and record that reasoning in `docs/operator-console-readiness-progress-tracker.md`.
- Distinguish newly introduced failures from pre-existing failures or environment failures.
- If testing cannot run, record the exact command and reason as `not_run` or `pre_existing_failure`.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.

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
- Do not push branches or open pull requests unless explicitly requested.
- Use a clear commit message tied to the task outcome, for example:
  - `Add operator console shell`
  - `Add browser review detail workspace`
  - `Expose scheduler controls in operator console`

### Completion rules
- Only finish after code changes, verification, and progress updates are done.
- Do not mark a task complete until `docs/operator-console-readiness-progress-tracker.md` includes the final status, changed files, test log, and commit details or the reason a commit was not created.
- If the work cannot be finished safely, leave the task as `blocked` with a clear next step instead of forcing completion.
- Report:
  - what changed,
  - why that shape was chosen,
  - tests run,
  - branch and commit details,
  - any remaining follow-up intentionally deferred.

## Progress Tracking Rules
The agent must keep `docs/operator-console-readiness-progress-tracker.md` updated while implementing this roadmap.

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
List the actual tasks defined in `docs/operator-console-readiness-roadmap.md` in dependency order. Add or remove lines as needed; the task count is not fixed.

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
You are implementing the Operator Console Readiness roadmap in this repository.

Start by reading:
- docs/operator-console-readiness-roadmap.md
- docs/operator-console-readiness-execution-guide.md
- docs/operator-console-readiness-progress-tracker.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/operator-console-readiness-execution-guide.md.

Your job:
1. Determine whether docs/operator-console-readiness-progress-tracker.md already shows an active task. If it is `in_progress` or `blocked`, resume or resolve that task unless the roadmap was intentionally reprioritized.
2. If there is no active task, determine the next unfinished task in the recommended order.
3. If the roadmap shape is incomplete, too large, or unsafe to execute cleanly, refine the task or milestone boundaries using the smallest additive slices that preserve the current structure, then update docs/operator-console-readiness-roadmap.md and docs/operator-console-readiness-progress-tracker.md before coding.
4. Create or switch to a dedicated task branch using the git workflow rules in docs/operator-console-readiness-execution-guide.md.
5. Update docs/operator-console-readiness-progress-tracker.md to mark that task in progress and note the intended scope, branch, and verification plan.
6. Implement only that task cleanly and completely.
7. Keep docs/operator-console-readiness-progress-tracker.md updated during the work with changed files, progress notes, blockers, or stop reasons.
8. Add or update targeted tests.
9. Run the task verification commands from docs/operator-console-readiness-roadmap.md, plus one broader regression slice if shared surfaces changed, and record the results in docs/operator-console-readiness-progress-tracker.md.
10. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
11. Mark the task complete in docs/operator-console-readiness-progress-tracker.md when verified, including branch and commit details, or leave it `blocked` with a clear next step if it cannot be finished safely.
12. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve manual review
- keep dry-run publish as the default gate
- avoid broad architecture rewrites
- do not expand into auth, multi-user permissions, or a separate SPA unless the task explicitly requires it
- do not push or open a PR unless explicitly requested

If the next task is ambiguous, choose the smallest sensible interpretation that best exposes current operator capabilities through a browser without changing workflow semantics.
```

## Milestone Prompt
Use this when you want the agent to complete the current incomplete milestone instead of one isolated unit.

```text
Implement the current incomplete Read-Only Console Foundation milestone described in docs/operator-console-readiness-roadmap.md.

Before editing:
- inspect the repository structure and current implementations
- identify which pieces of the milestone already exist and which are still missing
- if the milestone is too large to complete safely without disrupting the current structure, split it into smaller milestones or tasks and update docs/operator-console-readiness-roadmap.md and docs/operator-console-readiness-progress-tracker.md before coding
- create or switch to a dedicated milestone branch
- update docs/operator-console-readiness-progress-tracker.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- a console shell served by the current FastAPI app
- a run and failure dashboard page
- article status and pending-review queue pages
- focused browser-facing tests for those read-only pages

Constraints:
- preserve current safety behavior
- no auth layer
- no separate SPA by default
- no broad subsystem redesign
- keep the milestone bounded so it can be completed without breaking the current structure
- prefer additive template rendering and shared helper reuse over new business-logic layers
- add focused tests for each new surface
- keep docs/operator-console-readiness-progress-tracker.md updated as work proceeds
- make intentional commits as milestone slices are completed
- do not push or open a PR unless explicitly requested

At the end, report:
- completed milestone scope
- changed files
- tests run
- branch and commit details
- remaining roadmap items not included
```

## Task Detail Blocks
Duplicate or remove the task sections below as needed. The number of task sections is intentionally not fixed.

Each task section should stay small enough to be implemented, tested, logged, and committed without breaking the overall structure.
For each task, fill in the objective, relevant code, expected result, dependencies, verification expectations, and autonomous prompt as concretely as possible.

## Task 01: Console shell and template infrastructure

### Objective
Add the minimal FastAPI-served console shell, template loader, and static-asset structure needed for later operator pages.

### Relevant code
- `app/api/app.py`
- `pyproject.toml`
- `docs/finance-local-ui-data-contract.md`
- `tests/test_api.py`

### Expected result
- a dedicated console route namespace exists
- base template, navigation, and static assets are wired without a separate Node stack
- focused route coverage protects the console shell

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
- run one broader API regression slice if shared app wiring changes
```

## Task 02: Run overview and failure dashboard pages

### Objective
Render recent pipeline runs, policy-aware counts, failures, and policy skips into a browser-friendly dashboard.

### Relevant code
- `app/workflows/history_queries.py`
- `app/api/app.py`
- `docs/finance-local-ui-data-contract.md`
- `tests/test_history_queries.py`

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
- the run and failure data contracts exist
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

## Task 03: Article status and pending-review queue pages

### Objective
Add read-only browser pages for article status and the pending review queue.

### Relevant code
- `app/workflows/history_queries.py`
- `app/workflows/review_queue.py`
- `app/api/app.py`
- `tests/test_review_queue_workflow.py`

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

## Task 04: Review draft detail page

### Objective
Expose one operator-ready review detail page in the console.

### Relevant code
- `app/api/app.py`
- `app/workflows/review_queue.py`
- `app/storage/repositories.py`
- `tests/test_api.py`

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

## Task 05: Review action forms and safe mutation feedback

### Objective
Let operators perform approve, reject, edit, and schedule actions from the browser without changing review semantics.

### Relevant code
- `app/api/app.py`
- `app/workflows/review_queue.py`
- `app/services/draft_validation.py`
- `tests/test_review_queue_workflow.py`

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

## Task 06: Publish job list and detail pages

### Objective
Add browser visibility for publish-job queue and publish-log timelines.

### Relevant code
- `app/api/app.py`
- `app/workflows/history_queries.py`
- `app/storage/repositories.py`
- `tests/test_scheduler.py`

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
- tests/test_api.py

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

## Task 07: Scheduler action console with safe defaults

### Objective
Expose discover, backfill, and publish-due actions in the browser while keeping dry-run publish as the default.

### Relevant code
- `app/api/app.py`
- `app/scheduler/jobs.py`
- `app/scheduler/runtime.py`
- `tests/test_scheduler.py`

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

## Task 08: Console operator docs and browser-facing regression coverage

### Objective
Document the shipped console and protect its main flows with browser-facing regression tests.

### Relevant code
- `README.md`
- `docs/operator-control-plane-api.md`
- `tests/test_api.py`
- `tests/test_scheduler.py`

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
