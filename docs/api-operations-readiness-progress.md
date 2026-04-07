# API And Operations Readiness Progress

## Usage
This file is the live implementation tracker for the API and operations readiness roadmap.

When an autonomous agent works from [docs/api-operations-readiness-vibe-prompts.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/api-operations-readiness-vibe-prompts.md), it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when the task is complete.

Keep updates short, factual, and current.

## Current Status
- Current milestone: `phase_1_backend_ready_operator_api`
- Current task: `03_review_action_api_parity`
- Active status: `done`
- Last updated: `2026-04-07 11:05 KST`
- Active branch: `codex/task-03-review-action-api-parity`
- Latest task commit: `recorded in task completion output after commit creation`

## Scope For Current Task
- Goal: `Expose approve/reject/edit/schedule review actions through FastAPI without changing existing review safety semantics`
- In scope: `Thin review action handlers, structured API error responses, focused review action API tests, and progress tracking updates`
- Out of scope: `Schema migrations, auth, scheduler redesign, frontend work, and non-review workflow changes`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | FastAPI application wiring and read-only history | done | 2026-04-06 16:08 KST | FastAPI app entrypoint now exposes read-only `/health`, `/runs`, and `/failures` JSON routes with focused API tests |
| 02 | Article and pending-review read endpoints | done | 2026-04-07 10:55 KST | `/articles` and `/reviews/pending` now expose stored article/enrichment state and pending review drafts with focused API/workflow coverage |
| 03 | Review action API parity | done | 2026-04-07 11:05 KST | Added thin review action routes plus structured HTTP error mapping for approve/reject/edit/schedule without changing review_queue semantics |
| 04 | SQLite migration baseline | pending | 2026-04-06 15:53 KST | Planned explicit upgrade path so schema evolution does not require DB recreation |
| 05 | Config readiness guidance and validation | pending | 2026-04-06 15:53 KST | Planned operator-facing checks for sample config and placeholder URLs |
| 06 | Source-specific extraction tuning hooks | pending | 2026-04-06 15:53 KST | Planned additive extraction escape hatches for hard publisher layouts |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `app/api/app.py`
- `docs/api-operations-readiness-progress.md`
- `tests/test_api.py`

## Progress Log
- `2026-04-06 15:53 KST` Created the API and operations readiness roadmap based on the current repository state after finance-local MVP, all-domain phase 1, and implementation-alignment completion
- `2026-04-06 15:53 KST` Chose a next-stage scope centered on FastAPI surfaces, review API parity, migration baseline, operator config readiness, and extraction tuning because those are the highest-signal gaps still visible in the codebase
- `2026-04-06 15:53 KST` Left all execution tasks in `pending` so future implementation work can start cleanly from Task `01`
- `2026-04-06 15:57 KST` Started Task `01` on branch `codex/task-01-fastapi-readonly-history`
- `2026-04-06 15:57 KST` Chose an additive implementation shape: expose existing healthcheck and history helpers through a thin FastAPI entrypoint with explicit JSON response models
- `2026-04-06 16:01 KST` Added `app.api.create_app()` plus `/health`, `/runs`, and `/failures` routes that delegate to `run_healthcheck`, `list_pipeline_runs`, and `list_pipeline_failures`
- `2026-04-06 16:03 KST` Switched `app.workflows` package exports to lazy resolution so submodule imports for API/history routes do not eagerly load unrelated workflow dependencies
- `2026-04-06 16:05 KST` Added focused API tests covering health readiness JSON plus run and failure history payloads against a temporary SQLite database
- `2026-04-06 16:08 KST` Created commit `9996312` with message `Add FastAPI app with health and history routes`
- `2026-04-07 10:48 KST` Started Task `02` on branch `codex/task-02-article-review-read-endpoints`
- `2026-04-07 10:48 KST` Chose a thin additive shape: add one read-only article status query helper, reuse `list_pending_review_drafts` directly, and keep the FastAPI handlers as serialization-only wrappers
- `2026-04-07 10:53 KST` Added `list_article_statuses` in `app.workflows.history_queries` so `/articles` can expose source-item plus enrichment state without duplicating review or enrichment business logic
- `2026-04-07 10:53 KST` Extended the FastAPI app with `/articles` and `/reviews/pending`, keeping handlers thin and serializing existing workflow/query results into stable JSON payloads
- `2026-04-07 10:53 KST` Added focused workflow and API tests for article status rows, pending-review reads, and both empty-state responses
- `2026-04-07 10:55 KST` Created commit `af98e06` with message `Add article and pending-review read endpoints`
- `2026-04-07 10:59 KST` Started Task `03` on branch `codex/task-03-review-action-api-parity`
- `2026-04-07 10:59 KST` Chose the smallest additive shape: keep review mutations in `app.workflows.review_queue`, add thin FastAPI action routes, and map workflow/schema errors into structured HTTP responses instead of duplicating validation logic
- `2026-04-07 11:02 KST` Added POST `/reviews/{draft_id}/approve|reject|edit|schedule` handlers that call the existing review queue helpers and serialize `ReviewDraftResult` into stable JSON responses
- `2026-04-07 11:03 KST` Added structured API error handling for missing drafts, invalid review states, draft validation failures, schedule conflicts, config errors, and database schema readiness failures
- `2026-04-07 11:04 KST` Extended `tests/test_api.py` with focused review action coverage for all four success paths plus representative `404`, `409`, and `422` error responses

## Test Log
- `2026-04-06 15:53 KST` `git diff --check` -> `passed`
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_api.py` -> `passed`
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_history_queries.py` -> `passed`
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k 'healthcheck or history'` -> `passed`
- `2026-04-06 16:05 KST` `git diff --check` -> `passed`
- `2026-04-07 10:53 KST` `git diff --check` -> `passed`
- `2026-04-07 10:53 KST` `PYTHONPATH=$PWD pytest tests/test_history_queries.py` -> `passed`
- `2026-04-07 10:53 KST` `PYTHONPATH=$PWD pytest tests/test_api.py` -> `passed`
- `2026-04-07 10:53 KST` `PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py -k list_pending_review_drafts` -> `passed`
- `2026-04-07 10:53 KST` `git diff --check` -> `passed`
- `2026-04-07 11:03 KST` `git diff --check` -> `passed`
- `2026-04-07 11:04 KST` `PYTHONPATH=$PWD pytest tests/test_api.py` -> `passed`
- `2026-04-07 11:04 KST` `PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py` -> `passed`
- `2026-04-07 11:05 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k 'test_review_'` -> `passed`

## Blockers
- `None currently`

## Follow-up
- `Task 04 can add migration-aware startup checks to the same API surface without revisiting the review action contract`

## Completion Summary
- `Task 03 complete: the FastAPI operator surface now exposes approve/reject/edit/schedule review mutations with structured JSON responses and explicit HTTP error mapping while preserving the existing review_queue validation path`
