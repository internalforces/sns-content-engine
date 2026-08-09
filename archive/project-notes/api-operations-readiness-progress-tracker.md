# API And Operations Readiness Progress Tracker

## Usage
This file is the live implementation tracker for the API And Operations Readiness roadmap.

When an autonomous agent works from `docs/api-operations-readiness-execution-guide.md`, it should update this file:
- before starting a task
- during meaningful implementation progress
- after running tests
- when a blocker or stop reason appears
- when the task is complete

Keep updates short, factual, and current.

## Generated document naming
When instantiating this template, keep the filename explicit so this file is easy to distinguish from planning or prompt documents.

- Recommended filename: `docs/api-operations-readiness-progress-tracker.md`
- Related files:
  - `docs/api-operations-readiness-vibe-coding-prompt.md`
  - `docs/api-operations-readiness-roadmap.md`
  - `docs/api-operations-readiness-execution-guide.md`

If `Current task` is already marked `in_progress` or `blocked`, resume or resolve that task before picking a new one unless the roadmap was intentionally reprioritized.

## Current Status
- Current milestone: `M4_operator_readiness_and_extraction_reliability`
- Current task: `06_source_specific_extraction_tuning_hooks`
- Active status: `done`
- Last updated: `2026-04-09 15:29 KST`
- Base branch: `master`
- Active branch: `codex/task-06-source-extraction-hooks`
- Latest task commit: `01398ea`
- Resume decision: `pick_next_task`
- Stop reason: `none`

