# API And Operations Readiness Progress

## Usage
This file is the live implementation tracker for the API and operations readiness roadmap.

When an autonomous agent works from [docs/api-operations-readiness-vibe-prompts.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/api-operations-readiness-vibe-prompts.md), it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when the task is complete.

Keep updates short, factual, and current.

## Status Note
- This tracker is complete and kept as historical context.
- Active follow-on publish workflow work now lives in `docs/multichannel-manual-publish-readiness-roadmap.md`.

## Current Status
- Current milestone: `phase_1_backend_ready_operator_api`
- Current task: `06_source_specific_extraction_tuning_hooks`
- Active status: `done`
- Last updated: `2026-04-07 13:47 KST`
- Active branch: `codex/task-06-source-extraction-hooks`
- Latest task commit: `01398ea`

## Scope For Current Task
- Goal: `Add a small source-specific extraction override path so hard publisher layouts can be tuned without redesigning enrichment`
- In scope: `Source-level extraction config schema, default extractor hook-up through enrich_articles, focused extractor/config/workflow coverage, and progress tracking`
- Out of scope: `Auth, frontend work, scraper subsystem redesign, connector changes, and unrelated review or scheduler behavior`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | FastAPI application wiring and read-only history | done | 2026-04-06 16:08 KST | FastAPI app entrypoint now exposes read-only `/health`, `/runs`, and `/failures` JSON routes with focused API tests |
| 02 | Article and pending-review read endpoints | done | 2026-04-07 10:55 KST | `/articles` and `/reviews/pending` now expose stored article/enrichment state and pending review drafts with focused API/workflow coverage |
| 03 | Review action API parity | done | 2026-04-07 11:05 KST | Added thin review action routes plus structured HTTP error mapping for approve/reject/edit/schedule without changing review_queue semantics |
| 04 | SQLite migration baseline | done | 2026-04-07 11:30 KST | Added SQLite schema version detection, explicit `db upgrade` flow, operator docs updates, and focused regression coverage for upgrade success and no-op paths |
| 05 | Config readiness guidance and validation | done | 2026-04-07 11:42 KST | `healthcheck` now fails fast on bundled sample config dirs and placeholder example.* URLs, with focused CLI/API/operations coverage and updated README guidance |
| 06 | Source-specific extraction tuning hooks | done | 2026-04-07 13:47 KST | Added opt-in source extraction selectors and per-source minimum word count overrides in the default enrichment path |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `app/config/__init__.py`
- `app/config/schemas.py`
- `app/domain/extraction_selectors.py`
- `app/services/article_extractor.py`
- `app/workflows/enrich_articles.py`
- `config/examples/all_domain_news/sources.yaml`
- `docs/api-operations-readiness-progress.md`
- `tests/test_article_extractor.py`
- `tests/test_config.py`
- `tests/test_enrich_articles_workflow.py`

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
- `2026-04-07 11:35 KST` Started Task `05` on branch `codex/task-05-config-readiness-validation`
- `2026-04-07 11:35 KST` Chose the smallest additive shape: keep config loading strict, add healthcheck-side readiness checks for bundled sample directories and placeholder URLs, and update docs/tests around the clearer operator guidance
- `2026-04-07 11:39 KST` Added a dedicated `config_readiness` healthcheck step in `app.operations`, failing fast when `--config-dir` points at bundled `config/examples/...` content or when placeholder `example.*` URLs remain in landing/source config fields
- `2026-04-07 11:39 KST` Updated focused CLI/API/operations tests and README guidance so the new operator-readiness behavior is covered and documented alongside the existing schema healthcheck flow
- `2026-04-07 11:40 KST` Targeted regression checks passed for the new readiness behavior across operations, CLI healthcheck output, and the FastAPI health endpoint; the broader API/CLI regression slice also passed without behavioral drift
- `2026-04-07 11:42 KST` Created commit `74e7c19` with message `Improve healthcheck config readiness guidance`
- `2026-04-07 13:36 KST` Started Task `06` on branch `codex/task-06-source-extraction-hooks`
- `2026-04-07 13:36 KST` Chose a small additive shape: add opt-in source extraction selectors to `sources.yaml`, build default extractor overrides from `config_dir`, and keep custom injected extractors working unchanged in tests
- `2026-04-07 13:47 KST` Added `SourceExtractionConfig` to source schemas plus a shared limited-selector validator so `sources.yaml` can define opt-in preferred/excluded extraction scopes and per-source minimum word counts
- `2026-04-07 13:47 KST` Extended `ArticleExtractor` with limited selector-aware preferred/excluded scope handling and wired `enrich_articles` to build cached default extractors per `source_key` from `sources.yaml` without changing injected custom extractor behavior
- `2026-04-07 13:47 KST` Added focused extractor/config/workflow coverage plus a sample extraction override in the all-domain example sources config to document the new hook shape

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
- `2026-04-07 11:39 KST` `git diff --check` -> `passed`
- `2026-04-07 11:39 KST` `PYTHONPATH=$PWD pytest tests/test_operations.py` -> `passed`
- `2026-04-07 11:39 KST` `PYTHONPATH=$PWD pytest tests/test_api.py -k health` -> `passed`
- `2026-04-07 11:39 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k healthcheck` -> `passed`
- `2026-04-07 11:40 KST` `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_cli.py` -> `passed`
- `2026-04-07 13:45 KST` `git diff --check` -> `passed`
- `2026-04-07 13:45 KST` `PYTHONPATH=$PWD pytest tests/test_article_extractor.py` -> `passed`
- `2026-04-07 13:46 KST` `PYTHONPATH=$PWD pytest tests/test_config.py -k extraction` -> `passed`
- `2026-04-07 13:46 KST` `PYTHONPATH=$PWD pytest tests/test_enrich_articles_workflow.py -k source_specific_extraction_rules_with_default_extractor` -> `passed`
- `2026-04-07 13:47 KST` `PYTHONPATH=$PWD pytest tests/test_article_extractor.py tests/test_enrich_articles_workflow.py tests/test_run_local_pipeline_workflow.py tests/test_config.py` -> `passed`

## Blockers
- `None currently`

## Follow-up
- `This initiative is complete; current follow-on operator publish-lifecycle work continues in docs/multichannel-manual-publish-readiness-roadmap.md`
- `Current tuning intentionally supports a limited selector form (tag, .class, #id, and simple combinations); broader selector syntax can be added later only if a real source needs it`

## Completion Summary
- `Task 06 complete: the default enrichment path now supports opt-in source-specific extraction tuning through `sources.yaml`, including preferred content selectors, excluded boilerplate selectors, and per-source minimum word count overrides without changing review-first workflow semantics`
