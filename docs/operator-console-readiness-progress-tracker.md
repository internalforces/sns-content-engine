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
- Current milestone: `M1_read_only_console_foundation`
- Current task: `03_article_status_and_pending_review_queue_pages`
- Active status: `done`
- Last updated: `2026-04-09 13:57 KST`
- Base branch: `codex/task-02-console-dashboard`
- Active branch: `codex/task-03-console-queues`
- Latest task commit: `pending_commit_creation`
- Resume decision: `pick_next_task`
- Stop reason: `none`

## Scope For Current Task
- Goal: `Render article status rows and pending-review queue data in browser pages that stay aligned with the current operator data contract`
- In scope: `Read-only article status and pending-review pages, thin reuse of history and review-queue helpers, focused browser coverage for empty and populated states`
- Out of scope: `Review detail, review mutations, publish-job pages, scheduler controls, auth, and any separate frontend build stack`
- Dependencies: `Task 01 console shell, Task 02 dashboard wiring, app/workflows/history_queries.py, and app/workflows/review_queue.py`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -k "articles or pending_review"`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_review_queue_workflow.py -k "articles or pending_review"`

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
| M2 | 04 | Review draft detail page | pending | 2026-04-08 17:40 KST | Reuse the current operator-ready review detail contract in one browser page |
| M2 | 05 | Review action forms and safe mutation feedback | pending | 2026-04-08 17:40 KST | Keep browser mutations routed through existing review validation |
| M3 | 06 | Publish job list and detail pages | pending | 2026-04-08 17:40 KST | Surface publish queue visibility before adding more browser actions |
| M3 | 07 | Scheduler action console with safe defaults | pending | 2026-04-08 17:40 KST | Dry-run publish remains the default browser action path |
| M3 | 08 | Console operator docs and browser-facing regression coverage | pending | 2026-04-08 17:40 KST | Document the console only after the shipped browser surface exists |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `docs/operator-console-readiness-progress-tracker.md`
- `app/api/app.py`
- `app/api/console.py`
- `app/api/templates/console/index.html`
- `app/api/templates/console/articles.html`
- `app/api/templates/console/pending_review.html`
- `tests/test_console.py`

## Progress Log
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

## Open Questions
- `Should the first console stay fully server-rendered for all interactions, or should later tasks allow small progressive-enhancement fetch calls while still avoiding a separate SPA?`

## Blockers
- `None currently`

## Follow-up
- `Task 04 can now reuse the live pending-review page and shared console context to add one draft-detail browser workspace without revisiting article or queue list wiring`

## Completion Summary
- `Task 01 complete: the FastAPI app now serves a dedicated `/console` namespace with a canonical landing page, shared Jinja layout, and mounted static assets for future browser surfaces`
- `Task 01 complete: focused browser coverage now protects the console redirect, landing-page rendering, and static asset delivery while shared API regression confirms existing operator routes still behave as before`
- `Task 02 complete: the console now exposes `/console/dashboard` with recent pipeline runs, technical failures, and policy skips rendered through the same history query helpers that power the operator API`
- `Task 02 complete: focused browser coverage now protects empty and populated dashboard states while shared history-query and API regression confirms the linked run/failure data path still behaves as expected`
- `Task 03 complete: the console now exposes `/console/articles` and `/console/reviews/pending` so operators can browse stored article status and current manual-review workload without shell access`
- `Task 03 complete: focused browser coverage protects empty and populated article and pending-review states while shared API, review-workflow, and full-console regression slices confirm the reused data paths still behave as expected`
