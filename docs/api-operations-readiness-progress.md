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
- Current task: `01_fastapi_application_wiring_and_read_only_history`
- Active status: `in_progress`
- Last updated: `2026-04-06 16:05 KST`
- Active branch: `codex/task-01-fastapi-readonly-history`
- Latest task commit: `none`

## Scope For Current Task
- Goal: `Add a real FastAPI app entrypoint for health and readable run/failure history JSON`
- In scope: `FastAPI app wiring, read-only /health /runs /failures routes, response serialization, and focused API tests`
- Out of scope: `Review action endpoints, article list endpoints, schema migrations, auth, and frontend work`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | FastAPI application wiring and read-only history | in_progress | 2026-04-06 15:57 KST | Implementing minimal FastAPI app wiring with read-only health and run/failure JSON routes |
| 02 | Article and pending-review read endpoints | pending | 2026-04-06 15:53 KST | Intended to expose stored article/enrichment and review-list data for UI use |
| 03 | Review action API parity | pending | 2026-04-06 15:53 KST | Planned API wrappers for approve/reject/edit/schedule using existing review validation |
| 04 | SQLite migration baseline | pending | 2026-04-06 15:53 KST | Planned explicit upgrade path so schema evolution does not require DB recreation |
| 05 | Config readiness guidance and validation | pending | 2026-04-06 15:53 KST | Planned operator-facing checks for sample config and placeholder URLs |
| 06 | Source-specific extraction tuning hooks | pending | 2026-04-06 15:53 KST | Planned additive extraction escape hatches for hard publisher layouts |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `app/api/__init__.py`
- `app/api/app.py`
- `app/workflows/__init__.py`
- `tests/test_api.py`
- `docs/api-operations-readiness-progress.md`

## Progress Log
- `2026-04-06 15:53 KST` Created the API and operations readiness roadmap based on the current repository state after finance-local MVP, all-domain phase 1, and implementation-alignment completion
- `2026-04-06 15:53 KST` Chose a next-stage scope centered on FastAPI surfaces, review API parity, migration baseline, operator config readiness, and extraction tuning because those are the highest-signal gaps still visible in the codebase
- `2026-04-06 15:53 KST` Left all execution tasks in `pending` so future implementation work can start cleanly from Task `01`
- `2026-04-06 15:57 KST` Started Task `01` on branch `codex/task-01-fastapi-readonly-history`
- `2026-04-06 15:57 KST` Chose an additive implementation shape: expose existing healthcheck and history helpers through a thin FastAPI entrypoint with explicit JSON response models
- `2026-04-06 16:01 KST` Added `app.api.create_app()` plus `/health`, `/runs`, and `/failures` routes that delegate to `run_healthcheck`, `list_pipeline_runs`, and `list_pipeline_failures`
- `2026-04-06 16:03 KST` Switched `app.workflows` package exports to lazy resolution so submodule imports for API/history routes do not eagerly load unrelated workflow dependencies
- `2026-04-06 16:05 KST` Added focused API tests covering health readiness JSON plus run and failure history payloads against a temporary SQLite database

## Test Log
- `2026-04-06 15:53 KST` `git diff --check` -> `passed`
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_api.py` -> `passed`
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_history_queries.py` -> `passed`
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k 'healthcheck or history'` -> `passed`
- `2026-04-06 16:05 KST` `git diff --check` -> `passed`

## Blockers
- `None currently`

## Follow-up
- `If Task 02 starts next, reuse the same API app shape and add article/pending-review serializers without introducing new business-logic layers`

## Completion Summary
- `Roadmap docs created: the next implementation stage now has dedicated todo, prompt-pack, and progress-tracking documents in the same format as the recent roadmap sets`
