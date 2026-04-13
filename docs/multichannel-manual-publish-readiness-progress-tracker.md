# Multichannel Manual Publish Readiness Progress Tracker

## Usage
This file is the live implementation tracker for the Multichannel Manual Publish Readiness roadmap.

When an autonomous agent works from `docs/multichannel-manual-publish-readiness-execution-guide.md`, it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when a blocker or stop reason appears,
- when the task is complete.

Keep updates short, factual, and current.

## Generated document naming
When instantiating this template, keep the filename explicit so this file is easy to distinguish from planning or prompt documents.

- Recommended filename: `docs/multichannel-manual-publish-readiness-progress-tracker.md`
- Related files:
  - `docs/multichannel-manual-publish-readiness-vibe-coding-prompt.md`
  - `docs/multichannel-manual-publish-readiness-roadmap.md`
  - `docs/multichannel-manual-publish-readiness-execution-guide.md`

If `Current task` is already marked `in_progress` or `blocked`, resume or resolve that task before picking a new one unless the roadmap was intentionally reprioritized.

## Current Status
- Current milestone: `M2_manual_handoff_workflow`
- Current task: `04_add_manual_publish_outcome_workflow_and_persistence`
- Active status: `done`
- Last updated: `2026-04-13 19:11 KST`
- Base branch: `master`
- Active branch: `codex/task-04-manual-publish-outcome`
- Latest task commit: `self-referential commit SHA cannot be recorded in-band; see git history for the Task 04 workflow commit created after this tracker update`
- Resume decision: `pick_next_task`
- Stop reason: `task_complete`

