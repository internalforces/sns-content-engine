# Threads API Publish Readiness Autonomous Execution Guide

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in `docs/threads-api-publish-readiness-roadmap.md`, inspect the repository, choose the smallest clean implementation shape for each gap, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current implementation instead of inventing a new product from scratch,
- they constrain work so the existing safety model stays intact,
- they require reusing current workflows and repositories before adding new abstractions,
- they preserve the manual review gate and dry-run publish defaults unless a task explicitly expands a surface.

Progress for live implementation should be tracked in:
- `docs/threads-api-publish-readiness-progress-tracker.md`

## Generated document naming
When instantiating this template, use filenames that make each document's identity obvious at a glance.

- Roadmap file: `docs/threads-api-publish-readiness-roadmap.md`
- Execution guide file: `docs/threads-api-publish-readiness-execution-guide.md`
- Progress tracker file: `docs/threads-api-publish-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/threads-api-publish-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `prompt.md`, `guide.md`, or `progress.md` when multiple initiatives may coexist.

## Repository Context
The repository already has:
- config-driven draft generation for `x`, `linkedin`, and `threads`
- persisted review actions, publish jobs, publish logs, and scheduler-visible publish state
- a live X publisher plus config-backed publisher resolution and due-job execution
- explicit LinkedIn and Threads manual handoff workflow, API routes, and browser console actions

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/api/app.py`
- Core workflows or services: `app/workflows/review_queue.py`, `app/scheduler/jobs.py`
- Storage and schema logic: `app/storage/models.py`, `app/storage/repositories.py`
- Current placeholder or integration gap: `app/connectors/publishers/resolver.py`, `app/api/console.py`
- Existing operator or UI docs: `README.md`, `docs/operator-console-guide.md`, `docs/operator-control-plane-api.md`
- Existing roadmap: `docs/threads-api-publish-readiness-roadmap.md`

High-signal tests already exist and should be reused instead of inventing a new test structure:
- `tests/test_x_publisher.py`
- `tests/test_scheduler.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_api.py`
- `tests/test_console.py`

## Execution Environment
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands by area:
  - `./.venv/bin/pytest tests/test_x_publisher.py tests/test_scheduler.py -q`
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_scheduler.py tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest -q`
- Required services:
  - `none for adapter and workflow regression work`
  - `optional live Threads API connectivity only for explicit smoke verification after implementation`
- Required env files, secrets, or fixtures:
  - `.env is optional unless a live Threads publish smoke test is under test`
  - `temporary SQLite fixtures and per-test config directories are already present in the repository`
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path before editing.
- Read `docs/threads-api-publish-readiness-progress-tracker.md` before choosing the next task.
- Prefer reusing workflow and repository logic over duplicating it in new handlers or adapters.
- Keep each task self-contained and merge-friendly.
- Choose additive changes over broad redesigns.
- Preserve current behavior unless a task explicitly updates a shared abstraction.

### Resume rules
- If `docs/threads-api-publish-readiness-progress-tracker.md` shows a current task with status `in_progress` or `blocked`, resume or resolve that task before selecting a new one unless the roadmap was intentionally reprioritized.
- Only choose the next unfinished task when there is no active task that still owns the current branch or implementation state.
- If the active task was blocked by a fixable local issue and the scope is still the same, keep the same task ID and continue instead of creating a new task.

### Roadmap shaping rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- When creating or refining the roadmap, choose only as many milestones and tasks as are needed to make forward progress safely.
- The sizing rule is: split work so it can be completed without breaking the current structure, safety model, workflow semantics, or operator experience.
- Prefer the smallest additive slices that fit the existing architecture.
- Split a task or milestone when it would otherwise require a broad redesign, mix unrelated surfaces, or make verification unclear.
- Merge adjacent tiny items when they share the same code path, tests, and commit scope.
- If the roadmap shape changes during implementation, update `docs/threads-api-publish-readiness-roadmap.md` and `docs/threads-api-publish-readiness-progress-tracker.md` before continuing.

### Scope control
- Do not expand work into authentication, multi-user permissions, or a full frontend unless the task explicitly requires it.
- Do not redesign the domain model when existing workflow, scheduler, or query types can be adapted cleanly.
- Keep migration work modest and practical; the goal is Threads live-publish readiness, not a full platform rebuild.

### Dirty worktree rules
- Inspect the current branch and working tree before making substantive edits when repository tooling is available.
- Never overwrite, revert, or stage unrelated changes.
- If user or pre-existing changes conflict directly with the active task in the same files, stop, record the conflict in `docs/threads-api-publish-readiness-progress-tracker.md`, and treat the task as blocked until the conflict is resolved.
- Keep branch, staging, and commit scope limited to the active task.

### Safety constraints
- Preserve the current review or approval gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Keep validation and policy blockers intact.
- Keep `publish-due` dry-run-by-default and route live publish through the existing scheduler path.
- Preserve LinkedIn manual handoff behavior unless a later task explicitly expands that scope.

### Blocked-task rules
- Try the smallest reasonable local investigation first when a blocker appears.
- If progress is blocked by missing configuration, unavailable services, missing credentials, conflicting local edits, or unrelated failing tests, record the exact blocker and stop reason in `docs/threads-api-publish-readiness-progress-tracker.md`.
- Mark the task `blocked` when work cannot continue safely inside the intended scope.
- Do not mark blocked work as `done`.
- Do not create a normal task-completion commit for blocked work; only create a checkpoint commit if the partial state is independently safe, intentionally scoped, and clearly documented.

### Testing rules
- Add or update targeted tests for every behavior change.
- Use task-specific verification commands from `docs/threads-api-publish-readiness-roadmap.md` when they are provided.
- Run the narrowest relevant test set first.
- If a shared storage, workflow, or operator surface changes, run one broader regression slice too.
- If no explicit test command exists, infer the narrowest relevant command from the repository and record that reasoning in `docs/threads-api-publish-readiness-progress-tracker.md`.
- Distinguish newly introduced failures from pre-existing failures or environment failures.
- If testing cannot run, record the exact command and reason as `not_run` or `pre_existing_failure`.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-threads-publisher-adapter`
  - `codex/task-04-threads-live-operator-surfaces`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Do not push branches or open pull requests unless explicitly requested.
