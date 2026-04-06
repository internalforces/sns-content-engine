# Implementation Alignment Progress

## Usage
This file is the live implementation tracker for the implementation-alignment roadmap.

When an autonomous agent works from [docs/implementation-alignment-vibe-prompts.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/implementation-alignment-vibe-prompts.md), it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when the task is complete.

Keep updates short, factual, and current.

## Current Status
- Current milestone: `phase_1_runtime_and_docs_parity`
- Current task: `02_policy_aware_history_cli_parity`
- Active status: `in_progress`
- Last updated: `2026-04-06 15:19 KST`
- Active branch: `codex/task-02-history-cli-parity`
- Latest task commit: `n/a`

## Scope For Current Task
- Goal: `Expose policy-aware run and failure history details in the operator CLI so the terminal view matches the query layer`
- In scope: `history runs/failures output shape, focused CLI coverage, and clear visibility for policy skips`
- Out of scope: `New history storage fields, UI work, scheduler changes, and unrelated doc refreshes`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | Provider config runtime wiring | done | 2026-04-06 15:13 KST | Live draft workflows now load optional `providers.yaml` and still fall back to env-only resolution |
| 02 | Policy-aware history CLI parity | in_progress | 2026-04-06 15:19 KST | Updating `history runs` and `history failures` so policy-aware query fields are visible to operators |
| 03 | README and operator wording refresh | pending | 2026-04-06 15:02 KST | Several docs still describe pre-alignment behavior |
| 04 | Progress metadata cleanup | pending | 2026-04-06 15:02 KST | Progress log commit metadata should be refreshed after alignment work lands |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `docs/implementation-alignment-progress.md`

## Progress Log
- `2026-04-06 15:02 KST` Created the implementation-alignment roadmap docs based on the currently observed documentation/runtime mismatches
- `2026-04-06 15:02 KST` Left all execution tasks in `pending` so future implementation work can start from Task `01`
- `2026-04-06 15:08 KST` Started Task `01` on branch `codex/task-01-provider-config-runtime-wiring`
- `2026-04-06 15:08 KST` Intended scope: load optional `providers.yaml` on the live draft workflow path while preserving env-only fallback
- `2026-04-06 15:11 KST` Wired `generate_drafts()` to load optional `providers.yaml` before resolving the runtime draft provider
- `2026-04-06 15:11 KST` Added workflow-level tests for config-driven provider routing and a broader `run_local_pipeline()` regression slice
- `2026-04-06 15:13 KST` Task `01` verified and implementation committed as `ff622aa` (`Wire providers config into draft workflow resolution`)
- `2026-04-06 15:19 KST` Started Task `02` on branch `codex/task-02-history-cli-parity`
- `2026-04-06 15:19 KST` Intended scope: surface policy-aware summary fields and policy skips in CLI history output without changing storage/query contracts

## Test Log
- `2026-04-06 15:02 KST` `./.venv/bin/pytest -q` -> `passed (362 passed)` while auditing current repository state before defining alignment tasks
- `2026-04-06 15:11 KST` `./.venv/bin/pytest -q tests/test_generate_drafts_workflow.py::test_generate_drafts_uses_openai_provider_when_api_key_is_present tests/test_generate_drafts_workflow.py::test_generate_drafts_honors_providers_yaml_routing_when_present tests/test_run_local_pipeline_workflow.py::test_run_local_pipeline_honors_providers_yaml_for_draft_generation` -> `passed (3 passed)`
- `2026-04-06 15:11 KST` `./.venv/bin/pytest -q tests/test_generate_drafts_workflow.py tests/test_run_local_pipeline_workflow.py` -> `passed (13 passed)`

## Blockers
- `None currently`

## Follow-up
- `Pending: confirm whether the default CLI output can stay compact while still exposing all policy-aware fields operators need`

## Completion Summary
- `Task 01 complete: live draft-generation workflows now honor optional providers.yaml routing, env-only fallback remains intact, and workflow-level tests cover both direct and broader run-local paths`
