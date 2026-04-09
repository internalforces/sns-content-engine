# API And Operations Readiness Roadmap

## Goal
Extend the current CLI-first review workflow into a backend-ready next stage that:
- exposes the existing run, failure, article, and review data through stable API surfaces
- keeps the current manual-review and publish safety model intact
- adds a practical database migration baseline for non-destructive SQLite upgrades
- improves operator readiness for real source configuration and article extraction quality

## Generated document naming
When instantiating this template, use a filename that clearly shows the document identity.

- Roadmap file: `docs/api-operations-readiness-roadmap.md`
- Execution guide file: `docs/api-operations-readiness-execution-guide.md`
- Progress tracker file: `docs/api-operations-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/api-operations-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `plan.md`, or `notes.md` when multiple initiatives may exist.

## Roadmap construction rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- Define only as many milestones and tasks as are needed to reach the goal while keeping each unit safely implementable.
- Choose task and milestone boundaries so the work can be completed without breaking the existing architecture, workflow semantics, safety gates, or operator experience.
- Prefer the smallest additive API, migration, and extraction slices that reuse the current workflow and repository structure instead of forcing a broad redesign.
- Split a task when it would otherwise span unrelated surfaces, require unclear rollback, or make testing too broad.
- Merge adjacent tiny tasks when they share the same code path, verification surface, and branch scope.
- If the roadmap shape changes during implementation, update this file and `docs/api-operations-readiness-progress-tracker.md` before continuing.

## Current implementation snapshot

### Already implemented
- Config-driven source loading, discovery, ingestion, enrichment, brief building, draft generation, review, scheduler, and publish workflows.
- Policy-aware source handling, provenance capture, and readable run and failure query helpers.
- UI-facing data contract notes for run overview, article list, draft review, and failure views.
- Operational healthcheck and single-server scheduler support.

### Current limitations relevant to the new goal
- At roadmap creation time, the repository depended on FastAPI but did not expose any real API routes yet.
- `app/api/` was still a placeholder, so future UI work would have needed CLI commands or direct internal-module access.
- Database schema validation was strict, but automatic migration support did not exist yet.
- Example configs still used placeholder URLs and required manual operator replacement before real runs.
- HTML extraction was intentionally lightweight and needed a small source-specific escape hatch for harder publisher layouts.

## Environment and execution assumptions
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands already available:
  - `PYTHONPATH=$PWD pytest tests/test_api.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_review_queue_workflow.py`
  - `PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py`
  - `PYTHONPATH=$PWD pytest tests/test_article_extractor.py tests/test_enrich_articles_workflow.py tests/test_config.py`
- Broader regression commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_cli.py tests/test_review_queue_workflow.py`
  - `PYTHONPATH=$PWD pytest tests/test_storage.py tests/test_operations.py tests/test_enrich_articles_workflow.py`
- Required local services:
  - `none for most read-only API and docs work`
  - `a local SQLite database file when testing outside temporary fixtures`
- Required env files, secrets, or fixtures:
  - `config/ or another operator-approved config directory`
  - `temporary SQLite fixtures or sqlite:///data/sns_content_engine.db`
- Package install policy: `ask_first`

## Target architecture

### API layer
- `read_only_surfaces`
  - Health, run history, failure history, article status, and pending-review listing routes serialize existing workflow and query helpers.
  - Response shapes stay explicit and UI-friendly without duplicating business logic in handlers.
- `review_action_surfaces`
  - Approve, reject, edit, and schedule routes call existing `review_queue` helpers and return structured HTTP errors.
  - Validation, provenance, attribution, and state-conflict semantics stay owned by current workflow and service paths.

### Operations layer
1. Validate schema state before application startup and API health exposure.
2. Support intentional SQLite schema upgrades instead of database recreation for every model change.
3. Make config-readiness failures obvious before real runs.
4. Add a narrow source-specific extraction override path without redesigning enrichment.

## Milestones
Use as many milestone blocks as needed. Keep each milestone small enough to be completed without breaking the current structure or requiring a broad redesign.

### Milestone M1: Read-Only API Foundation
- Goal: Add the smallest backend-ready HTTP surface for health, run history, failure history, article status, and pending-review visibility.
- Includes:
  - a concrete FastAPI app entrypoint and thin read-only route wiring
  - JSON serialization for health, run, failure, article, and pending-review data
