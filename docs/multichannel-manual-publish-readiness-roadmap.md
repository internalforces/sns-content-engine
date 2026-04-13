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

## Current implementation snapshot

### Already implemented
- Config-driven draft generation already supports `x`, `linkedin`, and `threads`, including structured non-X output.
- The repository already has review queue workflows, publish-job persistence, FastAPI operator APIs, and a browser console for review and publish visibility.
- X live publishing already exists behind the config-backed publisher resolver, and approved non-X drafts already show manual upload guidance in the console.
- Task `01` restored the healthcheck smoke baseline and stabilized `app.workflows` exports so same-named workflow entrypoints stay callable during full-suite imports.

### Current limitations relevant to the new goal
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

## Milestones

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

### Milestone M2: Manual Handoff Workflow
- Goal: add the smallest reusable workflow contract for non-X manual publishing without changing X publish semantics
- Includes:
  - explicit non-X manual handoff creation
  - manual publish outcome recording with audit or log visibility

### Milestone M3: Operator Surfacing And Hardening
- Goal: expose the new handoff workflow through supported operator surfaces and lock it down with docs and regressions
- Includes:
  - console and API controls for manual handoff flow
  - operator docs and linked-data regression coverage

## Implementation roadmap

## Phase 1: Baseline Stability

### Task 01: Restore Healthcheck And Smoke Baseline
- Goal: fix the current readiness-related regressions so the repository returns to a clean baseline before new publish work starts
- Actions:
  - inspect the current `config_readiness` behavior in `app/operations.py` and compare it with the failing expectations in `tests/test_operations.py` and `tests/test_scripts.py`
  - align the sample-config expectation and smoke fixture shape with the current readiness policy without weakening the placeholder URL guardrails
  - rerun the focused healthcheck and smoke slices and record the final behavior in the progress tracker
- Verification commands:
  - `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest tests/test_cli.py -k healthcheck -q`
- Done when:
  - the current two readiness-related tests pass
  - the smoke config path no longer treats a placeholder URL as operator-ready
  - `docs/multichannel-manual-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status

### Task 02: Refresh Stale Roadmap And TODO Docs
- Goal: make the planning docs reflect reality so the next implementation stage has one clear active initiative

## Phase 2: Manual Handoff Contract

### Task 03: Define Non-X Manual Publish Handoff Model
- Goal: add the smallest workflow shape that turns approved LinkedIn and Threads drafts into explicit operator-trackable publish work

### Task 04: Add Manual Publish Outcome Workflow And Persistence
- Goal: let operators record manual publish success, failure, or cancellation for non-X channels through supported workflow helpers

## Phase 3: Operator Surfacing And Hardening

### Task 05: Expose Manual Handoff Controls Through API And Console
- Goal: let operators create and complete non-X handoffs through the existing FastAPI and browser console surfaces

### Task 06: Document Multichannel Handoff Flow And Expand Regressions
- Goal: document the shipped X-live versus non-X-manual behavior and protect it with focused regression coverage
