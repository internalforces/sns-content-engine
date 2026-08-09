# Multichannel Manual Publish Readiness Autonomous Execution Guide

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in `docs/multichannel-manual-publish-readiness-roadmap.md`, inspect the repository, choose the smallest clean implementation shape for each gap, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current implementation instead of inventing a new product from scratch,
- they constrain work so the existing safety model stays intact,
- they require reusing current workflows and repositories before adding new abstractions,
- they preserve the manual review gate and X dry-run or live publish safety defaults unless a task explicitly expands a surface.

Progress for live implementation should be tracked in:
- `docs/multichannel-manual-publish-readiness-progress-tracker.md`

## Generated document naming
When instantiating this template, use filenames that make each document's identity obvious at a glance.

- Roadmap file: `docs/multichannel-manual-publish-readiness-roadmap.md`
- Execution guide file: `docs/multichannel-manual-publish-readiness-execution-guide.md`
- Progress tracker file: `docs/multichannel-manual-publish-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/multichannel-manual-publish-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `prompt.md`, `guide.md`, or `progress.md` when multiple initiatives may coexist.

## Repository Context
The repository already has:
- config-driven draft generation for X, LinkedIn, and Threads
- review queue, publish job, and publish log persistence
- FastAPI control-plane routes plus a server-rendered operator console
- a live X publisher plus browser guidance for manual non-X uploads

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/api/app.py`
- Core workflows or services: `app/workflows/review_queue.py`, `app/scheduler/jobs.py`
- Storage and schema logic: `app/storage/models.py`, `app/storage/repositories.py`
- Current placeholder or integration gap: `app/connectors/publishers/resolver.py`, `app/api/console.py`
- Existing operator or UI docs: `docs/operator-console-guide.md`, `docs/operator-control-plane-api.md`
- Existing roadmap: `docs/multichannel-manual-publish-readiness-roadmap.md`

High-signal tests already exist and should be reused instead of inventing a new test structure:
- `tests/test_operations.py`
- `tests/test_scripts.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_api.py`
- `tests/test_console.py`
- `tests/test_scheduler.py`
- `tests/test_x_publisher.py`

## Execution Environment
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands by area:
  - `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest -q`
- Required services:
  - `none`
  - `local SQLite only`
- Required env files, secrets, or fixtures:
  - `.env is optional unless a live provider or live X publish path is under test`
  - `tests/fixtures and temp SQLite databases are already present and should be reused first`
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path before editing.
- Read `docs/multichannel-manual-publish-readiness-progress-tracker.md` before choosing the next task.
- Prefer reusing workflow and repository logic over duplicating it in new handlers or adapters.
- Keep each task self-contained and merge-friendly.
- Choose additive changes over broad redesigns.
- Preserve current behavior unless a task explicitly updates a shared abstraction.

### Resume rules
- If `docs/multichannel-manual-publish-readiness-progress-tracker.md` shows a current task with status `in_progress` or `blocked`, resume or resolve that task before selecting a new one unless the roadmap was intentionally reprioritized.
- Only choose the next unfinished task when there is no active task that still owns the current branch or implementation state.
- If the active task was blocked by a fixable local issue and the scope is still the same, keep the same task ID and continue instead of creating a new task.

### Roadmap shaping rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- When creating or refining the roadmap, choose only as many milestones and tasks as are needed to make forward progress safely.
- The sizing rule is: split work so it can be completed without breaking the current structure, safety model, workflow semantics, or operator experience.
- Prefer the smallest additive slices that fit the existing architecture.
- Split a task or milestone when it would otherwise require a broad redesign, mix unrelated surfaces, or make verification unclear.
- Merge adjacent tiny items when they share the same code path, tests, and commit scope.
- If the roadmap shape changes during implementation, update `docs/multichannel-manual-publish-readiness-roadmap.md` and `docs/multichannel-manual-publish-readiness-progress-tracker.md` before continuing.

