# Operator Console Readiness Progress Tracker

## Usage
This file is the live implementation tracker for the Operator Console Readiness roadmap.

When an autonomous agent works from `docs/operator-console-readiness-execution-guide.md`, it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when a blocker or stop reason appears,
- when the task is complete.

Keep updates short, factual, and current.

## Generated document naming
When instantiating this template, keep the filename explicit so this file is easy to distinguish from planning or prompt documents.

- Recommended filename: `docs/operator-console-readiness-progress-tracker.md`
- Related files:
  - `docs/operator-console-readiness-roadmap.md`
  - `docs/operator-console-readiness-execution-guide.md`

If `Current task` is already marked `in_progress` or `blocked`, resume or resolve that task before picking a new one unless the roadmap was intentionally reprioritized.

## Current Status
- Current milestone: `M3_publish_and_scheduler_controls`
- Current task: `08_console_operator_docs_and_browser_facing_regression_coverage`
- Active status: `done`
- Last updated: `2026-04-09 15:16 KST`
- Base branch: `codex/task-07-scheduler-console`
- Active branch: `codex/task-08-console-docs`
- Latest task commit: `3c2403e`
- Resume decision: `pick_next_task`
- Stop reason: `none`

## Scope For Current Task
- Goal: `Document the shipped operator console and add browser-facing regression coverage that protects its linked read and action flows`
- In scope: `One concise console operator guide, README guide-link updates, a realistic linked-fixture console regression sweep, and tracker updates for shipped console usage plus safety expectations`
- Out of scope: `New browser features, auth, SPA work, background refresh, or any change to manual-review and publish safety semantics`
- Dependencies: `Tasks 01 through 07, current console routes/templates/tests, README operator guide links, and existing API safety documentation`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py tests/test_review_queue_workflow.py`

## Environment Notes
- Required services status: `running (none required beyond local SQLite fixtures)`
- Env or fixture status: `ready (config/ and SQLite-backed test fixtures already exist)`
- Existing unrelated failures: `none known`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Console shell and template infrastructure | done | 2026-04-08 18:32 KST | Added a FastAPI-served console shell with shared templates, mounted static assets, and passing focused browser coverage on `codex/task-01-console-shell` |
| M1 | 02 | Run overview and failure dashboard pages | done | 2026-04-09 12:34 KST | Added `/console/dashboard` with recent run history, readable failures, policy skips, and passing focused browser plus shared query/API regression coverage on `codex/task-02-console-dashboard` |
| M1 | 03 | Article status and pending-review queue pages | done | 2026-04-09 13:57 KST | Added `/console/articles` and `/console/reviews/pending` with shared helper reuse, live navigation links, and focused console plus API/workflow regression coverage on `codex/task-03-console-queues` |
| M2 | 04 | Review draft detail page | done | 2026-04-09 14:09 KST | Added `/console/reviews/{draft_id}` with queue-to-detail links, browser-friendly not-found handling, and focused console plus shared review regression coverage on `codex/task-04-review-detail-console` |
| M2 | 05 | Review action forms and safe mutation feedback | done | 2026-04-09 14:29 KST | Added browser approve, reject, edit, and schedule actions with inline workflow feedback on `codex/task-05-review-action-console` |
| M3 | 06 | Publish job list and detail pages | done | 2026-04-09 14:44 KST | Added `/console/publish-jobs` and `/console/publish-jobs/{publish_job_id}` with focused browser coverage on `codex/task-06-publish-job-console` |
| M3 | 07 | Scheduler action console with safe defaults | done | 2026-04-09 15:00 KST | Added `/console/scheduler` with discover, backfill, and explicit live-opt-in publish-due actions plus focused console coverage on `codex/task-07-scheduler-console` |
| M3 | 08 | Console operator docs and browser-facing regression coverage | done | 2026-04-09 15:16 KST | Added a shipped-console operator guide, README link updates, and linked browser regressions on `codex/task-08-console-docs` in commit `3c2403e` |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `README.md`
- `docs/operator-console-guide.md`
- `docs/operator-console-readiness-progress-tracker.md`
- `tests/test_console.py`

## Progress Log
- `2026-04-09 15:16 KST` Committed Task `08` as `3c2403e` (`Document operator console and expand browser regression coverage`) after the full console suite, broader API/review/scheduler regression slice, and `git diff --check` passed
- `2026-04-09 15:15 KST` Added a dedicated `docs/operator-console-guide.md` reference plus a README guide link that documents how to start the shipped FastAPI console locally, open it with `config_dir` and `database_url`, and restates manual-review plus dry-run publish safety in browser terms
- `2026-04-09 15:16 KST` Expanded `tests/test_console.py` with linked-fixture browser regressions that cover the shipped read-only console routes together and the approve-to-schedule-to-publish-visibility flow alongside the default dry-run scheduler action path
- `2026-04-09 15:07 KST` Started Task `08` on `codex/task-08-console-docs`; keeping scope to one concise console operator guide, README guide-link updates, and realistic linked-fixture browser regression coverage now that the shipped console surface exists
- `2026-04-09 15:00 KST` Committed Task `07` as `50abe01` (`Expose scheduler controls in operator console`) after focused scheduler console coverage, scheduler API regression slices, and a full console regression run passed
- `2026-04-09 14:56 KST` Added `/console/scheduler` with POST-backed discover, backfill, and publish-due controls, kept the route thin by reusing the existing scheduler runners from app state, and made live publish an explicit checkbox opt-in while dry-run remains the default path
- `2026-04-09 14:58 KST` Added focused browser tests for scheduler summaries and publish-due mode wiring, then verified the page against focused scheduler console coverage, scheduler API regression slices, and a full console regression run
- `2026-04-09 14:50 KST` Started Task `07` on `codex/task-07-scheduler-console`; keeping scope to one scheduler control page that reuses the existing discover, backfill, and publish-due runners with dry-run publish as the obvious default and explicit live opt-in
- `2026-04-08 17:40 KST` Created the operator console readiness roadmap, execution guide, and progress tracker after confirming the backend control-plane roadmap is complete and no frontend stack exists in the repository
- `2026-04-08 17:40 KST` Chose a FastAPI plus Jinja2 server-rendered console as the smallest next stage because the operator API is already in place and `jinja2` is already a project dependency
- `2026-04-08 17:40 KST` Left all implementation tasks in `pending` and set Task `01` as the next recommended work item so implementation can begin from the browser shell
- `2026-04-08 18:26 KST` Started Task `01` on `codex/task-01-console-shell`; keeping scope to additive console route wiring, shared templates, lightweight static assets, and focused shell tests
- `2026-04-08 18:34 KST` Added a dedicated `app.api.console` module with a `/console` redirect, `/console/` landing page, shared Jinja template shell, mounted static assets, and focused console-shell tests so later page tasks can extend one browser entrypoint
- `2026-04-08 18:31 KST` Verified the new console shell against focused browser coverage plus a small API regression slice to confirm the shared FastAPI app wiring still serves health, runs, failures, and article endpoints unchanged
- `2026-04-08 18:32 KST` Committed Task `01` as `2e373ce` (`Add operator console shell`) after the focused console coverage and shared API regression slice passed
- `2026-04-09 12:22 KST` Started Task `02` on `codex/task-02-console-dashboard`; keeping scope to one dashboard page that reuses existing history-query helpers for recent runs, failures, and policy skips without changing API semantics
- `2026-04-09 12:28 KST` Added a dedicated `/console/dashboard` page, wired the console shell to shared run/failure listers through FastAPI app state, and shaped one read-only dashboard template with recent-run, failure, and policy-skip sections plus focused browser tests for empty and populated states
- `2026-04-09 12:34 KST` Committed Task `02` as `06ed520` (`Add operator console dashboard`) after focused browser coverage and the shared runs/failures regression slice passed
- `2026-04-09 13:51 KST` Started Task `03` on `codex/task-03-console-queues`; keeping scope to two read-only list pages that reuse existing article-status and pending-review helpers with focused console coverage for empty and populated states
- `2026-04-09 13:56 KST` Added `/console/articles` and `/console/reviews/pending`, promoted the Task 03 navigation entries to live links, and shaped matching Jinja tables plus focused console tests without changing the underlying API or workflow helper contracts
- `2026-04-09 13:57 KST` Verified the new read-only list pages with focused console coverage, shared API and review-workflow regression slices, and a full console navigation regression run after reusing the existing article-status and pending-review helpers
- `2026-04-09 14:02 KST` Started Task `04` on `codex/task-04-review-detail-console`; keeping scope to one browser draft-detail page, a queue-to-detail entry path, and focused console coverage for populated and not-found states
- `2026-04-09 14:05 KST` Added a dedicated `/console/reviews/{draft_id}` page, linked queue rows into the detail workspace, and kept the read path thin by reusing the existing review-detail helper plus a browser-friendly 404 template path
- `2026-04-09 14:09 KST` Verified the detail page against populated and not-found browser states, shared API/workflow review-detail regressions, and a wider console navigation slice after linking pending-review rows into the new workspace
- `2026-04-09 14:20 KST` Started Task `05` on `codex/task-05-review-action-console`; keeping scope to server-rendered approve, reject, edit, and schedule actions that reuse the current review_queue validation and conflict semantics without adding client-side state management
- `2026-04-09 14:24 KST` Added a POST-backed review action flow on `/console/reviews/{draft_id}`, reusing the existing review_queue mutation helpers and rendering workflow-aligned success or error feedback directly in the draft workspace without introducing a second data path
- `2026-04-09 14:25 KST` Expanded the review detail template and console stylesheet with state-aware action cards so pending drafts expose approve/reject/edit while approved drafts expose scheduling with browser-readable guardrail messaging
- `2026-04-09 14:27 KST` Added focused console browser tests covering approve, reject, edit, and schedule success plus approval-validation and schedule-conflict feedback to keep the new mutation surface aligned with the existing review workflow rules
- `2026-04-09 14:29 KST` Committed Task `05` as `a8e4842` (`Add browser review action console`) after focused console review-action coverage plus shared API/workflow and console regression slices passed
- `2026-04-09 14:33 KST` Started Task `06` on `codex/task-06-publish-job-console`; keeping scope to read-only publish-job list and detail pages that reuse the existing history-query helpers, show linked draft context and publish logs, and add focused console coverage before any scheduler controls
- `2026-04-09 14:42 KST` Added `/console/publish-jobs` and `/console/publish-jobs/{publish_job_id}` with shared publish-job list/detail helpers, promoted the navigation entry to a live link, and linked review audit publish-job references into the new browser detail path without introducing new mutation flows
- `2026-04-09 14:44 KST` Verified the new publish-job browser surfaces with focused console coverage, shared publish-job API regression slices, and a full console regression run after wiring publish-job detail links from the review workspace
- `2026-04-09 14:44 KST` Committed Task `06` as `a123778` (`Add browser publish job console`) after focused browser publish-job coverage plus shared API and full-console regression slices passed

## Test Log
- `2026-04-08 17:44 KST` `git diff --check` -> `passed`
- `2026-04-08 18:30 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "console_shell"` -> `passed`
- `2026-04-08 18:30 KST` `PYTHONPATH=$PWD pytest tests/test_api.py -k "health"` -> `passed`
- `2026-04-08 18:31 KST` `PYTHONPATH=$PWD pytest tests/test_api.py -k "runs or failures or articles"` -> `passed`
- `2026-04-08 18:31 KST` `git diff --check` -> `passed`
- `2026-04-09 12:29 KST` `PYTHONPATH=$PWD python -m compileall app/api tests/test_console.py` -> `passed`
- `2026-04-09 12:30 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "dashboard"` -> `failed` (`policy_mode_counts` are rendered in deterministic sorted order on the dashboard, so the populated-state assertion expected the wrong label order; updated the assertion and reran)
- `2026-04-09 12:31 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "dashboard"` -> `passed`
- `2026-04-09 12:32 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "console_shell or dashboard"` -> `passed`
- `2026-04-09 12:33 KST` `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_api.py -k "runs or failures"` -> `passed`
- `2026-04-09 12:33 KST` `git diff --check` -> `passed`
- `2026-04-09 13:56 KST` `PYTHONPATH=$PWD python -m compileall app/api tests/test_console.py` -> `passed`
- `2026-04-09 13:56 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "articles or pending_review"` -> `passed`
- `2026-04-09 13:57 KST` `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_review_queue_workflow.py -k "articles or pending_review"` -> `passed`
- `2026-04-09 13:57 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "console_shell or dashboard or articles or pending_review"` -> `passed`
- `2026-04-09 13:57 KST` `git diff --check` -> `passed`
- `2026-04-09 14:05 KST` `PYTHONPATH=$PWD python -m compileall app/api tests/test_console.py` -> `passed`
- `2026-04-09 14:06 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "review_detail"` -> `failed` (`schedule_draft` validation rejected the populated-state fixture because the edited draft body was missing required attribution for an attributed source; updated the fixture text and reran)
- `2026-04-09 14:07 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "review_detail"` -> `passed`
- `2026-04-09 14:08 KST` `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_review_queue_workflow.py -k "review_detail"` -> `passed`
- `2026-04-09 14:08 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "pending_review or review_detail"` -> `passed`
- `2026-04-09 14:09 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "console_shell or dashboard or articles or pending_review or review_detail"` -> `passed`
- `2026-04-09 14:08 KST` `git diff --check` -> `passed`
- `2026-04-09 14:25 KST` `PYTHONPATH=$PWD python -m compileall app/api tests/test_console.py` -> `passed`
- `2026-04-09 14:26 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "review_actions"` -> `passed`
- `2026-04-09 14:27 KST` `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_review_queue_workflow.py -k "approve or reject or edit or schedule"` -> `passed`
- `2026-04-09 14:27 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "pending_review or review_detail or review_actions"` -> `passed`
- `2026-04-09 14:27 KST` `git diff --check` -> `passed`
- `2026-04-09 14:42 KST` `PYTHONPATH=$PWD python -m compileall app/api tests/test_console.py` -> `passed`
- `2026-04-09 14:42 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "publish_jobs"` -> `passed`
- `2026-04-09 14:42 KST` `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py -k "publish_jobs or publish_job_detail"` -> `passed`
- `2026-04-09 14:43 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "console_shell or dashboard or articles or pending_review or review_detail or review_actions or publish_jobs"` -> `passed`
- `2026-04-09 14:43 KST` `git diff --check` -> `passed`
- `2026-04-09 14:52 KST` `PYTHONPATH=$PWD python -m compileall app/api tests/test_console.py` -> `passed`
- `2026-04-09 14:54 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "scheduler_actions"` -> `passed`
- `2026-04-09 14:55 KST` `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py -k "scheduler_discover_endpoint or scheduler_backfill_endpoint or scheduler_publish_due_endpoint"` -> `passed`
- `2026-04-09 14:57 KST` `PYTHONPATH=$PWD pytest tests/test_console.py` -> `passed`
- `2026-04-09 14:58 KST` `git diff --check` -> `passed`
- `2026-04-09 15:17 KST` `PYTHONPATH=$PWD pytest tests/test_console.py -k "linked_operator_context or mutation_flow"` -> `passed`
- `2026-04-09 15:18 KST` `PYTHONPATH=$PWD pytest tests/test_console.py` -> `passed`
- `2026-04-09 15:18 KST` `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py tests/test_review_queue_workflow.py` -> `passed`
- `2026-04-09 15:18 KST` `git diff --check` -> `passed`

## Open Questions
- `Should the first console stay fully server-rendered for all interactions, or should later tasks allow small progressive-enhancement fetch calls while still avoiding a separate SPA?`

## Blockers
- `None currently`

## Follow-up
- `Operator console readiness roadmap tasks 01 through 08 are complete; any further browser enhancements should be scoped as a new roadmap item instead of extending this finished slice`

## Completion Summary
- `Task 01 complete: the FastAPI app now serves a dedicated `/console` namespace with a canonical landing page, shared Jinja layout, and mounted static assets for future browser surfaces`
- `Task 01 complete: focused browser coverage now protects the console redirect, landing-page rendering, and static asset delivery while shared API regression confirms existing operator routes still behave as before`
- `Task 02 complete: the console now exposes `/console/dashboard` with recent pipeline runs, technical failures, and policy skips rendered through the same history query helpers that power the operator API`
- `Task 02 complete: focused browser coverage now protects empty and populated dashboard states while shared history-query and API regression confirms the linked run/failure data path still behaves as expected`
- `Task 03 complete: the console now exposes `/console/articles` and `/console/reviews/pending` so operators can browse stored article status and current manual-review workload without shell access`
- `Task 03 complete: focused browser coverage protects empty and populated article and pending-review states while shared API, review-workflow, and full-console regression slices confirm the reused data paths still behave as expected`
- `Task 04 complete: the console now exposes `/console/reviews/{draft_id}` so operators can inspect one draft's body, provenance, brief, source-item, enrichment, audit history, and sibling variants from the browser`
- `Task 04 complete: focused browser coverage protects populated and not-found detail states while shared review-detail regressions and a full console slice confirm the queue-to-detail path stays aligned with the current API and workflow helper behavior`
- `Task 05 complete: the review workspace now exposes browser approve, reject, edit, and schedule actions that call the same review_queue helpers and preserve the existing validation, state-conflict, and scheduling guardrails`
- `Task 05 complete: focused console browser coverage protects all four action paths plus representative validation/conflict feedback while shared API/workflow regressions confirm the mutation semantics still match the existing operator surfaces`
- `Task 06 complete: the console now exposes `/console/publish-jobs` and `/console/publish-jobs/{publish_job_id}` so operators can inspect queued, published, and failed jobs without leaving the browser`
- `Task 06 complete: focused publish-job browser coverage plus shared API and full-console regression slices confirm the new read-only publish visibility stays aligned with the existing history-query contracts and review workspace links`
- `Task 07 complete: the console now exposes `/console/scheduler` so operators can trigger discover, backfill, and publish-due runs from the browser without shell access`
- `Task 07 complete: focused scheduler browser coverage plus shared scheduler API regressions and a full console slice confirm dry-run stays the default browser path while live publish still requires explicit opt-in`
- `Task 08 complete: the repository now includes one dedicated operator console guide that explains local startup, context query parameters, main pages, and the browser safety model without drifting from shipped behavior`
- `Task 08 complete: linked browser-facing regressions now cover the shared read-only console context plus the approve-to-schedule-to-publish visibility flow while keeping the default scheduler publish path in dry-run mode`