## Scope For Current Task
- Goal: `Let operators record manual LinkedIn and Threads publish success, failure, or cancellation through supported workflow helpers without changing X scheduler behavior`
- In scope: `Workflow-backed manual outcome helpers, publish-job transition validation, publish-log payloads for operator-visible auditability, and focused workflow/storage/API regression coverage`
- Out of scope: `New API or console controls, direct LinkedIn or Threads integrations, schema redesign, and changes to X live-publish scheduling`
- Dependencies: `Task 03 manual handoff creation is already complete on the parent branch`
- Verification commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_storage.py tests/test_api.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -q`

## Environment Notes
- Required services status: `running (none required beyond local SQLite fixtures)`
- Env or fixture status: `ready (.venv, temp-db fixtures, and test configs are already present)`
- Existing unrelated failures: `none confirmed on this branch after targeted and full-suite verification`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Restore healthcheck and smoke baseline | done | 2026-04-13 18:20 KST | Restored smoke healthcheck expectation, stabilized workflow package exports, and confirmed full `pytest` passes |
| M1 | 02 | Refresh stale roadmap and TODO docs | done | 2026-04-13 18:42 KST | Added historical-status notes to completed initiative roadmaps, pointed related progress docs at this follow-on plan, and fixed stale API readiness commit metadata |
| M2 | 03 | Define non-X manual publish handoff model | done | 2026-04-13 18:56 KST | Approved LinkedIn and Threads drafts now create explicit manual handoff jobs and logs through the shared review workflow, while X scheduling stays unchanged |
| M2 | 04 | Add manual publish outcome workflow and persistence | done | 2026-04-13 19:11 KST | Added workflow-backed non-X handoff completion, failure, and cancellation helpers that reuse the publish-job state machine and publish-log audit trail |
| M3 | 05 | Expose manual handoff controls through API and console | pending | 2026-04-13 18:00 KST | Existing review and publish pages show context but not a full non-X handoff lifecycle |
| M3 | 06 | Document multichannel handoff flow and expand regressions | pending | 2026-04-13 18:00 KST | Operator docs and linked regressions need to reflect the shipped non-X handoff behavior |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `app/workflows/__init__.py`
- `app/workflows/review_queue.py`
- `docs/multichannel-manual-publish-readiness-progress-tracker.md`
- `tests/test_api.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_storage.py`

## Progress Log
- `2026-04-13 18:00 KST` Created the Multichannel Manual Publish Readiness initiative after the previous readiness, control-plane, all-domain, and console initiatives were all found complete but the repository still lacked a clean baseline and a real non-X publish lifecycle.
- `2026-04-13 18:00 KST` Chose a next-stage scope centered on baseline cleanup first, then explicit manual publish handoff support for LinkedIn and Threads, because multichannel drafts already exist while only X has a supported live publish path.
- `2026-04-13 18:00 KST` Left all execution tasks in `pending` so implementation can begin cleanly from Task `01` on a dedicated task branch.
- `2026-04-13 18:13 KST` Created the missing initiative documents on the task branch because they were present on the prior branch context but absent from `master`.
- `2026-04-13 18:13 KST` Reproduced the two baseline failures. `tests/test_operations.py` still expects bundled sample config to mention placeholder URLs even though `config/examples/all_domain_news` now uses live URLs, and `tests/test_scripts.py` still writes a placeholder RSS URL into the smoke config so CLI healthcheck fails by design.
- `2026-04-13 18:16 KST` Corrected the Task `01` diagnosis after switching to `master`. The bundled sample config still intentionally uses placeholder URLs, so no readiness assertion change was needed there; the real stale smoke issue was the placeholder RSS URL and old healthcheck check-count expectation in `tests/test_scripts.py`.
- `2026-04-13 18:18 KST` Broader `pytest` revealed a separate pre-existing full-suite blocker: `app.workflows` could expose `discover_sources` and `enrich_articles` as module objects instead of callables when same-named submodules were imported earlier in the test process.
- `2026-04-13 18:19 KST` Replaced the lazy workflow package export shim with explicit re-exports in `app/workflows/__init__.py`, which restored stable callable imports across the full test suite.
- `2026-04-13 18:30 KST` Fetched the latest `origin/master`, merged it into `codex/task-01-healthcheck-baseline`, and resolved the add/add multichannel doc conflicts by keeping the newer upstream document structure while preserving Task `01` completion state.
- `2026-04-13 18:31 KST` Latest `origin/master` also reintroduced a stale bundled-sample healthcheck expectation in `tests/test_operations.py`; the example config now uses live URLs again, so the assertion was realigned with the current readiness behavior.
- `2026-04-13 18:41 KST` Started Task `02` on `codex/task-02-refresh-roadmap-docs` after confirming the current task branch had no effective diff from `master`, so a clean follow-on docs branch could be created without carrying extra code changes.
- `2026-04-13 18:41 KST` Initial audit found four completed `docs/*todo*.md` files still framed as active implementation roadmaps, and `docs/api-operations-readiness-progress.md` still carried stale commit metadata, so the smallest safe fix is to mark the old initiative docs as historical and point follow-on work at this multichannel roadmap.
- `2026-04-13 18:42 KST` Added minimal historical-status and follow-on sections to the completed API, control-plane, all-domain, and implementation-alignment roadmap docs; matched their related progress docs to the same follow-on reference; and corrected the stale latest-commit metadata in `docs/api-operations-readiness-progress.md`.
- `2026-04-13 18:51 KST` Started Task `03` on `codex/task-03-manual-publish-handoff` after confirming the Task `02` branch was clean enough to fork directly into the next implementation slice.
- `2026-04-13 18:51 KST` Chose approval-time handoff creation as the smallest safe shape: approved `linkedin` and `threads` drafts will create explicit publish-job records with publish-log visibility, while X keeps the existing scheduled live-publish path unchanged.
- `2026-04-13 18:55 KST` Implemented approval-time non-X handoff creation in `app/workflows/review_queue.py` by reusing `publish_jobs` and `publish_logs`, attaching the created `publish_job_id` to the approval audit entry, and blocking scheduled live-publish creation for manual-only channels.
- `2026-04-13 18:56 KST` Added focused workflow, storage, and API regressions proving that unscheduled manual handoff jobs stay out of the due queue while remaining operator-visible through the existing publish-job detail flow.
- `2026-04-13 19:04 KST` Started Task `04` on `codex/task-04-manual-publish-outcome`, branching from the completed Task `03` handoff work because manual outcome recording depends directly on the newly created non-X publish-job records.
- `2026-04-13 19:04 KST` Chose publish-log-backed operator auditability as the smallest safe shape for manual outcomes, so success, failure, and cancellation will reuse the existing publish-job state machine instead of adding new review-action types or schema tables.
- `2026-04-13 19:08 KST` Implemented `complete`, `fail`, and `cancel` manual handoff helpers in `app/workflows/review_queue.py`, reusing `PublishJobRepository.transition_state` and `PublishLogRepository.record` so manual channels can move to terminal states without altering X scheduler behavior.
- `2026-04-13 19:09 KST` Re-exported the new workflow entrypoints from `app/workflows/__init__.py` and added focused workflow, storage, and API regressions for manual publish success, failure, cancellation, unsupported-channel rejection, and publish-job detail visibility.
- `2026-04-13 19:11 KST` Verified the narrow Task `04` regression slices plus `tests/test_scheduler.py`, confirming the shared publish lifecycle remains green after the manual outcome helpers landed.

## Test Log
- `2026-04-13 18:00 KST` `./.venv/bin/pytest -q` -> `pre_existing_failure` `2 failed, 463 passed; current failures are test_run_healthcheck_flags_bundled_sample_config_directory and test_operations_smoke_cli_flow`
- `2026-04-13 18:13 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q` -> `failed` `2 failed, 4 passed; confirmed stale bundled-sample assertion and placeholder-URL smoke fixture`
- `2026-04-13 18:16 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q` -> `passed` `6 passed`
- `2026-04-13 18:16 KST` `./.venv/bin/pytest tests/test_cli.py -k healthcheck -q` -> `passed` `5 passed, 31 deselected`
- `2026-04-13 18:18 KST` `./.venv/bin/pytest -q` -> `failed` `10 failed, 427 passed; discovered package export shadowing in app.workflows`
- `2026-04-13 18:19 KST` `./.venv/bin/pytest tests/test_discover_workflow.py tests/test_enrich_articles_workflow.py -q` -> `passed` `10 passed`
- `2026-04-13 18:19 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py tests/test_cli.py -k healthcheck -q` -> `passed` `7 passed, 35 deselected`
- `2026-04-13 18:20 KST` `./.venv/bin/pytest -q` -> `passed` `437 passed`
- `2026-04-13 18:31 KST` `./.venv/bin/pytest -q` -> `failed` `1 failed, 464 passed; latest master reintroduced a stale bundled-sample expectation in tests/test_operations.py`
- `2026-04-13 18:32 KST` `./.venv/bin/pytest -q` -> `passed` `465 passed`
- `2026-04-13 18:42 KST` `git diff --check` -> `passed`
- `2026-04-13 18:42 KST` `rg -n "Historical|Status Note|Follow-on initiative|multichannel-manual-publish-readiness-roadmap" docs/api-operations-readiness-todo.md docs/operator-control-plane-readiness-todo.md docs/all-domain-news-todo.md docs/implementation-alignment-todo.md docs/api-operations-readiness-progress.md docs/operator-control-plane-readiness-progress.md docs/all-domain-news-progress.md docs/implementation-alignment-progress.md docs/multichannel-manual-publish-readiness-progress-tracker.md` -> `passed`
- `2026-04-13 18:42 KST` `runtime tests` -> `not_run` `docs-only task; verification stayed at planning-doc consistency and diff hygiene`
- `2026-04-13 18:55 KST` `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_storage.py tests/test_api.py tests/test_scheduler.py -q` -> `passed` `112 passed`
- `2026-04-13 18:56 KST` `./.venv/bin/pytest tests/test_console.py -q` -> `passed` `34 passed`
- `2026-04-13 18:56 KST` `git diff --check` -> `passed`
- `2026-04-13 19:07 KST` `./.venv/bin/pytest tests/test_review_queue_workflow.py -q` -> `passed` `24 passed`
- `2026-04-13 19:07 KST` `./.venv/bin/pytest tests/test_storage.py -q` -> `passed` `50 passed`
- `2026-04-13 19:08 KST` `./.venv/bin/pytest tests/test_api.py -q` -> `passed` `30 passed`
- `2026-04-13 19:08 KST` `./.venv/bin/pytest tests/test_scheduler.py -q` -> `passed` `15 passed`
- `2026-04-13 19:11 KST` `git diff --check` -> `passed`

## Open Questions
- `None currently; Task 04 is proceeding with publish logs as the audit surface for manual operator updates`

## Blockers
- `None currently`

## Follow-up
- `If the manual handoff model proves too limiting later, a separate initiative can add direct LinkedIn or Threads platform adapters without reopening this baseline roadmap`

## Completion Summary
- `Task 01 is complete. The smoke CLI fixture now uses a non-placeholder source URL, the healthcheck expectation reflects the current three-check output, and workflow package exports are stable across the full test suite.`
- `Commit 9b614a0 recorded the baseline restoration before the latest master merge started.`
- `Task 02 is complete. Completed roadmap docs now self-identify as historical, related progress docs point future work at the multichannel manual publish readiness roadmap, and the stale API readiness progress metadata no longer shows a pending latest commit.`
- `Task 03 is complete. Approved LinkedIn and Threads drafts now create explicit manual handoff publish-job records and logs through the shared review workflow, the approval response surfaces the linked publish job ID, and manual-only handoff jobs stay out of the scheduled due queue while remaining visible in existing publish-job reads.`
- `Task 04 is complete. Manual LinkedIn and Threads handoff jobs can now be marked published, failed, or cancelled through workflow helpers that preserve the existing publish-job state machine, capture operator identity and outcome context in publish logs, and keep existing publish-job detail surfaces useful without adding new API or console mutation routes yet.`