### Scope control
- Do not expand work into authentication, multi-user permissions, or a full frontend unless the task explicitly requires it.
- Do not redesign the domain model when existing workflow, repository, and publish-log types can be adapted cleanly.
- Keep migration or schema work modest and practical; the goal is safe operator workflow expansion, not a platform rewrite.

### Dirty worktree rules
- Inspect the current branch and working tree before making substantive edits when repository tooling is available.
- Never overwrite, revert, or stage unrelated changes.
- If user or pre-existing changes conflict directly with the active task in the same files, stop, record the conflict in `docs/multichannel-manual-publish-readiness-progress-tracker.md`, and treat the task as blocked until the conflict is resolved.
- Keep branch, staging, and commit scope limited to the active task.

### Safety constraints
- Preserve the current review or approval gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Keep validation and policy blockers intact.
- Preserve X dry-run-by-default scheduler behavior unless a task explicitly says otherwise.
- For non-X channels, prefer explicit operator handoff and completion recording over speculative automation.

### Blocked-task rules
- Try the smallest reasonable local investigation first when a blocker appears.
- If progress is blocked by missing configuration, unavailable services, missing credentials, conflicting local edits, or unrelated failing tests, record the exact blocker and stop reason in `docs/multichannel-manual-publish-readiness-progress-tracker.md`.
- Mark the task `blocked` when work cannot continue safely inside the intended scope.
- Do not mark blocked work as `done`.
- Do not create a normal task-completion commit for blocked work; only create a checkpoint commit if the partial state is independently safe, intentionally scoped, and clearly documented.

### Testing rules
- Add or update targeted tests for every behavior change.
- Use task-specific verification commands from `docs/multichannel-manual-publish-readiness-roadmap.md` when they are provided.
- Run the narrowest relevant test set first.
- If a shared storage, workflow, or operator surface changes, run one broader regression slice too.
- If no explicit test command exists, infer the narrowest relevant command from the repository and record that reasoning in `docs/multichannel-manual-publish-readiness-progress-tracker.md`.
- Distinguish newly introduced failures from pre-existing failures or environment failures.
- If testing cannot run, record the exact command and reason as `not_run` or `pre_existing_failure`.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-healthcheck-baseline`
  - `codex/task-04-manual-publish-outcome`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Do not push branches or open pull requests unless explicitly requested.
- Use a clear commit message tied to the task outcome, for example:
  - `Restore readiness smoke baseline`
  - `Add manual publish outcome workflow`
  - `Expose manual handoff controls`

### Completion rules
- Only finish after code changes, verification, and progress updates are done.
- Do not mark a task complete until `docs/multichannel-manual-publish-readiness-progress-tracker.md` includes the final status, changed files, test log, and commit details or the reason a commit was not created.
- If the work cannot be finished safely, leave the task as `blocked` with a clear next step instead of forcing completion.
- Report:
  - what changed,
  - why that shape was chosen,
  - tests run,
  - branch and commit details,
  - any remaining follow-up intentionally deferred.

## Progress Tracking Rules
The agent must keep `docs/multichannel-manual-publish-readiness-progress-tracker.md` updated while implementing this roadmap.

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
1. Task 01: Restore healthcheck and smoke baseline
2. Task 02: Refresh stale roadmap and TODO docs
3. Task 03: Define non-X manual publish handoff model
4. Task 04: Add manual publish outcome workflow and persistence
5. Task 05: Expose manual handoff controls through API and console
6. Task 06: Document multichannel handoff flow and expand regressions

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the Multichannel Manual Publish Readiness roadmap in this repository.

Start by reading:
- docs/multichannel-manual-publish-readiness-roadmap.md
- docs/multichannel-manual-publish-readiness-execution-guide.md
- docs/multichannel-manual-publish-readiness-progress-tracker.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/multichannel-manual-publish-readiness-execution-guide.md.

Your job:
1. Determine whether docs/multichannel-manual-publish-readiness-progress-tracker.md already shows an active task. If it is `in_progress` or `blocked`, resume or resolve that task unless the roadmap was intentionally reprioritized.
2. If there is no active task, determine the next unfinished task in the recommended order.
3. If the roadmap shape is incomplete, too large, or unsafe to execute cleanly, refine the task or milestone boundaries using the smallest additive slices that preserve the current structure, then update docs/multichannel-manual-publish-readiness-roadmap.md and docs/multichannel-manual-publish-readiness-progress-tracker.md before coding.
4. Create or switch to a dedicated task branch using the git workflow rules in docs/multichannel-manual-publish-readiness-execution-guide.md.
5. Update docs/multichannel-manual-publish-readiness-progress-tracker.md to mark that task in progress and note the intended scope, branch, and verification plan.
6. Implement only that task cleanly and completely.
7. Keep docs/multichannel-manual-publish-readiness-progress-tracker.md updated during the work with changed files, progress notes, blockers, or stop reasons.
8. Add or update targeted tests.
9. Run the task verification commands from docs/multichannel-manual-publish-readiness-roadmap.md, plus one broader regression slice if shared surfaces changed, and record the results in docs/multichannel-manual-publish-readiness-progress-tracker.md.
10. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
11. Mark the task complete in docs/multichannel-manual-publish-readiness-progress-tracker.md when verified, including branch and commit details, or leave it `blocked` with a clear next step if it cannot be finished safely.
12. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve the manual review gate
- keep X dry-run or explicit-live publish safety as the default gate
- avoid broad architecture rewrites
- do not expand into auth, frontend implementation, or speculative platform work unless the task explicitly requires it
- do not push or open a PR unless explicitly requested

If the next task is ambiguous, choose the smallest sensible interpretation that best restores baseline safety, improves operator visibility, or advances the stated milestone without changing workflow semantics.
```

