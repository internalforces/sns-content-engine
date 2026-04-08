# Operator Control Plane Readiness Progress

## Usage
This file is the live implementation tracker for the operator-control-plane-readiness roadmap.

When an autonomous agent works from [docs/operator-control-plane-readiness-vibe-prompts.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/operator-control-plane-readiness-vibe-prompts.md), it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when the task is complete.

Keep updates short, factual, and current.

## Current Status
- Current milestone: `phase_1_operator_control_plane_basics`
- Current task: `06_control_plane_api_docs_and_regression_coverage`
- Active status: `done`
- Last updated: `2026-04-08 17:20 KST`
- Active branch: `codex/task-06-control-plane-api-docs`
- Latest task commit: `pending`

## Scope For Current Task
- Goal: `Document the operator-facing control-plane API surfaces and add regression coverage that protects the linked-data contract across review, publish-job, and scheduler endpoints`
- In scope: `A concise operator API reference, README linkage to that reference, and focused API regression coverage using realistic linked draft and publish fixtures`
- Out of scope: `Auth, frontend implementation, deployment-guide expansion, scheduler redesign, and any change to manual review or dry-run publish defaults`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | Review-draft detail endpoint | done | 2026-04-07 14:29 KST | Added `GET /reviews/{draft_id}` with repository-backed linked brief/source/enrichment detail and passing API/review regression tests |
| 02 | Review audit and sibling-variant visibility | done | 2026-04-07 16:47 KST | Extended `GET /reviews/{draft_id}` with stored review-action timeline data and same-brief/channel sibling variants plus passing API/workflow coverage |
| 03 | Publish-job list endpoint | done | 2026-04-07 17:00 KST | Added `GET /publish-jobs` with storage-backed state/account/channel/limit filters and linked draft metadata plus passing API/scheduler regression coverage |
| 04 | Publish-job detail and log timeline | done | 2026-04-07 17:10 KST | Added `GET /publish-jobs/{publish_job_id}` with storage-backed draft/source detail, ordered publish-log timeline, and passing API/scheduler regression coverage |
| 05 | Scheduler action API wrappers | done | 2026-04-08 17:09 KST | Added `POST /scheduler/discover`, `/scheduler/backfill`, and `/scheduler/publish-due` with scheduler-backed summaries, explicit live opt-in, and passing API/scheduler regression coverage |
| 06 | Control-plane API docs and regression coverage | done | 2026-04-08 17:20 KST | Added `docs/operator-control-plane-api.md`, linked it from `README.md`, and added passing linked-data API regression coverage for review and publish surfaces |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `README.md`
- `docs/operator-control-plane-api.md`
- `docs/operator-control-plane-readiness-progress.md`
- `tests/test_api.py`

