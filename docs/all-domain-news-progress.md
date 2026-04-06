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
- Current task: `03_all_domain_example_config`
- Active status: `done`
- Last updated: `2026-04-06 10:00 KST`
- Active branch: `codex/task-03-all-domain-example-config`
- Latest task commit: `Add all-domain example config samples`

## Scope For Current Task
- Goal: `Add a sample all-domain config directory that demonstrates safe source policy usage`
- In scope: `New example config files, sample-only documentation, and config-loading validation for the bundled example`
- Out of scope: `New connector types, policy-aware workflow gating, and provider routing changes`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | Source policy schema | done | 2026-04-05 20:52 KST | Added source policy fields with explicit defaults and focused config validation |
| 02 | Policy persistence | done | 2026-04-06 09:33 KST | Persisted source policy snapshots on source items and policy decision reasons on enrichments |
| 03 | All-domain example config | done | 2026-04-06 10:00 KST | Added sample-only config set for reusable public, corporate, and attribution-friendly news sources with a commented GDELT placeholder |
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
- `config/examples/all_domain_news/accounts.yaml`
- `config/examples/all_domain_news/prompts.yaml`
- `config/examples/all_domain_news/sources.yaml`
- `README.md`
- `tests/test_config.py`
- `docs/all-domain-news-progress.md`

## Progress Log
- `2026-04-05 20:48 KST` Started task `01`. Scope: `source policy schema defaults and validation coverage`
- `2026-04-05 20:48 KST` Created or switched branch `codex/task-01-source-policy-schema`
- `2026-04-05 20:49 KST` Added source policy fields to `BaseSourceConfig` with backward-compatible defaults and string normalization
- `2026-04-05 20:50 KST` Added focused config tests for default policy values, explicit overrides, and invalid policy mode handling
- `2026-04-05 20:54 KST` Created commit `5b1db83` with message `Add source policy fields to source config`
- `2026-04-06 09:22 KST` Started task `02`. Scope: `persist policy snapshots on source items and decision-reason fields for enrichment records`
- `2026-04-06 09:22 KST` Created or switched branch `codex/task-02-policy-persistence`
- `2026-04-06 09:29 KST` Added source policy snapshot fields to `SourceItem` and a `policy_decision_reason` field to `ArticleEnrichment`; updated storage schema validation requirements
- `2026-04-06 09:29 KST` Wired `ingest_sources` to persist source policy values from config onto saved source items
- `2026-04-06 09:30 KST` Added focused storage and ingest tests for policy persistence, idempotent reads, and schema drift detection
- `2026-04-06 09:33 KST` Completed task `02` after targeted storage, ingest, and history query tests passed
- `2026-04-06 09:56 KST` Started task `03`. Scope: `all-domain sample config directory, sample-only docs note, and bundled config validation`
- `2026-04-06 09:56 KST` Created or switched branch `codex/task-03-all-domain-example-config`
- `2026-04-06 09:58 KST` Added `config/examples/all_domain_news/` sample config files covering reusable public feeds, reusable corporate IR/newsroom feeds, attribution-friendly Wikinews-style settings, and a commented future GDELT placeholder
- `2026-04-06 09:59 KST` Documented bundled example-config intent in `README.md` and added focused config-registry coverage for the new example directory; aligned an outdated root sample source-set expectation with current bundled config
- `2026-04-06 10:00 KST` Completed task `03` after targeted and full config tests passed

## Test Log
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py::test_sources_default_duplicate_window_days_to_thirty tests/test_config.py::test_sources_load_policy_overrides_for_supported_variants tests/test_config.py::test_invalid_source_policy_mode_raises_validation_error -q` -> `passed (3 passed)`
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py -k 'not test_registry_loads_sample_config_directory' -q` -> `passed (19 passed, 1 deselected)`
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py -q` -> `not clean: pre-existing failure in test_registry_loads_sample_config_directory due current config/source-set expectations mismatch; initial plain pytest invocation also hit external app import path drift outside .venv`
- `2026-04-06 09:30 KST` `./.venv/bin/pytest tests/test_storage.py::test_source_item_can_be_inserted_and_read tests/test_storage.py::test_article_enrichment_can_be_inserted_and_read tests/test_storage.py::test_article_enrichment_get_or_create_is_idempotent tests/test_storage.py::test_source_item_get_or_create_is_idempotent tests/test_storage.py::test_bootstrap_database_detects_missing_source_policy_snapshot_columns tests/test_storage.py::test_bootstrap_database_detects_missing_article_policy_reason_column tests/test_ingest_workflow.py::test_ingest_sources_persists_source_policy_snapshot_from_config -q` -> `passed (7 passed)`
- `2026-04-06 09:31 KST` `./.venv/bin/pytest tests/test_storage.py tests/test_ingest_workflow.py tests/test_history_queries.py -q` -> `passed (49 passed)`
- `2026-04-06 09:59 KST` `./.venv/bin/pytest tests/test_config.py::test_registry_loads_all_domain_example_config_directory -q` -> `passed (1 passed)`
- `2026-04-06 10:00 KST` `./.venv/bin/pytest tests/test_config.py -q` -> `passed (21 passed)`

## Blockers
- `None currently`

## Follow-up
- `Task 04 can implement the gdelt connector and uncomment the placeholder example source once that type is supported`

## Completion Summary
- `Task 03 complete: added a sample-only all-domain config set, documented that bundled examples do not replace the active default config, and verified the new example directory loads cleanly`
