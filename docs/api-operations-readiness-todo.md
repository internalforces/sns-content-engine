# API And Operations Readiness TODO

## Goal
Extend the current CLI-first review workflow into a backend-ready next stage that:
- exposes the existing run, failure, and review data through stable API surfaces,
- keeps the current manual-review and publish safety model intact,
- adds a practical database migration baseline for non-destructive upgrades,
- improves operator readiness for real source configuration and article extraction quality.

## Current implementation snapshot

### Already implemented
- Config-driven source loading, discovery, ingestion, enrichment, brief building, draft generation, review, scheduler, and publish workflows.
- Policy-aware source handling, provenance capture, and readable run/failure query helpers.
- UI-facing data contract notes for run overview, article list, draft review, and failure views.
- Operational healthcheck and single-server scheduler support.

### Current limitations relevant to the new goal
- The repository depends on FastAPI but does not expose any real API routes yet.
- `app/api/` is still a placeholder, so future UI work would need to call CLI commands or internal Python modules directly.
- Database schema validation is strict, but automatic migration support does not exist yet.
- Example configs still use placeholder URLs and require manual operator replacement before real runs.
- HTML extraction is intentionally lightweight and may need source-specific handling for complex publisher layouts.

## Target architecture

### API layer
- `read_only`
  - Health, run history, failure history, article status, and pending-review listing endpoints.
- `review_actions`
  - Approve, reject, edit, and schedule actions exposed through validated API handlers.
- `operator_safe`
  - Preserve the current review-first semantics and never bypass scheduling or publish validation.

### Operations layer
1. Validate schema state before application startup.
2. Support explicit schema upgrades instead of forcing database recreation for every model change.
3. Make config readiness and sample-config replacement expectations more operator-visible.
4. Add source-specific extraction escape hatches without redesigning the current enrichment workflow.

## TODO roadmap

## Phase 1: Read-only API foundation

### 1. Add FastAPI application wiring for existing health and history surfaces
- Create a minimal FastAPI app and router structure in `app/api/`.
- Reuse existing workflow/query helpers instead of duplicating business logic.
- Start with safe read-only routes:
  - `/health`
  - `/runs`
  - `/failures`
- Done when:
  - the repository has a concrete API application entrypoint,
  - health and history data can be returned as JSON,
  - tests cover the new API surface.

### 2. Add article-list and pending-review read endpoints
- Expose the existing article/enrichment status and pending-review draft list through API handlers.
- Keep response fields aligned with the current UI data contract and stored data.
- Done when:
  - an operator or future UI can fetch article status rows and pending drafts without parsing CLI output,
  - tests cover the endpoint response shape and basic empty-state behavior.

## Phase 2: Review workflow API parity

### 3. Add review action endpoints without changing review semantics
- Expose approve, reject, edit, and schedule actions through API routes.
- Reuse `review_queue` validation and repository logic.
- Preserve current approval and schedule-time blockers for attribution, provenance, and restricted-source reuse.
- Done when:
  - review actions can be triggered through API calls,
  - validation failures are returned clearly,
  - review semantics stay aligned with the CLI path.

## Phase 3: Schema upgrade baseline

### 4. Add a practical migration baseline for SQLite-backed local environments
- Introduce an explicit migration mechanism instead of relying only on schema recreation.
- Keep the first version modest:
  - baseline migration metadata,
  - forward upgrades for current schema versions,
  - clear CLI or script entrypoint for upgrade execution.
- Done when:
  - a previously initialized local database can be upgraded intentionally,
  - operators are no longer forced to recreate the DB for every schema addition,
  - tests cover version detection and at least one upgrade path.

## Phase 4: Operator readiness and extraction reliability

### 5. Improve operator-facing config readiness guidance and validation
- Make placeholder source/config usage easier to detect before real runs.
- Add clearer readiness feedback for sample config directories and unresolved placeholder URLs.
- Keep example configs available, but make production-readiness gaps more obvious.
- Done when:
  - readiness checks or docs clearly distinguish sample config from operator-ready config,
  - common setup mistakes fail with actionable messages.

### 6. Add source-specific extraction tuning hooks
- Extend extraction in a narrowly additive way so hard publisher layouts can be handled without rewriting the whole extractor.
- Prefer opt-in rules or small parser hooks over a complex scraping subsystem.
- Done when:
  - the enrichment path can support at least one source-specific extraction override shape,
  - extraction tuning stays compatible with the current workflow and tests.

## Suggested execution order
1. FastAPI application wiring and read-only history endpoints.
2. Article list and pending-review API reads.
3. Review action API parity.
4. Migration baseline.
5. Config readiness validation.
6. Source-specific extraction tuning hooks.

## Recommended first milestone
Ship a small "backend-ready operator API" milestone with:
- a real FastAPI application,
- read-only health/history/article/review endpoints,
- review action endpoints that reuse the existing validation path,
- no change to manual-review or publish safety semantics.

This keeps the next stage focused on making the current system consumable by a UI or other backend clients before expanding into broader product features.
