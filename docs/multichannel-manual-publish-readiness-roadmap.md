# Multichannel Manual Publish Readiness Roadmap

## Goal
Extend the current review-first X-live plus structured non-X draft workflow into a multichannel operator publishing workflow that:
- restores a clean readiness and smoke-test baseline before further expansion
- lets approved LinkedIn and Threads drafts enter an explicit manual publish handoff path
- lets operators record manual publish success or failure without direct database access
- preserves the current manual review gate, X live publish behavior, and safe dry-run defaults

## Generated document naming
When instantiating this template, use a filename that clearly shows the document identity.

- Roadmap file: `docs/multichannel-manual-publish-readiness-roadmap.md`
- Execution guide file: `docs/multichannel-manual-publish-readiness-execution-guide.md`
- Progress tracker file: `docs/multichannel-manual-publish-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/multichannel-manual-publish-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `plan.md`, or `notes.md` when multiple initiatives may exist.

## Roadmap construction rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- Define only as many milestones and tasks as are needed to reach the goal while keeping each unit safely implementable.
- Choose task and milestone boundaries so the work can be completed without breaking the existing architecture, workflow semantics, safety gates, or operator experience.
- Prefer the smallest additive slices that reuse the current structure instead of forcing a broad redesign.
- Split a task when it would otherwise span unrelated surfaces, require unclear rollback, or make testing too broad.
- Merge adjacent tiny tasks when they share the same code path, verification surface, and branch scope.
- If the roadmap shape changes during implementation, update this file and `docs/multichannel-manual-publish-readiness-progress-tracker.md` before continuing.

## Current implementation snapshot

### Already implemented
- Config-driven draft generation already supports `x`, `linkedin`, and `threads`, including structured non-X output.
- The repository already has review queue workflows, publish-job persistence, FastAPI operator APIs, and a browser console for review and publish visibility.
- X live publishing already exists behind the config-backed publisher resolver, and approved non-X drafts already show manual upload guidance in the console.

### Current limitations relevant to the new goal
- Two healthcheck-related tests are failing, so the repository does not currently have a clean baseline for the next initiative.
- Several old `docs/*todo*.md` files still describe already-completed work as if it were the active next step.
- Approved LinkedIn and Threads drafts stop at manual upload guidance only; there is no operator-safe workflow to create, complete, or fail a manual publish handoff.
- The current publisher resolver only supports live X publishing, so non-X channels cannot move through a real publish lifecycle without direct DB manipulation or test-only helpers.

## Environment and execution assumptions
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands already available:
  - `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest -q`
- Required local services:
  - `none`
  - `local SQLite files only`
- Required env files, secrets, or fixtures:
  - `.env is optional unless a live provider or live X publish path is being exercised`
  - `tests/fixtures plus temporary SQLite databases are already available in the repository`
- Package install policy: `ask_first`

## Target architecture

### Stability and planning layer
- `baseline_stability`
  - keeps readiness and smoke fixtures aligned with the current operator-ready rules
  - restores a green local test baseline before new workflow changes land
- `initiative_hygiene`
  - marks completed roadmap docs as historical or superseded where needed
  - points the next stage of work at one explicit follow-on initiative

### Manual publish handoff layer
1. An operator approves a non-X draft without bypassing the current review gate.
2. The workflow creates or exposes an explicit manual handoff record using the existing publish job and log model where practical.
3. The operator uploads the content to LinkedIn or Threads outside the app.
4. The operator records the outcome as published, failed, or cancelled through the supported workflow, API, or console surface.
5. Publish visibility, history, and operator docs reflect the exact X-live versus non-X-manual semantics.

## Milestones
Use as many milestone blocks as needed. Keep each milestone small enough to be completed without breaking the current structure or requiring a broad redesign.

### Milestone M1: Stability Baseline
- Goal: restore a clean repository baseline and remove planning drift before adding new publish workflow behavior
- Includes:
  - healthcheck regression cleanup
  - stale roadmap and TODO doc cleanup
- Excludes:
  - new publish workflow behavior
  - live LinkedIn or Threads API integrations
- Verification target:
  - `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest tests/test_cli.py -k healthcheck -q`
- Ship when:
  - the current two readiness-related failures are resolved
  - completed roadmap docs no longer present old work as the active next step

### Milestone M2: Manual Handoff Workflow
- Goal: add the smallest reusable workflow contract for non-X manual publishing without changing X publish semantics
- Includes:
  - explicit non-X manual handoff creation
  - manual publish outcome recording with audit or log visibility
- Excludes:
  - auto-publish for non-X channels
  - auth, multi-user permissions, or scheduler redesign
- Verification target:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_storage.py tests/test_api.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -q`
- Ship when:
  - approved non-X drafts can move into a trackable manual publish lifecycle
  - manual publish completion and failure paths are validated with focused tests

### Milestone M3: Operator Surfacing And Hardening
- Goal: expose the new handoff workflow through supported operator surfaces and lock it down with docs and regressions
- Includes:
  - console and API controls for manual handoff flow
  - operator docs and linked-data regression coverage
- Excludes:
  - frontend redesign beyond the current server-rendered console
  - speculative direct LinkedIn or Threads platform adapters
- Verification target:
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py tests/test_review_queue_workflow.py tests/test_scheduler.py -q`
  - `git diff --check`
- Ship when:
  - operators can complete the intended non-X manual flow without direct DB access
  - docs and tests reflect shipped behavior rather than planned future behavior

## Implementation roadmap

## Phase 1: Baseline Stability

### Task 01: Restore Healthcheck And Smoke Baseline
- Goal: fix the current readiness-related regressions so the repository returns to a clean baseline before new publish work starts
- Actions:
  - inspect the current `config_readiness` behavior in `app/operations.py` and compare it with the failing expectations in `tests/test_operations.py` and `tests/test_scripts.py`
  - align the sample-config expectation and smoke fixture shape with the current readiness policy without weakening the placeholder URL guardrails
  - rerun the focused healthcheck and smoke slices and record the final behavior in the progress tracker
- Dependencies:
  - none
  - none
- Verification commands:
  - `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest tests/test_cli.py -k healthcheck -q`
- Risk or rollback note:
  - keep the runtime readiness policy authoritative; prefer correcting stale tests or smoke fixtures over silently weakening operator-ready validation
- Done when:
  - the current two failing readiness-related tests pass
  - the smoke config path no longer treats a placeholder URL as operator-ready
  - `docs/multichannel-manual-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 02: Refresh Stale Roadmap And TODO Docs
- Goal: make the planning docs reflect reality so the next implementation stage has one clear active initiative
- Actions:
  - audit the completed `docs/*todo*.md` and related progress files for wording that still presents finished work as pending
  - update those docs with factual completion, superseded, or follow-up notes without rewriting implementation history
  - link this initiative from the relevant follow-up sections so the next stage is discoverable
- Dependencies:
  - Task 01
  - none
- Verification commands:
  - `git diff --check`
  - `rg -n "Follow-up|superseded|completed|next initiative" docs`
- Risk or rollback note:
  - keep historical context intact and avoid converting archived initiative docs into a second live roadmap
- Done when:
  - completed roadmap docs no longer advertise finished work as the active next milestone
  - this initiative is the clear follow-on reference where future work should continue
  - `docs/multichannel-manual-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 2: Manual Handoff Contract

### Task 03: Define Non-X Manual Publish Handoff Model
- Goal: add the smallest workflow shape that turns approved LinkedIn and Threads drafts into explicit operator-trackable publish work
- Actions:
  - inspect the approved-draft path in `app/workflows/review_queue.py`, the scheduler and publish-job model in `app/scheduler/jobs.py` and `app/storage/models.py`, and the current manual upload guidance in `app/api/console.py`
  - reuse `publish_jobs` and `publish_logs` where practical instead of inventing a separate table or parallel workflow model
  - introduce a minimal non-X handoff creation path that leaves X scheduling and live publishing semantics unchanged
- Dependencies:
  - Task 01
  - Task 02
- Verification commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_storage.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -q`
- Risk or rollback note:
  - do not auto-create unexpected X jobs or bypass the existing review gate just to make manual channels easier to track
- Done when:
  - approved non-X drafts can move into an explicit handoff state or record that operators can inspect later
  - the new model reuses the current publish-job and log structure unless a clearly documented exception is required
  - `docs/multichannel-manual-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 04: Add Manual Publish Outcome Workflow And Persistence
- Goal: let operators record manual publish success, failure, or cancellation for non-X channels through supported workflow helpers
- Actions:
  - add the smallest workflow helpers needed to mark manual handoffs as published, failed, or cancelled while preserving auditability
  - record meaningful publish-log events, external post IDs, and error messages so the operator surfaces can show useful state later
  - reject invalid channels or state transitions with explicit errors rather than silently coercing them
- Dependencies:
  - Task 03
  - none
- Verification commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_storage.py tests/test_api.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -q`
- Risk or rollback note:
  - preserve the existing publish state machine and publish-log ordering instead of introducing a second lifecycle for manual channels
- Done when:
  - manual channels have workflow-backed success and failure completion paths
  - invalid transition attempts return clear operator-facing failure messages
  - `docs/multichannel-manual-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 3: Operator Surfacing And Hardening

### Task 05: Expose Manual Handoff Controls Through API And Console
- Goal: let operators create and complete non-X handoffs through the existing FastAPI and browser console surfaces
- Actions:
  - add thin API handlers and console actions that reuse the new workflow helpers instead of duplicating business logic in handlers or templates
  - preserve the current manual upload guidance while adding the minimum forms or controls needed to progress the handoff lifecycle
  - surface the resulting states in review and publish-job pages so operators can see where each draft or job stands
- Dependencies:
  - Task 04
  - none
- Verification commands:
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_scheduler.py -q`
- Risk or rollback note:
  - keep the console server-rendered and reuse the existing workflow/API safety rules rather than inventing a new frontend interaction model
- Done when:
  - operators can progress non-X manual handoffs through supported API or console controls
  - X live publish controls and dry-run-safe scheduler behavior remain unchanged
  - `docs/multichannel-manual-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 06: Document Multichannel Handoff Flow And Expand Regressions
- Goal: document the shipped X-live versus non-X-manual behavior and protect it with focused regression coverage
- Actions:
  - update `README.md`, `docs/operator-console-guide.md`, and `docs/operator-control-plane-api.md` so operators can see the exact manual handoff flow
  - add or expand realistic linked-data regression coverage across API, console, review, and publish-job surfaces
  - keep documentation aligned with shipped behavior only, including any limits or intentional non-goals
- Dependencies:
  - Task 05
  - none
- Verification commands:
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py tests/test_review_queue_workflow.py tests/test_scheduler.py -q`
  - `git diff --check`
- Risk or rollback note:
  - avoid documenting speculative direct LinkedIn or Threads integrations that are not actually implemented
- Done when:
  - operator docs clearly describe the manual handoff lifecycle and current safety semantics
  - focused and broader regression slices cover the new manual handoff behavior
  - `docs/multichannel-manual-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Suggested execution order
1. Task 01
2. Task 02
3. Task 03
4. Task 04
5. Task 05
6. Task 06

## Initial milestone recommendation
Start with the smallest milestone that:
- restores the green readiness baseline
- removes stale planning drift
- creates the minimal non-X manual handoff contract without changing X live publish behavior
- can be implemented and verified without breaking the current structure

This keeps the next stage focused on operator-safe multichannel publish handoff before expanding into direct non-X platform integrations or broader console redesign.
