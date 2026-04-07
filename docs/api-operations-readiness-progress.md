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
- Current task: `04_sqlite_migration_baseline`
- Active status: `done`
- Last updated: `2026-04-07 11:30 KST`
- Active branch: `codex/task-04-sqlite-migration-baseline`
- Latest task commit: `726f790 Add SQLite schema migration baseline`

## Scope For Current Task
- Goal: `Introduce an explicit SQLite schema upgrade baseline so existing local databases can be upgraded intentionally instead of being recreated`
- In scope: `Migration metadata, legacy schema version detection, additive SQLite upgrade helpers, CLI/script upgrade entrypoints, focused storage/CLI/docs updates, and progress tracking`
- Out of scope: `Auth, frontend work, non-SQLite migration engines, scheduler redesign, and unrelated review/API behavior changes`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | FastAPI application wiring and read-only history | done | 2026-04-06 16:08 KST | FastAPI app entrypoint now exposes read-only `/health`, `/runs`, and `/failures` JSON routes with focused API tests |
| 02 | Article and pending-review read endpoints | done | 2026-04-07 10:55 KST | `/articles` and `/reviews/pending` now expose stored article/enrichment state and pending review drafts with focused API/workflow coverage |
| 03 | Review action API parity | done | 2026-04-07 11:05 KST | Added thin review action routes plus structured HTTP error mapping for approve/reject/edit/schedule without changing review_queue semantics |
| 04 | SQLite migration baseline | done | 2026-04-07 11:30 KST | Added SQLite schema version detection, explicit `db upgrade` flow, operator docs updates, and focused regression coverage for upgrade success and no-op paths |
| 05 | Config readiness guidance and validation | pending | 2026-04-06 15:53 KST | Planned operator-facing checks for sample config and placeholder URLs |
| 06 | Source-specific extraction tuning hooks | pending | 2026-04-06 15:53 KST | Planned additive extraction escape hatches for hard publisher layouts |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `README.md`
- `app/cli.py`
- `app/storage/__init__.py`
- `app/storage/bootstrap.py`
- `docs/all-domain-news-operator-guide.md`
- `docs/api-operations-readiness-progress.md`
- `docs/finance-local-operator-guide.md`
- `scripts/create_db.py`
- `tests/test_cli.py`
- `tests/test_scripts.py`
- `tests/test_storage.py`

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
- `2026-04-07 11:14 KST` Started Task `04` on branch `codex/task-04-sqlite-migration-baseline`
- `2026-04-07 11:14 KST` Chose a modest upgrade shape: keep strict schema validation, add a lightweight schema migration table plus version detection for unversioned SQLite databases, and expose one intentional `db upgrade` path instead of introducing a large migration framework
- `2026-04-07 11:20 KST` Implemented SQLite migration helpers in `app.storage.bootstrap`: fresh `db init` now records schema version metadata, unversioned legacy SQLite files are detected as schema version `1`, and `upgrade_database_schema()` applies additive column/table/index upgrades before validating the final schema
- `2026-04-07 11:21 KST` Added `sns-engine db upgrade` plus `scripts/create_db.py --upgrade` so operators can upgrade intentionally without changing the existing `db init` behavior
- `2026-04-07 11:27 KST` Updated README and operator guides to replace the old “recreate the database” guidance with the new upgrade flow for older local SQLite files
- `2026-04-07 11:28 KST` Added focused storage, CLI, and script coverage for schema version detection, legacy upgrade success, current-schema no-op upgrades, and upgrade-aware healthcheck messaging; broader storage/API/operations regression slices also passed
- `2026-04-07 11:30 KST` Created commit `726f790` with message `Add SQLite schema migration baseline`

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
- `2026-04-07 11:17 KST` `git diff --check` -> `passed`
- `2026-04-07 11:20 KST` `PYTHONPATH=$PWD pytest tests/test_storage.py -k 'schema_version or upgrade_database_schema or bootstrap_database'` -> `passed`
- `2026-04-07 11:20 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k 'healthcheck or db_'` -> `passed`
- `2026-04-07 11:20 KST` `PYTHONPATH=$PWD pytest tests/test_scripts.py -k 'create_db_script'` -> `passed`
- `2026-04-07 11:27 KST` `PYTHONPATH=$PWD pytest tests/test_storage.py` -> `passed`
- `2026-04-07 11:27 KST` `PYTHONPATH=$PWD pytest tests/test_operations.py` -> `passed`
- `2026-04-07 11:27 KST` `PYTHONPATH=$PWD pytest tests/test_api.py` -> `passed`
- `2026-04-07 11:28 KST` `git diff --check` -> `passed`

## Blockers
- `None currently`

## Follow-up
- `Task 05 can build on the same healthcheck surface to make sample-config and placeholder-source readiness more explicit for operators`

## Completion Summary
- `Task 04 complete: local SQLite environments now have an explicit schema version baseline plus intentional `db upgrade` support, allowing older unversioned databases to be upgraded additively instead of being recreated`