## Milestone Prompt
Use this when you want the agent to complete the current incomplete milestone instead of one isolated unit.

```text
Implement the current incomplete milestone described in docs/multichannel-manual-publish-readiness-roadmap.md.

Before editing:
- inspect the repository structure and current implementations
- identify which pieces of the milestone already exist and which are still missing
- if the milestone is too large to complete safely without disrupting the current structure, split it into smaller milestones or tasks and update docs/multichannel-manual-publish-readiness-roadmap.md and docs/multichannel-manual-publish-readiness-progress-tracker.md before coding
- create or switch to a dedicated milestone branch
- update docs/multichannel-manual-publish-readiness-progress-tracker.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- restore the clean readiness baseline if the milestone still depends on it
- preserve the existing review gate and X publish safety behavior
- add the smallest reusable non-X manual handoff slice required by the milestone
- update docs and tests so shipped behavior stays explicit

Constraints:
- preserve current safety behavior
- no auth layer
- no frontend implementation
- no broad subsystem redesign
- keep the milestone bounded so it can be completed without breaking the current structure
- prefer additive workflow, route wiring, or adapter work over new parallel business-logic layers
- add focused tests for each new surface
- keep docs/multichannel-manual-publish-readiness-progress-tracker.md updated as work proceeds
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
Each task section should stay small enough to be implemented, tested, logged, and committed without breaking the overall structure.
For each task, fill in the objective, relevant code, expected result, dependencies, verification expectations, and autonomous prompt as concretely as possible.

## Task 01: Restore Healthcheck And Smoke Baseline

### Objective
Return the repository to a clean readiness baseline by resolving the two current healthcheck-related regressions without weakening operator-ready guardrails.

### Relevant code
- `app/operations.py`
- `tests/test_operations.py`
- `tests/test_scripts.py`
- `tests/test_cli.py`

### Expected result
- readiness behavior and tests agree on the current bundled-sample and placeholder-URL policy
- the smoke config fixture no longer pretends that placeholder URLs are operator-ready
- focused readiness and healthcheck tests pass again

### Autonomous prompt
```text
Implement Task 01 from docs/multichannel-manual-publish-readiness-roadmap.md.