## Scope For Current Task
- Goal: `Add a small source-specific extraction override path so hard publisher layouts can be tuned without redesigning enrichment`
- In scope: `Source-level extraction config schema, default extractor hook-up through enrich_articles, focused extractor/config/workflow coverage, an example all-domain source override, and progress tracking`
- Out of scope: `Auth, frontend work, scraper subsystem redesign, new connector behavior, and unrelated review or scheduler changes`
- Dependencies: `Task 05 readiness work, source config schemas, the default extractor path in app/services/article_extractor.py, and enrich_articles default-extractor construction`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_article_extractor.py`
  - `PYTHONPATH=$PWD pytest tests/test_config.py -k extraction`
  - `PYTHONPATH=$PWD pytest tests/test_enrich_articles_workflow.py -k source_specific_extraction_rules_with_default_extractor`

## Environment Notes
- Required services status: `running (none required beyond local SQLite fixtures)`
- Env or fixture status: `ready (config/ and SQLite-backed test fixtures already exist)`
- Existing unrelated failures: `none known`

## Roadmap Status
Duplicate or remove rows as needed. The number of milestones and tasks is intentionally flexible.

| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | FastAPI application wiring and read-only history | done | 2026-04-06 16:08 KST | Added a concrete FastAPI app entrypoint with `/health`, `/runs`, and `/failures` backed by existing helpers in commit `9996312` |
| M1 | 02 | Article and pending-review read endpoints | done | 2026-04-07 10:55 KST | Added `/articles` and `/reviews/pending` with shared query reuse and focused API plus workflow coverage in commit `af98e06` |
| M2 | 03 | Review action API parity | done | 2026-04-07 11:05 KST | Added thin approve, reject, edit, and schedule routes plus structured HTTP error mapping on task branch commit `440ff2a` |
| M3 | 04 | SQLite migration baseline | done | 2026-04-07 11:30 KST | Added schema-version tracking, `db upgrade`, and focused upgrade regression coverage in commit `726f790` |
| M4 | 05 | Config readiness guidance and validation | done | 2026-04-07 11:42 KST | Healthcheck now fails fast on sample configs and placeholder URLs, with focused API, CLI, and operations coverage in commit `74e7c19` |
| M4 | 06 | Source-specific extraction tuning hooks | done | 2026-04-07 13:47 KST | Added opt-in extraction selectors and minimum-word-count overrides to the default enrichment path in commit `01398ea` |

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
- `2026-04-06 15:53 KST` Created the API and operations readiness roadmap from the current repository state after finance-local MVP, all-domain phase 1, and implementation-alignment completion.
- `2026-04-06 15:53 KST` Chose a next-stage scope centered on FastAPI surfaces, review API parity, migration baseline, operator config readiness, and extraction tuning because those were the highest-signal gaps still visible in the codebase.
- `2026-04-06 15:53 KST` Left all execution tasks in `pending` so future implementation work could start cleanly from Task `01`.
- `2026-04-06 15:57 KST` Started Task `01` on branch `codex/task-01-fastapi-readonly-history`.
- `2026-04-06 16:01 KST` Added `app.api.create_app()` plus `/health`, `/runs`, and `/failures` routes that delegate to existing healthcheck and history helpers without duplicating business logic.
- `2026-04-06 16:08 KST` Committed Task `01` as `9996312` (`Add FastAPI app with health and history routes`) after focused API, history-query, and CLI regression checks passed.
- `2026-04-07 10:48 KST` Started Task `02` on branch `codex/task-02-article-review-read-endpoints`.
- `2026-04-07 10:53 KST` Added `list_article_statuses` plus `/articles` and `/reviews/pending`, keeping handlers serialization-only wrappers around existing workflow and queue helpers.
- `2026-04-07 10:55 KST` Committed Task `02` as `af98e06` (`Add article and pending-review read endpoints`) after focused API and workflow coverage passed.
- `2026-04-07 10:59 KST` Started Task `03` on branch `codex/task-03-review-action-api-parity`.
- `2026-04-07 11:02 KST` Added POST review-action routes and structured HTTP error mapping for missing drafts, conflicts, validation failures, config errors, and schema-readiness failures without changing `review_queue` semantics.
- `2026-04-07 11:05 KST` Committed Task `03` on task branch `codex/task-03-review-action-api-parity` as `440ff2a` (`Expose review queue actions through API handlers`) after focused API, review-workflow, and CLI review regression checks passed.
- `2026-04-07 11:14 KST` Started Task `04` on branch `codex/task-04-sqlite-migration-baseline`.
- `2026-04-07 11:20 KST` Implemented SQLite migration helpers in `app/storage/bootstrap`, added schema-version detection for unversioned databases, and introduced an explicit `db upgrade` flow plus script support.
- `2026-04-07 11:30 KST` Committed Task `04` as `726f790` (`Add SQLite schema migration baseline`) after focused storage, CLI, script, and broader operations and API regression slices passed.
- `2026-04-07 11:35 KST` Started Task `05` on branch `codex/task-05-config-readiness-validation`.
- `2026-04-07 11:39 KST` Added a dedicated `config_readiness` healthcheck step that fails fast on bundled sample config directories and unresolved placeholder example URLs, then aligned README and test coverage to match.
- `2026-04-07 11:42 KST` Committed Task `05` as `74e7c19` (`Improve healthcheck config readiness guidance`) after focused API, CLI, and operations regression checks passed.
- `2026-04-07 13:36 KST` Started Task `06` on branch `codex/task-06-source-extraction-hooks`.
- `2026-04-07 13:47 KST` Added `SourceExtractionConfig`, limited selector validation, source-key-based default extractor construction, and a sample all-domain extraction override without changing injected custom-extractor behavior.
- `2026-04-07 13:47 KST` Committed Task `06` as `01398ea` (`Add source-specific extraction tuning hooks`) after focused extractor, config, and enrichment-workflow coverage plus broader run-local-adjacent regression checks passed.

## Test Log
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_api.py` -> `passed`
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_history_queries.py` -> `passed`
- `2026-04-06 16:04 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k 'healthcheck or history'` -> `passed`
- `2026-04-07 10:53 KST` `PYTHONPATH=$PWD pytest tests/test_history_queries.py` -> `passed`
- `2026-04-07 10:53 KST` `PYTHONPATH=$PWD pytest tests/test_api.py` -> `passed`
- `2026-04-07 10:53 KST` `PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py -k 'list_pending_review_drafts'` -> `passed`
- `2026-04-07 11:04 KST` `PYTHONPATH=$PWD pytest tests/test_api.py` -> `passed`
- `2026-04-07 11:04 KST` `PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py` -> `passed`
- `2026-04-07 11:05 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k 'test_review_'` -> `passed`
- `2026-04-07 11:20 KST` `PYTHONPATH=$PWD pytest tests/test_storage.py -k 'schema_version or upgrade_database_schema or bootstrap_database'` -> `passed`
- `2026-04-07 11:20 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k 'healthcheck or db_'` -> `passed`
- `2026-04-07 11:20 KST` `PYTHONPATH=$PWD pytest tests/test_scripts.py -k 'create_db_script'` -> `passed`
- `2026-04-07 11:27 KST` `PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py tests/test_api.py` -> `passed`
- `2026-04-07 11:39 KST` `PYTHONPATH=$PWD pytest tests/test_operations.py` -> `passed`
- `2026-04-07 11:39 KST` `PYTHONPATH=$PWD pytest tests/test_api.py -k health` -> `passed`
- `2026-04-07 11:39 KST` `PYTHONPATH=$PWD pytest tests/test_cli.py -k healthcheck` -> `passed`
- `2026-04-07 11:40 KST` `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_cli.py` -> `passed`
- `2026-04-07 13:45 KST` `PYTHONPATH=$PWD pytest tests/test_article_extractor.py` -> `passed`
- `2026-04-07 13:46 KST` `PYTHONPATH=$PWD pytest tests/test_config.py -k extraction` -> `passed`
- `2026-04-07 13:46 KST` `PYTHONPATH=$PWD pytest tests/test_enrich_articles_workflow.py -k source_specific_extraction_rules_with_default_extractor` -> `passed`
- `2026-04-07 13:47 KST` `PYTHONPATH=$PWD pytest tests/test_article_extractor.py tests/test_enrich_articles_workflow.py tests/test_run_local_pipeline_workflow.py tests/test_config.py` -> `passed`

## Open Questions
- `None currently; any follow-on backend, control-plane, or browser expansion should be scoped as a new roadmap item instead of reopening this completed initiative.`

## Blockers
- `None currently`

## Follow-up
- `Further operator control-plane and browser-console work continued in later readiness initiatives; keep this tracker as the completed backend-readiness baseline rather than extending it ad hoc.`

## Completion Summary
- Task 01 complete: the repository gained a concrete FastAPI app entrypoint with read-only `/health`, `/runs`, and `/failures` routes backed by existing healthcheck and history helpers.
- Task 02 complete: `/articles` and `/reviews/pending` now expose stored article and pending-review state without requiring CLI parsing.
- Task 03 complete: approve, reject, edit, and schedule review actions are available through thin API handlers that preserve current workflow and validation semantics.
- Task 04 complete: SQLite-backed local environments now have an intentional schema-upgrade baseline with version detection, `db upgrade`, and supporting docs.
- Task 05 complete: healthcheck now catches bundled sample config directories and placeholder URLs before real runs, with aligned API, CLI, and operations feedback.
- Task 06 complete: the default enrichment path now supports opt-in source-specific extraction selectors and minimum-word-count overrides without redesigning the extractor or review-first workflow.