- Use a clear commit message tied to the task outcome, for example:
  - `Add Threads publisher adapter`
  - `Resolve Threads publishers from config`
  - `Make Threads scheduling publisher-aware`

### Completion rules
- Only finish after code changes, verification, and progress updates are done.
- Do not mark a task complete until `docs/threads-api-publish-readiness-progress-tracker.md` includes the final status, changed files, test log, and commit details or the reason a commit was not created.
- If the work cannot be finished safely, leave the task as `blocked` with a clear next step instead of forcing completion.
- Report:
  - what changed,
  - why that shape was chosen,
  - tests run,
  - branch and commit details,
  - any remaining follow-up intentionally deferred.

## Progress Tracking Rules
The agent must keep `docs/threads-api-publish-readiness-progress-tracker.md` updated while implementing this roadmap.

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
1. Task 01: Define Threads credential bundle and publisher adapter
2. Task 02: Expand config-backed publisher resolution for Threads
3. Task 03: Make Threads review and scheduling flow publisher-aware
4. Task 04: Carry Threads live jobs through scheduler, API, and console surfaces
5. Task 05: Document token-ready Threads setup and expand regressions

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the Threads API Publish Readiness roadmap in this repository.

Start by reading:
- docs/threads-api-publish-readiness-roadmap.md
- docs/threads-api-publish-readiness-execution-guide.md
- docs/threads-api-publish-readiness-progress-tracker.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/threads-api-publish-readiness-execution-guide.md.

Your job:
1. Determine whether docs/threads-api-publish-readiness-progress-tracker.md already shows an active task. If it is `in_progress` or `blocked`, resume or resolve that task unless the roadmap was intentionally reprioritized.
2. If there is no active task, determine the next unfinished task in the recommended order.
3. If the roadmap shape is incomplete, too large, or unsafe to execute cleanly, refine the task or milestone boundaries using the smallest additive slices that preserve the current structure, then update docs/threads-api-publish-readiness-roadmap.md and docs/threads-api-publish-readiness-progress-tracker.md before coding.
4. Create or switch to a dedicated task branch using the git workflow rules in docs/threads-api-publish-readiness-execution-guide.md.
5. Update docs/threads-api-publish-readiness-progress-tracker.md to mark that task in progress and note the intended scope, branch, and verification plan.
6. Implement only that task cleanly and completely.
7. Keep docs/threads-api-publish-readiness-progress-tracker.md updated during the work with changed files, progress notes, blockers, or stop reasons.
8. Add or update targeted tests.
9. Run the task verification commands from docs/threads-api-publish-readiness-roadmap.md, plus one broader regression slice if shared behavior changed, and record the results in docs/threads-api-publish-readiness-progress-tracker.md.
10. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
11. Mark the task complete in docs/threads-api-publish-readiness-progress-tracker.md when verified, including branch and commit details, or leave it `blocked` with a clear next step if it cannot be finished safely.
12. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve the manual review gate
- keep `publish-due` dry-run-by-default unless an explicit live run is requested
- avoid broad architecture rewrites
- do not expand into auth, frontend implementation, or speculative LinkedIn work unless the task explicitly requires it
- do not push or open a PR unless explicitly requested