Inspect:
- app/operations.py
- tests/test_operations.py
- tests/test_scripts.py

The gap to close is:
- the repository currently has two failing readiness-related tests
- the smoke config fixture and one bundled-sample expectation have drifted from the current config_readiness policy

Make the smallest clean change that introduces or improves:
- a consistent healthcheck expectation for bundled sample configs
- an operator-ready smoke fixture shape
- a green readiness baseline

Requirements:
- reuse the current healthcheck and CLI behavior
- keep operator-facing failure messages explicit
- do not weaken the bundled-sample or placeholder URL guardrails just to satisfy tests
- do not add auth or deployment concerns

Testing requirements:
- add or update focused tests for the readiness behavior
- run one broader healthcheck regression slice if shared helpers are touched
```

## Task 02: Refresh Stale Roadmap And TODO Docs

### Objective
Clean up stale planning documents so completed initiatives read as historical context and this initiative becomes the clear follow-on plan.

### Relevant code
- `docs/api-operations-readiness-todo.md`
- `docs/operator-control-plane-readiness-todo.md`
- `docs/all-domain-news-todo.md`
- `docs/implementation-alignment-todo.md`

### Expected result
- completed roadmap docs no longer describe finished work as if it were the active next step
- follow-up notes point to the multichannel manual publish readiness initiative where appropriate
- the historical execution record remains intact

### Autonomous prompt
```text
Implement Task 02 from docs/multichannel-manual-publish-readiness-roadmap.md.

Inspect the current roadmap, progress, and TODO docs first.

Expose a clean planning state for:
- completed initiatives that should now read as historical context
- the new follow-on initiative that should own the next active work

Requirements:
- prefer factual superseded or follow-up notes over broad rewrites
- keep filenames stable
- preserve useful implementation history and commit references
- avoid speculative future work that is not part of the new initiative

Testing requirements:
- run docs-only verification such as git diff --check
- keep related planning docs internally consistent
```

## Task 03: Define Non-X Manual Publish Handoff Model

### Objective
Add the smallest workflow and data contract needed to represent manual LinkedIn and Threads publish handoffs using the existing publish job and log model where practical.

### Relevant code
- `app/workflows/review_queue.py`
- `app/scheduler/jobs.py`
- `app/storage/models.py`
- `app/storage/repositories.py`

### Expected result
- approved non-X drafts can move into an explicit operator-trackable handoff state
- the solution reuses publish jobs and logs instead of inventing a parallel model unless clearly necessary
- X scheduling and live publish semantics stay unchanged

### Autonomous prompt
```text
Implement Task 03 from docs/multichannel-manual-publish-readiness-roadmap.md.

Inspect current action handlers and publish-job behavior first.

Expose handlers or entrypoints for:
- non-X manual handoff creation
- reuse of the existing publish job lifecycle where practical
- explicit channel-aware handoff rules
- clear refusal for unsupported or invalid paths

Requirements:
- reuse existing workflow functions and repository helpers
- preserve the current manual-review and X schedule-time semantics
- keep the new handoff model additive and operator-safe
- do not redesign the review model or create a second publish subsystem unless forced by data constraints

Testing requirements:
- add focused tests for at least one successful non-X handoff path and one invalid path
- run the existing workflow and storage tests if shared lifecycle behavior changes
```

## Task 04: Add Manual Publish Outcome Workflow And Persistence

### Objective
Let operators record manual publish completion, failure, or cancellation for non-X channels with auditability and explicit error handling.

### Relevant code
- `app/workflows/review_queue.py`
- `app/storage/repositories.py`
- `app/storage/models.py`
- `app/api/app.py`

### Expected result
- workflow-backed manual publish outcome mutations exist for non-X channels
- publish logs and state transitions capture useful operator-facing context
- invalid channels or state transitions fail clearly

### Autonomous prompt
```text
Implement Task 04 from docs/multichannel-manual-publish-readiness-roadmap.md.