## Progress Log
- `2026-04-07 13:57 KST` Created the operator control plane readiness roadmap based on the current FastAPI, review queue, scheduler, and persistence capabilities already present in the repository
- `2026-04-07 13:57 KST` Chose a next-stage scope centered on review detail, publish-job visibility, scheduler-safe API wrappers, and operator docs because those are the largest remaining control-plane gaps after API and operations readiness
- `2026-04-07 13:57 KST` Left all execution tasks in `pending` so future implementation work can start cleanly from Task `01`
- `2026-04-07 14:22 KST` Started Task `01` on branch `codex/task-01-review-draft-detail-endpoint` with scope limited to one repository-backed review-draft detail read, thin API wiring, and focused API tests
- `2026-04-07 14:28 KST` Added `DraftVariantRepository.get_detail` plus a review-queue read helper so the API can load one draft with its linked brief, source item, and article enrichment without duplicating persistence logic
- `2026-04-07 14:28 KST` Added `GET /reviews/{draft_id}` with explicit operator-facing sections for draft review state, provenance, brief context, source item details, and optional article enrichment
- `2026-04-07 14:28 KST` Extended `tests/test_api.py` with populated and not-found review-detail coverage using the existing draft fixture helper
- `2026-04-07 14:29 KST` Committed Task `01` as `6907f71` (`Add review draft detail API endpoint`) after the focused API test and broader API/review workflow regression slice passed
- `2026-04-07 16:42 KST` Started Task `02` on branch `codex/task-02-review-audit-sibling-visibility` with scope limited to additive review-detail visibility for stored review actions and sibling variants using existing repositories
- `2026-04-07 16:45 KST` Changed the review-detail read helper to return one repository-backed detail bundle so the API can serialize the main draft, chronological review actions, and same-brief/channel sibling variants without reconstructing history from logs
- `2026-04-07 16:46 KST` Extended `GET /reviews/{draft_id}` with explicit `review_actions` and `sibling_variants` sections while preserving the existing draft, provenance, brief, source-item, and article-enrichment fields
- `2026-04-07 16:46 KST` Added focused API coverage for empty and populated review-history states plus a review-workflow helper test for sibling filtering and stable variant ordering
- `2026-04-07 16:48 KST` Committed Task `02` as `f1f0ba2` (`Add review audit and sibling variant detail`) after the focused review-detail slice and broader API/review workflow regression slice passed
- `2026-04-07 16:54 KST` Started Task `03` on branch `codex/task-03-publish-job-list-endpoint` with scope limited to a storage-backed publish-job list endpoint, modest operator filters, and focused API coverage
- `2026-04-07 16:58 KST` Added a repository-backed publish-job operator list helper plus a readable query adapter so the API can filter by state, account, channel, and limit without introducing a separate read model
- `2026-04-07 16:58 KST` Extended the FastAPI contract with `GET /publish-jobs` and linked draft metadata fields, then added focused API coverage for filtered mixed-state results and the empty-state response
- `2026-04-07 17:00 KST` Verified Task `03` with focused publish-job API coverage plus the broader API/scheduler regression slice, and marked the publish-job list endpoint complete pending its focused task commit
- `2026-04-07 17:04 KST` Started Task `04` on branch `codex/task-04-publish-job-detail-log-timeline` with scope limited to a repository-backed publish-job detail read, thin API wiring, and focused API coverage for success, failure, and no-log paths
- `2026-04-07 17:07 KST` Added `PublishJobRepository.get_detail` plus a history-query detail helper so the API can load one publish job with linked draft, brief, source-item context, and ordered persisted publish logs without changing scheduler behavior
- `2026-04-07 17:08 KST` Extended the FastAPI contract with `GET /publish-jobs/{publish_job_id}` including nested draft/provenance/brief/source context, readable publish-log timeline entries, and a dedicated not-found API error
- `2026-04-07 17:08 KST` Added focused API coverage for published, failed, empty-log, and not-found publish-job detail paths while keeping the new surface read-only
- `2026-04-07 17:10 KST` Committed Task `04` as `76eeace` (`Add publish job detail API endpoint`) after the focused publish-job detail API slice and broader API/scheduler regression slice passed
- `2026-04-08 17:04 KST` Started Task `05` on branch `codex/task-05-scheduler-action-api-wrappers` with scope limited to thin API wrappers for scheduler discover, backfill, and publish-due plus focused API coverage for safe defaults
- `2026-04-08 17:07 KST` Added scheduler action request and response models plus thin FastAPI wrappers so the API can expose existing discover, backfill, and publish-due helpers without adding a parallel control-plane workflow layer
- `2026-04-08 17:08 KST` Kept `publish-due` safe by default through an explicit `live` opt-in flag that maps to the existing scheduler helper's `dry_run` behavior instead of changing publish execution defaults
- `2026-04-08 17:09 KST` Added focused API coverage for scheduler action serialization, real backfill creation, default dry-run publish behavior, and explicit live opt-in wiring, then marked Task `05` complete after the focused and broader regression slices passed
- `2026-04-08 17:17 KST` Started Task `06` on branch `codex/task-06-control-plane-api-docs` with scope limited to concise operator-facing API contract docs and tighter regression coverage for the new control-plane surfaces
- `2026-04-08 17:19 KST` Added `docs/operator-control-plane-api.md` as a concise operator reference that distinguishes read-only review/publish routes from scheduler-triggering action routes and reiterates the manual-review plus dry-run safety defaults
- `2026-04-08 17:19 KST` Linked the new control-plane API guide from `README.md` and extended `tests/test_api.py` with a shared linked-data regression that keeps review detail and publish-job responses aligned on draft, brief, provenance, and source context

