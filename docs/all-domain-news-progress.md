# All-Domain News Progress

## Usage
This file is the live implementation tracker for the all-domain news roadmap.

When an autonomous agent works from [docs/all-domain-news-vibe-prompts.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-vibe-prompts.md), it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when the task is complete.

Keep updates short, factual, and current.

## Current Status
- Current milestone: `phase_1_foundation`
- Current task: `01_source_policy_schema`
- Active status: `in_progress`
- Last updated: `2026-04-05 20:54 KST`
- Active branch: `codex/task-01-source-policy-schema`
- Latest task commit: `5b1db83 Add source policy fields to source config`

## Scope For Current Task
- Goal: `Add source policy metadata to config schemas with backward-compatible defaults`
- In scope: `Source config schema defaults, validation, and focused config tests`
- Out of scope: `Storage persistence, workflow gating, example config expansion`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | Source policy schema | done | 2026-04-05 20:52 KST | Added source policy fields with explicit defaults and focused config validation |
| 02 | Policy persistence | pending | - | |
| 03 | All-domain example config | pending | - | |
| 04 | GDELT discovery connector | pending | - | |
| 05 | Policy-aware enrichment gating | pending | - | |
| 06 | Codex-Wrapper provider | pending | - | |
| 07 | Provider routing support | pending | - | |
| 08 | All-domain prompt profiles | pending | - | |
| 09 | Provenance visibility | pending | - | |
| 10 | Domain sensitivity guardrails | pending | - | |
| 11 | Review scheduling validation | pending | - | |
| 12 | History query expansion and operator docs | pending | - | |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `app/config/schemas.py`
- `tests/test_config.py`
- `docs/all-domain-news-progress.md`

## Progress Log
- `2026-04-05 20:48 KST` Started task `01`. Scope: `source policy schema defaults and validation coverage`
- `2026-04-05 20:48 KST` Created or switched branch `codex/task-01-source-policy-schema`
- `2026-04-05 20:49 KST` Added source policy fields to `BaseSourceConfig` with backward-compatible defaults and string normalization
- `2026-04-05 20:50 KST` Added focused config tests for default policy values, explicit overrides, and invalid policy mode handling
- `2026-04-05 20:54 KST` Created commit `5b1db83` with message `Add source policy fields to source config`

## Test Log
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py::test_sources_default_duplicate_window_days_to_thirty tests/test_config.py::test_sources_load_policy_overrides_for_supported_variants tests/test_config.py::test_invalid_source_policy_mode_raises_validation_error -q` -> `passed (3 passed)`
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py -k 'not test_registry_loads_sample_config_directory' -q` -> `passed (19 passed, 1 deselected)`
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py -q` -> `not clean: pre-existing failure in test_registry_loads_sample_config_directory due current config/source-set expectations mismatch; initial plain pytest invocation also hit external app import path drift outside .venv`

## Blockers
- `No blocker for Task 01 completion; broader config test file still contains a pre-existing sample-config assertion mismatch unrelated to source policy schema`

## Follow-up
- `Reconcile test_registry_loads_sample_config_directory with current config/sources.yaml contents in separate cleanup work`

## Completion Summary
- `Task 01 complete: source configs now support policy metadata with explicit defaults, and focused config tests cover defaults, overrides, and invalid values`
- Commit: `5b1db83 Add source policy fields to source config`