If the next task is ambiguous, choose the smallest sensible interpretation that best exposes current capabilities, improves operator safety, or advances the stated milestone without changing workflow semantics.
```

## Milestone Prompt
Use this when you want the agent to complete the current incomplete milestone instead of one isolated unit.

```text
Implement the current incomplete Threads Workflow Integration milestone described in docs/threads-api-publish-readiness-roadmap.md.

Before editing:
- inspect the repository structure and current implementations
- identify which pieces of the milestone already exist and which are still missing
- if the milestone is too large to complete safely without disrupting the current structure, split it into smaller milestones or tasks and update docs/threads-api-publish-readiness-roadmap.md and docs/threads-api-publish-readiness-progress-tracker.md before coding
- create or switch to a dedicated milestone branch
- update docs/threads-api-publish-readiness-progress-tracker.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- add config-gated Threads live scheduling support
- preserve manual Threads fallback when no live publisher is configured
- keep LinkedIn manual handoff semantics unchanged
- expand focused workflow, scheduler, API, and console coverage

Constraints:
- preserve current safety behavior
- no auth layer
- no frontend redesign
- no broad scheduler or persistence redesign
- keep the milestone bounded so it can be completed without breaking the current structure
- prefer additive adapter, resolver, and workflow-capability checks over new business-logic layers
- add focused tests for each new surface
- keep docs/threads-api-publish-readiness-progress-tracker.md updated as work proceeds
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

## Task 01: Define Threads credential bundle and publisher adapter

### Objective
Add a minimal Threads publisher implementation that accepts the existing normalized publish request and returns normalized publish results.

### Relevant code
- `app/connectors/publishers/base.py`
- `app/connectors/publishers/x.py`
- `app/connectors/publishers/__init__.py`
- `tests/test_x_publisher.py`

### Expected result
- A dedicated Threads publisher exists with an isolated HTTP boundary.
- The chosen credential contract is explicit and test-covered.
- Success, provider failure, and malformed response paths normalize into `PublishResult`.

## Task 02: Expand config-backed publisher resolution for Threads

### Objective
Resolve Threads publishers from the existing account or channel config plus env bundle without adding a second operator setup path.

### Relevant code
- `app/connectors/publishers/resolver.py`
- `app/config/schemas.py`
- `config/accounts.yaml`
- `tests/test_scheduler.py`

### Expected result
- Resolver support exists for `threads`.
- Missing or malformed Threads credentials fail with readable messages.
- X resolution continues to behave exactly as before.

## Task 03: Make Threads review and scheduling flow publisher-aware

### Objective
Replace the static manual-only Threads behavior with config-gated live-publish capability checks.

### Relevant code
- `app/workflows/review_queue.py`
- `app/config/registry.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_storage.py`

### Expected result
- Threads can use schedule or backfill when live publishing is configured.
- Threads falls back to manual handoff when live publishing is not configured.
- LinkedIn stays manual-only.

## Task 04: Carry Threads live jobs through scheduler, API, and console surfaces

### Objective
Make the existing operator surfaces execute and explain the new Threads live path without duplicating publish logic.

### Relevant code
- `app/scheduler/jobs.py`
- `app/api/app.py`
- `app/api/console.py`
- `tests/test_api.py`
- `tests/test_console.py`

### Expected result
- Scheduler can publish due Threads jobs through the resolved publisher path.
- API and console surfaces show Threads live-publish capability when configured.
- Manual upload hints appear only for channels or configs that still require them.

## Task 05: Document token-ready Threads setup and expand regressions

### Objective
Document the operator setup and preserve the shipped Threads live/manual semantics with focused tests.

### Relevant code
- `README.md`
- `docs/operator-console-guide.md`
- `docs/operator-control-plane-api.md`
- `docs/threads-api-publish-readiness-progress-tracker.md`

### Expected result
- Operators can see how to enable Threads live publishing through one env bundle.
- Docs and tests match the actual Threads-live versus LinkedIn-manual behavior.
- The initiative tracker records the shipped result and any deferred follow-up.
