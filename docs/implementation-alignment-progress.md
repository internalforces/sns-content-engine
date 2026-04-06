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
- Current task: `03_readme_and_operator_wording_refresh`
- Active status: `done`
- Last updated: `2026-04-06 15:33 KST`
- Active branch: `codex/task-03-readme-operator-wording-refresh`
- Latest task commit: `pending Task 04 metadata refresh after commit creation`

## Scope For Current Task
- Goal: `Refresh README and operator-facing docs so they describe the aligned provider-routing, history CLI, and policy-skip behavior accurately`
- In scope: `README wording, all-domain operator guidance, and nearby factual doc updates tied directly to the aligned runtime behavior`
- Out of scope: `Runtime refactors, new CLI features, broad historical doc rewrites, and unrelated roadmap expansion`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | Provider config runtime wiring | done | 2026-04-06 15:13 KST | Live draft workflows now load optional `providers.yaml` and still fall back to env-only resolution |
| 02 | Policy-aware history CLI parity | done | 2026-04-06 15:24 KST | CLI history output now exposes policy-aware run fields and intentional policy skips |
| 03 | README and operator wording refresh | done | 2026-04-06 15:33 KST | README and all-domain operator docs now describe live provider routing, policy skips, and CLI history output accurately |
| 04 | Progress metadata cleanup | pending | 2026-04-06 15:02 KST | Progress log commit metadata should be refreshed after alignment work lands |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `README.md`
- `docs/all-domain-news-operator-guide.md`
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
- `2026-04-06 15:23 KST` Updated `history runs` to show policy skip counts, attribution-required counts, policy-mode counts, and rewrite providers from existing query fields
- `2026-04-06 15:23 KST` Updated `history failures` to print both real failures and intentional policy skips with explicit row types for operator visibility
- `2026-04-06 15:23 KST` Expanded CLI coverage in `tests/test_cli.py` to verify the richer history output shape
- `2026-04-06 15:24 KST` Task `02` verified; progress metadata will capture the resulting commit SHA during Task `04` because the task-completion commit does not know its own hash in advance
- `2026-04-06 15:30 KST` Started Task `03` on branch `codex/task-03-readme-operator-wording-refresh`
- `2026-04-06 15:30 KST` Intended scope: refresh README and operator-facing docs so provider routing, policy skips, and history CLI wording match current runtime behavior
- `2026-04-06 15:32 KST` Updated `README.md` so live draft-provider routing, env fallback behavior, history CLI output, and GDELT discovery wording match the current runtime path
- `2026-04-06 15:32 KST` Updated `docs/all-domain-news-operator-guide.md` so operators can see the real history row types and how `providers.yaml` routing behaves at runtime
- `2026-04-06 15:33 KST` Task `03` verified as a docs-only slice; no code-path tests were needed beyond `git diff --check`, and Task `04` will refresh the resulting commit metadata after commit creation

## Test Log
- `2026-04-06 15:02 KST` `./.venv/bin/pytest -q` -> `passed (362 passed)` while auditing current repository state before defining alignment tasks
- `2026-04-06 15:11 KST` `./.venv/bin/pytest -q tests/test_generate_drafts_workflow.py::test_generate_drafts_uses_openai_provider_when_api_key_is_present tests/test_generate_drafts_workflow.py::test_generate_drafts_honors_providers_yaml_routing_when_present tests/test_run_local_pipeline_workflow.py::test_run_local_pipeline_honors_providers_yaml_for_draft_generation` -> `passed (3 passed)`
- `2026-04-06 15:11 KST` `./.venv/bin/pytest -q tests/test_generate_drafts_workflow.py tests/test_run_local_pipeline_workflow.py` -> `passed (13 passed)`
- `2026-04-06 15:23 KST` `./.venv/bin/pytest -q tests/test_cli.py -k 'history_runs_command or history_failures_command'` -> `passed (2 passed)`
- `2026-04-06 15:23 KST` `./.venv/bin/pytest -q tests/test_cli.py` -> `passed (32 passed)`
- `2026-04-06 15:23 KST` `./.venv/bin/pytest -q tests/test_history_queries.py tests/test_cli.py -k 'history'` -> `passed (5 passed)`
- `2026-04-06 15:32 KST` `git diff --check` -> `passed`

## Blockers
- `None currently`

## Follow-up
- `Task 04 remains next: refresh latest-commit metadata and other stale factual tracker fields after the latest alignment commits land`
- `Task 04 should refresh latest-commit metadata once subsequent alignment commits have landed`

## Completion Summary
- `Task 03 complete: README and all-domain operator docs now match the aligned provider-routing, policy-skip, and history CLI behavior without broad documentation rewrites`