- Excludes:
  - review mutation routes
  - migration work and extraction tuning
- Verification target:
  - focused API and history-query coverage
  - one shared CLI or review-workflow regression slice
- Ship when:
  - operators and future UI layers can fetch the current read-only workflow state without parsing CLI output
  - the API reuses existing history and queue helpers without changing their semantics

### Milestone M2: Review Workflow API Parity
- Goal: Expose review mutations through HTTP without changing the current manual-review and scheduling rules.
- Includes:
  - approve, reject, edit, and schedule action routes
  - structured HTTP error mapping for workflow and validation failures
- Excludes:
  - auto-approve or auto-publish behavior
  - publish-job and scheduler action expansion
- Verification target:
  - focused API review-action coverage
  - broader `review_queue` and draft-validation regression coverage
- Ship when:
  - review actions can be triggered over HTTP
  - validation and conflict behavior remain aligned with the CLI path

### Milestone M3: SQLite Upgrade Baseline
- Goal: Add a modest, operator-friendly upgrade path for SQLite-backed local environments.
- Includes:
  - schema version metadata and legacy version detection
  - one intentional `db upgrade` flow and related operator guidance
- Excludes:
  - a broad migration framework
  - non-SQLite upgrade orchestration
- Verification target:
  - focused storage, CLI, and script coverage
  - one broader operations or API regression slice
- Ship when:
  - previously initialized local databases can be upgraded intentionally
  - operators are no longer forced to recreate the database for every schema change

### Milestone M4: Operator Readiness And Extraction Reliability
- Goal: Reduce common operator setup mistakes and support one small extraction escape hatch for hard publisher layouts.
- Includes:
  - placeholder-config readiness failures and clearer guidance
  - source-specific extraction selectors and minimum-word-count overrides
- Excludes:
  - scraper-subsystem redesign
  - new connectors, auth, or frontend work
- Verification target:
  - focused operations, API, CLI, extractor, config, and enrichment-workflow coverage
  - one broader run-local or storage-adjacent regression slice
- Ship when:
  - sample config directories and unresolved placeholder URLs fail clearly
  - the default enrichment path supports at least one source-specific override shape without workflow drift

## Implementation roadmap

## Phase 1: Read-Only API Foundation

### Task 01: FastAPI application wiring and read-only history
- Goal: Add a real FastAPI application and expose safe read-only health and history data as JSON without duplicating current workflow logic.
- Actions:
  - create a concrete FastAPI app entrypoint and router structure in `app/api/`
  - expose `/health`, `/runs`, and `/failures` by reusing `run_healthcheck`, `list_pipeline_runs`, and `list_pipeline_failures`
  - add focused API coverage for readiness JSON and history payloads
- Dependencies:
  - existing CLI and operations helpers in `app/operations.py`
  - `app/workflows/history_queries.py`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py`
- Risk or rollback note:
  - keep handlers thin so the new API surface can be removed or reshaped without changing workflow behavior
- Done when:
  - the repository has a concrete API application entrypoint
  - `/health`, `/runs`, and `/failures` return stable JSON
  - focused tests cover the new API surface
  - `docs/api-operations-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 02: Article and pending-review read endpoints
- Goal: Expose stored article and pending-review status through API handlers that match the current UI data contract.
- Actions:
  - add `/articles` and `/reviews/pending` routes
  - reuse article-status and pending-review helpers instead of inventing a new read model
  - add focused API and workflow coverage for populated and empty-state responses
- Dependencies:
  - Task 01
  - existing review queue and history-query helpers
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_review_queue_workflow.py -k "list_pending_review_drafts"`
- Risk or rollback note:
  - keep response fields aligned with stored data and current UI notes instead of introducing speculative filtering or pagination
- Done when:
  - an operator or future UI can fetch article status rows and pending drafts without parsing CLI output
  - the response shape stays aligned with the current data contract and stored state
  - focused tests cover representative populated and empty-state behavior
  - `docs/api-operations-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 2: Review Workflow API Parity

