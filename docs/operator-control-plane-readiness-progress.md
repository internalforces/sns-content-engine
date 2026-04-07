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
- Current task: `01_review_draft_detail_endpoint`
- Active status: `in_progress`
- Last updated: `2026-04-07 14:28 KST`
- Active branch: `codex/task-01-review-draft-detail-endpoint`
- Latest task commit: `not_created`

## Scope For Current Task
- Goal: `Expose full review-draft context through the API so a real operator screen can inspect one draft without CLI parsing or direct DB access`
- In scope: `A draft-detail route, reuse of existing brief/provenance storage, focused API serialization, and targeted tests`
- Out of scope: `Scheduler actions, live publish behavior changes, auth, and frontend implementation`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | Review-draft detail endpoint | in_progress | 2026-04-07 14:22 KST | Implementing repository-backed single-draft detail API on dedicated task branch |
| 02 | Review audit and sibling-variant visibility | pending | 2026-04-07 13:57 KST | Roadmap created; implementation not started |
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
- `app/storage/repositories.py`
- `app/workflows/review_queue.py`
- `app/api/app.py`
- `tests/test_api.py`

## Progress Log
- `2026-04-07 13:57 KST` Created the operator control plane readiness roadmap based on the current FastAPI, review queue, scheduler, and persistence capabilities already present in the repository
- `2026-04-07 13:57 KST` Chose a next-stage scope centered on review detail, publish-job visibility, scheduler-safe API wrappers, and operator docs because those are the largest remaining control-plane gaps after API and operations readiness
- `2026-04-07 13:57 KST` Left all execution tasks in `pending` so future implementation work can start cleanly from Task `01`
- `2026-04-07 14:22 KST` Started Task `01` on branch `codex/task-01-review-draft-detail-endpoint` with scope limited to one repository-backed review-draft detail read, thin API wiring, and focused API tests
- `2026-04-07 14:28 KST` Added `DraftVariantRepository.get_detail` plus a review-queue read helper so the API can load one draft with its linked brief, source item, and article enrichment without duplicating persistence logic
- `2026-04-07 14:28 KST` Added `GET /reviews/{draft_id}` with explicit operator-facing sections for draft review state, provenance, brief context, source item details, and optional article enrichment
- `2026-04-07 14:28 KST` Extended `tests/test_api.py` with populated and not-found review-detail coverage using the existing draft fixture helper

## Test Log
- `2026-04-07 13:57 KST` `git diff --check` -> `passed`
- `2026-04-07 14:27 KST` `pytest tests/test_api.py -k "review_detail"` -> `failed` (`pytest` entrypoint hit a local import-path issue for this repo; reran with `python -m pytest`)
- `2026-04-07 14:27 KST` `python -m pytest tests/test_api.py -k "review_detail"` -> `passed`
- `2026-04-07 14:28 KST` `python -m pytest tests/test_api.py tests/test_review_queue_workflow.py` -> `passed`

## Blockers
- `None currently`

## Follow-up
- `None yet`

## Completion Summary
- `Roadmap scaffolded; implementation has not started yet`