Inspect the current workflow mutation path and publish state machine first.

The gap to close is:
- non-X channels cannot currently be marked published or failed through supported workflow helpers
- publish visibility surfaces can already show non-X jobs, but no real operator-safe mutation path exists

Add the smallest practical workflow and persistence support for intentional local operator updates.

Requirements:
- keep the design modest and compatible with the current environment
- avoid overengineering a separate manual-publish framework if the current publish-job and publish-log model works
- keep operator failure messages explicit
- preserve the existing publish state checks wherever practical

Testing requirements:
- add focused tests for at least one success path and one invalid transition
- run broader storage or workflow regression coverage if lifecycle behavior changes substantially
```

## Task 05: Expose Manual Handoff Controls Through API And Console

### Objective
Expose the new manual handoff lifecycle through supported FastAPI and server-rendered console controls without duplicating workflow logic.

### Relevant code
- `app/api/app.py`
- `app/api/console.py`
- `app/api/templates/console/review_detail.html`
- `app/api/templates/console/publish_job_detail.html`

### Expected result
- operators can create and complete non-X handoffs through API or console controls
- the console still shows clear manual upload guidance while adding status-changing actions where appropriate
- X live publish and scheduler controls remain unaffected

### Autonomous prompt
```text
Implement Task 05 from docs/multichannel-manual-publish-readiness-roadmap.md.

Inspect the current readiness behavior, review detail console flow, and publish-job API contract first.

Improve operator workflow around:
- manual handoff creation
- manual upload completion or failure recording
- linked review and publish-job visibility

Requirements:
- prefer thin API and console surfaces that call existing workflow helpers
- keep the console server-rendered
- avoid blocking legitimate X live publish flows or scheduler behavior
- keep docs and route naming practical and explicit

Testing requirements:
- add focused API and console tests for the new operator actions
- keep linked data and state transition behavior covered by shared regression slices
```

## Task 06: Document Multichannel Handoff Flow And Expand Regressions

### Objective
Document the shipped X-live versus non-X-manual flow and protect it with focused regression coverage.

### Relevant code
- `README.md`
- `docs/operator-console-guide.md`
- `docs/operator-control-plane-api.md`
- `tests/test_api.py`

### Expected result
- operator-facing docs clearly describe manual handoff semantics for LinkedIn and Threads
- regression coverage protects the new linked-data and operator-action paths
- the documented behavior matches the implementation exactly

### Autonomous prompt
```text
Implement Task 06 from docs/multichannel-manual-publish-readiness-roadmap.md.

Inspect the current docs, API contract, and console operator flow first.

Add a small, additive documentation and regression hardening pass so the new multichannel handoff behavior is easy to operate and difficult to regress.

Requirements:
- prefer explicit operator guidance over vague future-looking statements
- keep the current default behavior intact
- preserve workflow-level failure handling and policy gating
- do not expand into a generalized non-X automation platform

Testing requirements:
- add focused coverage for the documented handoff behavior
- run at least one broader workflow or console slice if linked operator paths change
```

## Suggested Working Pattern
When using this document operationally:
1. Run the Master Prompt to let the agent resume the current task or pick the next unfinished task.
2. If tighter control is needed, run a single task prompt directly.
3. Keep work scoped to one task per branch or commit when possible.
4. During active implementation, keep `docs/multichannel-manual-publish-readiness-progress-tracker.md` current.
5. After each completed task, update the roadmap or progress notes.

## Operator Note
If you want the agent to continue through multiple tasks without asking each time, pair the Master Prompt with a simple instruction such as:

```text
Continue task-by-task in roadmap order. After each task, commit only if tests pass and the scope is still clean.
```