### Task 03: Review action API parity
- Goal: Expose approve, reject, edit, and schedule actions through API routes without changing review semantics.
- Actions:
  - add thin POST action routes for approve, reject, edit, and schedule
  - reuse `app.workflows.review_queue` and existing draft-validation paths
  - map missing-draft, conflict, and validation failures into structured HTTP responses
- Dependencies:
  - Task 02
  - existing review action workflow and validation logic
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py`
  - `PYTHONPATH=$PWD pytest tests/test_review_queue_workflow.py`
- Risk or rollback note:
  - keep all mutation semantics owned by the current review workflow so the API cannot bypass attribution, provenance, or scheduling blockers
- Done when:
  - review actions can be triggered through API calls
  - validation failures are returned clearly and consistently
  - review semantics stay aligned with the CLI path
  - `docs/api-operations-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 3: SQLite Upgrade Baseline

### Task 04: SQLite migration baseline
- Goal: Introduce a modest, intentional SQLite upgrade mechanism instead of relying only on schema recreation.
- Actions:
  - add schema-version metadata and legacy-version detection for existing SQLite files
  - add one explicit `db upgrade` path and a matching script entrypoint
  - update operator docs and readiness messaging so upgrade expectations are clear
- Dependencies:
  - existing schema validation and bootstrap logic in `app/storage/bootstrap.py`
  - CLI entrypoints and operator docs
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_storage.py -k "schema_version or upgrade_database_schema or bootstrap_database"`
  - `PYTHONPATH=$PWD pytest tests/test_cli.py -k "healthcheck or db_"`
- Risk or rollback note:
  - keep migration work limited to additive upgrade safety instead of introducing a large migration framework
- Done when:
  - a previously initialized local database can be upgraded intentionally
  - operators are no longer forced to recreate the DB for every schema addition
  - focused tests cover version detection and at least one upgrade path
  - `docs/api-operations-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 4: Operator Readiness And Extraction Reliability

### Task 05: Config readiness guidance and validation
- Goal: Make placeholder source and config usage easier to detect before real runs.
- Actions:
  - add healthcheck-side readiness validation for bundled sample config directories and placeholder example URLs
  - update API, CLI, and operations messaging to surface actionable readiness failures
  - refresh operator docs so sample config expectations are explicit
- Dependencies:
  - Task 04
  - `app.operations` healthcheck path and current config loaders
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_operations.py`
  - `PYTHONPATH=$PWD pytest tests/test_api.py -k health`
- Risk or rollback note:
  - keep readiness checks narrowly focused on high-signal operator mistakes instead of turning healthcheck into a broad deployment linter
- Done when:
  - readiness checks clearly distinguish sample config from operator-ready config
  - common setup mistakes fail with actionable messages
  - focused API, CLI, and operations coverage protects the new behavior
  - `docs/api-operations-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 06: Source-specific extraction tuning hooks
- Goal: Extend extraction in a narrowly additive way so hard publisher layouts can be handled without rewriting the whole extractor.
- Actions:
  - add opt-in source extraction config for preferred and excluded selectors plus minimum-word-count overrides
  - wire default extractor construction in `enrich_articles` so source-specific overrides are used automatically
  - add focused config, extractor, and workflow coverage plus one example config shape
- Dependencies:
  - Task 05
  - current extraction and enrichment path in `app/services/article_extractor.py` and `app/workflows/enrich_articles.py`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_article_extractor.py`
  - `PYTHONPATH=$PWD pytest tests/test_config.py -k extraction`
- Risk or rollback note:
  - keep selector support intentionally limited so the default extractor stays simple and testable
- Done when:
  - the enrichment path supports at least one source-specific extraction override shape
  - extraction tuning stays compatible with the current workflow and injected custom-extractor tests
  - focused config, extractor, and workflow coverage passes
  - `docs/api-operations-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Suggested execution order
List only the tasks that actually exist in dependency order. Add or remove lines as needed.

1. Task 01
2. Task 02
3. Task 03
4. Task 04
5. Task 05
6. Task 06

## Initial milestone recommendation
Start with the smallest milestone that:
- introduces a real FastAPI application entrypoint
- exposes read-only health, history, article, and pending-review surfaces
- preserves the current review-first and publish-safety model
- can be implemented and verified without breaking the existing workflow structure

This keeps the next stage focused on making the current system consumable by future UI or automation work before expanding into broader product features.