## Test Log
- `2026-04-07 13:57 KST` `git diff --check` -> `passed`
- `2026-04-07 14:27 KST` `pytest tests/test_api.py -k "review_detail"` -> `failed` (`pytest` entrypoint hit a local import-path issue for this repo; reran with `python -m pytest`)
- `2026-04-07 14:27 KST` `python -m pytest tests/test_api.py -k "review_detail"` -> `passed`
- `2026-04-07 14:28 KST` `python -m pytest tests/test_api.py tests/test_review_queue_workflow.py` -> `passed`
- `2026-04-07 16:43 KST` `python -m pytest tests/test_api.py -k "review_detail"` -> `failed` (`approve` validation rejected an edited test draft that no longer contained the account topic keywords; updated the fixture body and reran)
- `2026-04-07 16:43 KST` `python -m pytest tests/test_review_queue_workflow.py -k "get_review_draft_detail"` -> `failed` (same topic-guard issue in the new workflow test fixture; updated the edited body and reran)
- `2026-04-07 16:45 KST` `python -m pytest tests/test_review_queue_workflow.py -k "get_review_draft_detail"` -> `passed`
- `2026-04-07 16:46 KST` `python -m pytest tests/test_api.py -k "review_detail"` -> `failed` (`schedule` validation hit an attribution-required fixture path unrelated to the audit-history assertion; narrowed that test setup and reran)
- `2026-04-07 16:46 KST` `python -m pytest tests/test_api.py -k "review_detail"` -> `passed`
- `2026-04-07 16:47 KST` `python -m pytest tests/test_api.py tests/test_review_queue_workflow.py` -> `passed`
- `2026-04-07 16:47 KST` `git diff --check` -> `passed`
- `2026-04-07 16:58 KST` `python -m pytest tests/test_api.py -k "publish_jobs"` -> `passed`
- `2026-04-07 16:58 KST` `git diff --check` -> `passed`
- `2026-04-07 16:59 KST` `python -m pytest tests/test_api.py tests/test_scheduler.py` -> `passed`
- `2026-04-07 17:07 KST` `git diff --check` -> `passed`
- `2026-04-07 17:07 KST` `python -m pytest tests/test_api.py -k "publish_job_detail"` -> `passed`
- `2026-04-07 17:08 KST` `python -m pytest tests/test_api.py tests/test_scheduler.py` -> `passed`
- `2026-04-08 17:05 KST` `git diff --check` -> `passed`
- `2026-04-08 17:06 KST` `python -m pytest tests/test_api.py -k "scheduler_discover_endpoint or scheduler_backfill_endpoint or scheduler_publish_due_endpoint"` -> `failed` (`backfill` uses the current clock, so the fixed scheduled timestamp assertion was too strict; relaxed the expectation to assert a scheduled UTC slot instead and reran)
- `2026-04-08 17:07 KST` `git diff --check` -> `passed`
- `2026-04-08 17:07 KST` `python -m pytest tests/test_api.py -k "scheduler_discover_endpoint or scheduler_backfill_endpoint or scheduler_publish_due_endpoint"` -> `passed`
- `2026-04-08 17:08 KST` `python -m pytest tests/test_api.py tests/test_scheduler.py` -> `passed`
- `2026-04-08 17:18 KST` `git diff --check` -> `passed`
- `2026-04-08 17:18 KST` `python -m pytest tests/test_api.py -k "control_plane_read_endpoints_share_consistent_linked_context"` -> `failed` (`include_article_enrichment=True` made source attribution mandatory for scheduling; updated the fixture body to include the required attribution and reran)
- `2026-04-08 17:19 KST` `git diff --check` -> `passed`
- `2026-04-08 17:19 KST` `python -m pytest tests/test_api.py -k "control_plane_read_endpoints_share_consistent_linked_context"` -> `passed`
- `2026-04-08 17:19 KST` `python -m pytest tests/test_api.py tests/test_scheduler.py` -> `passed`

## Blockers
- `None currently`

## Follow-up
- `None yet`

## Completion Summary
- `Task 01 complete: single-draft review detail is now available through `GET /reviews/{draft_id}` with explicit draft, provenance, brief, source-item, and enrichment context`
- `Task 02 complete: `GET /reviews/{draft_id}` now also exposes stored review-action history and same-brief/channel sibling variants with stable ordering and empty-state coverage`
- `Task 03 complete: `GET /publish-jobs` now exposes stored publish jobs with state/account/channel/limit filters plus linked draft, brief, and source metadata for operator list views`
- `Task 04 complete: `GET /publish-jobs/{publish_job_id}` now exposes one publish job with readable state/timestamps, linked draft and source context, and ordered persisted publish-log events for operator detail views`
- `Task 05 complete: the API now exposes `POST /scheduler/discover`, `POST /scheduler/backfill`, and `POST /scheduler/publish-due` as thin wrappers around the existing scheduler helpers while preserving default dry-run publish safety through an explicit live opt-in`
- `Task 06 complete: the repository now has a focused operator control-plane API guide plus shared linked-data regression coverage that protects the documented review-detail, publish-job, and scheduler safety contract`
