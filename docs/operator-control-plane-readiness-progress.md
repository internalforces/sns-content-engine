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
- Current task: `02_review_audit_and_sibling_variant_visibility`
- Active status: `done`
- Last updated: `2026-04-07 16:48 KST`
- Active branch: `codex/task-02-review-audit-sibling-visibility`
- Latest task commit: `f1f0ba2` (`Add review audit and sibling variant detail`)

## Scope For Current Task
- Goal: `Expose stored review-action history and sibling variants through the draft-detail API so operators can understand timeline context and compare alternatives`
- In scope: `Repository-backed review action and sibling variant reads, additive review-detail serialization, and focused API/workflow tests`
- Out of scope: `Publish-job API reads, scheduler action endpoints, auth, and frontend implementation`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | Review-draft detail endpoint | done | 2026-04-07 14:29 KST | Added `GET /reviews/{draft_id}` with repository-backed linked brief/source/enrichment detail and passing API/review regression tests |
| 02 | Review audit and sibling-variant visibility | done | 2026-04-07 16:47 KST | Extended `GET /reviews/{draft_id}` with stored review-action timeline data and same-brief/channel sibling variants plus passing API/workflow coverage |
| 03 | Publish-job list endpoint | pending | 2026-04-07 13:57 KST | Roadmap created; implementation not started |
| 04 | Publish-job detail and log timeline | pending | 2026-04-07 13:57 KST | Roadmap created; implementation not started |
| 05 | Scheduler action API wrappers | pending | 2026-04-07 13:57 KST | Roadmap created; implementation not started |
| 06 | Control-plane API docs and regression coverage | pending | 2026-04-07 13:57 KST | Roadmap created; implementation not started |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `docs/operator-control-plane-readiness-progress.md`
- `app/workflows/review_queue.py`
- `app/api/app.py`
- `tests/test_api.py`
- `tests/test_review_queue_workflow.py`

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

## Blockers
- `None currently`

## Follow-up
- `None yet`

## Completion Summary
- `Task 01 complete: single-draft review detail is now available through `GET /reviews/{draft_id}` with explicit draft, provenance, brief, source-item, and enrichment context`
- `Task 02 complete: `GET /reviews/{draft_id}` now also exposes stored review-action history and same-brief/channel sibling variants with stable ordering and empty-state coverage`
