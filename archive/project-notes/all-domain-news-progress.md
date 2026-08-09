# All-Domain News Progress

## Usage
This file is the live implementation tracker for the all-domain news roadmap.

When an autonomous agent works from [docs/all-domain-news-vibe-prompts.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-vibe-prompts.md), it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when the task is complete.

Keep updates short, factual, and current.

## Status Note
- This tracker is complete and kept as historical context.
- Active follow-on publish workflow work now lives in `docs/multichannel-manual-publish-readiness-roadmap.md`.

## Current Status
- Current milestone: `phase_1_foundation`
- Current task: `12_history_query_expansion_and_operator_docs`
- Active status: `done`
- Last updated: `2026-04-06 15:36 KST`
- Active branch: `codex/task-12-history-query-expansion-operator-docs`
- Latest task commit: `45eaf49 Finalize Task 12 progress log`

## Scope For Current Task
- Goal: `Expose policy-aware history fields for future UI/API use and document safe all-domain operator guidance`
- In scope: `History query expansion, focused history-query coverage, README/doc updates, and operator guidance for policy categories, intentional skips, Codex-Wrapper usage, and manual review`
- Out of scope: `New storage schema changes, speculative API endpoints, CLI redesign, and publish-time automation changes`

## Roadmap Status
| Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- |
| 01 | Source policy schema | done | 2026-04-05 20:52 KST | Added source policy fields with explicit defaults and focused config validation |
| 02 | Policy persistence | done | 2026-04-06 09:33 KST | Persisted source policy snapshots on source items and policy decision reasons on enrichments |
| 03 | All-domain example config | done | 2026-04-06 10:00 KST | Added sample-only config set for reusable public, corporate, and attribution-friendly news sources with a commented GDELT placeholder |
| 04 | GDELT discovery connector | done | 2026-04-06 10:28 KST | Added a discovery-only gdelt source type, request-normalizing connector, and safe sample docs |
| 05 | Policy-aware enrichment gating | done | 2026-04-06 10:41 KST | Added intentional skip handling for blocked fetch/rewrite paths in enrichment with readable persisted reasons |
| 06 | Codex-Wrapper provider | done | 2026-04-06 12:43 KST | Added an OpenAI-compatible draft provider, export wiring, and workflow compatibility coverage |
| 07 | Provider routing support | done | 2026-04-06 12:56 KST | Wired codex_wrapper into route registry and draft resolver, updated sample config, and verified mixed fallback coverage |
| 08 | All-domain prompt profiles | done | 2026-04-06 13:07 KST | Added neutral all-domain prompt profiles, sample-account selection, and attribution-aware prompt context coverage |
| 09 | Provenance visibility | done | 2026-04-06 13:23 KST | Snapshotted source origin and policy metadata onto stored drafts for review visibility |
| 10 | Domain sensitivity guardrails | done | 2026-04-06 13:46 KST | Added shared sensitivity detection plus prompt and validation guardrails for high-risk topics |
| 11 | Review scheduling validation | done | 2026-04-06 14:25 KST | Added schedule-time blockers for required attribution, restricted-source full-text reuse, and missing draft provenance |
| 12 | History query expansion and operator docs | done | 2026-04-06 14:46 KST | Added policy-aware run/failure history fields, intentional policy-skip query output, and all-domain operator docs |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `README.md`
- `app/connectors/llm/resolver.py`
- `app/storage/repositories.py`
- `app/workflows/generate_drafts.py`
- `app/workflows/history_queries.py`
- `app/workflows/run_local_pipeline.py`
- `docs/all-domain-news-operator-guide.md`
- `docs/all-domain-news-progress.md`
- `docs/finance-local-ui-data-contract.md`
- `tests/test_history_queries.py`

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
- `2026-04-06 10:21 KST` Started task `04`. Scope: `gdelt source schema, discovery connector, registry wiring, and focused docs/tests`
- `2026-04-06 10:21 KST` Created or switched branch `codex/task-04-gdelt-discovery-connector`
- `2026-04-06 10:25 KST` Added `GdeltSourceConfig` with discovery-only defaults and wired a new `GdeltSourceConnector` through the existing source registry/export surface
- `2026-04-06 10:26 KST` Updated the all-domain example sources and README so the bundled GDELT sample stays in a dedicated discovery-only source set until policy-aware enrichment gating is implemented
- `2026-04-06 10:28 KST` Added focused config, connector, and discover-workflow coverage for the new gdelt source type and request normalization path
- `2026-04-06 10:28 KST` Completed task `04` after targeted gdelt tests and the broader config/source/discovery regression slice passed
- `2026-04-06 10:37 KST` Started task `05`. Scope: `policy-aware enrichment skips for blocked fetch/rewrite paths with persisted readable reasons`
- `2026-04-06 10:37 KST` Created or switched branch `codex/task-05-policy-aware-enrichment-gating`
- `2026-04-06 10:39 KST` Updated `enrich_articles` to treat blocked full-text fetch and blocked rewrite as intentional skips, persisting readable policy reasons instead of failure codes
- `2026-04-06 10:40 KST` Added focused workflow tests covering allowed enrichment, blocked full-text fetch, blocked rewrite, and existing completed enrichments
- `2026-04-06 10:41 KST` Completed task `05` after targeted enrichment tests and a broader run-local regression slice passed
- `2026-04-06 12:38 KST` Started task `06`. Scope: `Codex-Wrapper draft-generation provider with env-based setup, OpenAI-compatible request shaping, and focused error handling`
- `2026-04-06 12:38 KST` Created or switched branch `codex/task-06-codex-wrapper-provider`
- `2026-04-06 12:40 KST` Added `CodexWrapperDraftGenerationProvider` with env-based setup for an OpenAI-compatible chat-completions endpoint, JSON-output instructions, and consistent error mapping
- `2026-04-06 12:42 KST` Exported the new provider and added focused provider/workflow coverage for env defaults, explicit overrides, malformed responses, upstream failures, and draft persistence compatibility
- `2026-04-06 12:43 KST` Completed task `06` after targeted Codex-Wrapper tests and broader OpenAI draft workflow regression tests passed
- `2026-04-06 12:51 KST` Started task `07`. Scope: `config and env-driven codex_wrapper route resolution with focused routing/resolver coverage`
- `2026-04-06 12:51 KST` Created or switched branch `codex/task-07-provider-routing-support`
- `2026-04-06 12:55 KST` Added `codex_wrapper` support to the draft route resolver and route registry, keeping env auto-detection order stable while limiting wrapper auto-registration to draft generation
- `2026-04-06 12:55 KST` Updated the bundled `config/providers.yaml` example to show `codex_wrapper` as the draft-generation route with Anthropic fallback and added focused routing/resolver tests
- `2026-04-06 12:56 KST` Completed task `07` after routing/resolver tests and draft workflow/provider regression tests passed
- `2026-04-06 13:03 KST` Started task `08`. Scope: `neutral all-domain prompt profiles, sample-account prompt selection, and focused prompt rendering coverage`
- `2026-04-06 13:03 KST` Created or switched branch `codex/task-08-all-domain-prompt-profiles`
- `2026-04-06 13:05 KST` Added neutral all-domain prompt profiles to the bundled prompt configs, kept a review-first compatibility profile in the example path, and pointed the sample all-domain account at `all_domain_factual_x_post`
- `2026-04-06 13:05 KST` Extended X draft prompt rendering with source `policy_mode` and `require_attribution` so attribution-aware templates can stay data-driven; added focused renderer, generator, and config assertions
- `2026-04-06 13:07 KST` Completed task `08` after targeted prompt, draft, and config regression tests passed
- `2026-04-06 13:17 KST` Started task `09`. Scope: `draft provenance snapshots for source origin and policy visibility`
- `2026-04-06 13:17 KST` Created or switched branch `codex/task-09-provenance-visibility`
- `2026-04-06 13:20 KST` Added draft-level provenance snapshot fields for source name, URLs, published timestamp, and policy mode; wired draft generation to persist a consistent snapshot derived from the content brief source item
- `2026-04-06 13:21 KST` Added focused workflow and storage coverage for persisted provenance snapshots plus schema-drift detection of the new draft columns
- `2026-04-06 13:23 KST` Completed task `09` after targeted provenance tests and broader draft/storage regression tests passed
- `2026-04-06 13:39 KST` Started task `10`. Scope: `lightweight domain-sensitivity detection with prompt and validation guardrails`
- `2026-04-06 13:39 KST` Created or switched branch `codex/task-10-domain-sensitivity-guardrails`
- `2026-04-06 13:45 KST` Added a shared rule-based domain-sensitivity helper for politics, finance, health, and crime-or-disaster topics; wired the new context into all-domain prompt templates and X draft generation
- `2026-04-06 13:45 KST` Added validator warnings for high-risk domains plus blocking phrase checks for finance and health claim language; updated focused renderer, generator, and validator tests
- `2026-04-06 13:46 KST` Completed task `10` after focused prompt, generator, validator, draft-workflow, and config regression tests passed
- `2026-04-06 14:19 KST` Started task `11`. Scope: `policy-aware scheduling blockers for attribution, restricted-source reuse, and missing provenance`
- `2026-04-06 14:19 KST` Created or switched branch `codex/task-11-review-scheduling-validation`
- `2026-04-06 14:23 KST` Added schedule-only draft validation rules for missing attribution, missing provenance snapshots, and restricted-source full-text reuse while leaving approval semantics unchanged
- `2026-04-06 14:24 KST` Updated review-queue fixtures and validator coverage so policy-compliant scheduling still succeeds while blocked cases fail with readable error codes
- `2026-04-06 14:25 KST` Completed task `11` after targeted validator/review-queue tests and CLI regression coverage passed
- `2026-04-06 14:39 KST` Started task `12`. Scope: `policy-aware history query fields plus all-domain operator docs`
- `2026-04-06 14:39 KST` Created or switched branch `codex/task-12-history-query-expansion-operator-docs`
- `2026-04-06 14:42 KST` Extended run and failure history helpers with policy-mode metadata, intentional policy-skip rows, and safe parsing of stored run-summary policy fields
- `2026-04-06 14:43 KST` Wired draft-generation provider names and per-run policy counts into stored run summaries without changing the database schema
- `2026-04-06 14:45 KST` Added `docs/all-domain-news-operator-guide.md`, linked it from `README.md`, and updated the UI data contract notes for policy-aware run and failure history fields
- `2026-04-06 14:46 KST` Completed task `12` after focused history-query tests and broader draft/run-local/routing regressions passed; runtime/docs implementation landed in `ff47c93` (`Expand policy-aware history queries and add operator guide`) and the task branch later finalized its tracker state in `45eaf49` (`Finalize Task 12 progress log`)

## Test Log
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py::test_sources_default_duplicate_window_days_to_thirty tests/test_config.py::test_sources_load_policy_overrides_for_supported_variants tests/test_config.py::test_invalid_source_policy_mode_raises_validation_error -q` -> `passed (3 passed)`
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py -k 'not test_registry_loads_sample_config_directory' -q` -> `passed (19 passed, 1 deselected)`
- `2026-04-05 20:51 KST` `./.venv/bin/pytest tests/test_config.py -q` -> `not clean: pre-existing failure in test_registry_loads_sample_config_directory due current config/source-set expectations mismatch; initial plain pytest invocation also hit external app import path drift outside .venv`
- `2026-04-06 09:30 KST` `./.venv/bin/pytest tests/test_storage.py::test_source_item_can_be_inserted_and_read tests/test_storage.py::test_article_enrichment_can_be_inserted_and_read tests/test_storage.py::test_article_enrichment_get_or_create_is_idempotent tests/test_storage.py::test_source_item_get_or_create_is_idempotent tests/test_storage.py::test_bootstrap_database_detects_missing_source_policy_snapshot_columns tests/test_storage.py::test_bootstrap_database_detects_missing_article_policy_reason_column tests/test_ingest_workflow.py::test_ingest_sources_persists_source_policy_snapshot_from_config -q` -> `passed (7 passed)`
- `2026-04-06 09:31 KST` `./.venv/bin/pytest tests/test_storage.py tests/test_ingest_workflow.py tests/test_history_queries.py -q` -> `passed (49 passed)`
- `2026-04-06 09:59 KST` `./.venv/bin/pytest tests/test_config.py::test_registry_loads_all_domain_example_config_directory -q` -> `passed (1 passed)`
- `2026-04-06 10:00 KST` `./.venv/bin/pytest tests/test_config.py -q` -> `passed (21 passed)`
- `2026-04-06 10:27 KST` `./.venv/bin/pytest tests/test_source_connectors.py::test_gdelt_connector_discovers_normalized_items_from_json tests/test_source_connectors.py::test_gdelt_connector_reports_invalid_json_as_parse_failure tests/test_source_connectors.py::test_gdelt_connector_allows_empty_article_lists tests/test_discover_workflow.py::test_discover_sources_runs_gdelt_connector_from_registry tests/test_config.py::test_gdelt_source_variant_loads_discovery_only_defaults tests/test_config.py::test_registry_loads_all_domain_example_config_directory -q` -> `passed (6 passed)`
- `2026-04-06 10:27 KST` `./.venv/bin/pytest tests/test_source_connectors.py tests/test_discover_workflow.py tests/test_config.py -q` -> `passed (41 passed)`
- `2026-04-06 10:40 KST` `./.venv/bin/pytest tests/test_enrich_articles_workflow.py -q` -> `passed (5 passed)`
- `2026-04-06 10:40 KST` `./.venv/bin/pytest tests/test_enrich_articles_workflow.py tests/test_run_local_pipeline_workflow.py -q` -> `passed (6 passed)`
- `2026-04-06 12:42 KST` `./.venv/bin/pytest tests/test_codex_wrapper_provider.py tests/test_generate_drafts_workflow.py::test_generate_drafts_accepts_codex_wrapper_provider -q` -> `passed (12 passed)`
- `2026-04-06 12:43 KST` `./.venv/bin/pytest tests/test_openai_llm_provider.py tests/test_generate_drafts_workflow.py -q` -> `passed (20 passed)`
- `2026-04-06 12:55 KST` `./.venv/bin/pytest tests/test_openai_llm_provider.py tests/test_phase6_config_routing.py -q` -> `passed (60 passed)`
- `2026-04-06 12:55 KST` `./.venv/bin/pytest tests/test_generate_drafts_workflow.py tests/test_codex_wrapper_provider.py -q` -> `passed (20 passed)`
- `2026-04-06 13:06 KST` `./.venv/bin/pytest tests/test_prompt_renderer.py tests/test_x_draft_generator.py tests/test_config.py::test_registry_loads_sample_config_directory tests/test_config.py::test_registry_loads_all_domain_example_config_directory -q` -> `passed (13 passed)`
- `2026-04-06 13:06 KST` `./.venv/bin/pytest tests/test_generate_drafts_workflow.py tests/test_config.py -q` -> `passed (31 passed)`
- `2026-04-06 13:21 KST` `./.venv/bin/pytest tests/test_storage.py::test_draft_variant_can_store_provenance_snapshot tests/test_storage.py::test_draft_variant_get_or_create_is_idempotent tests/test_storage.py::test_bootstrap_database_detects_missing_draft_variant_provenance_columns tests/test_generate_drafts_workflow.py::test_generate_drafts_persists_source_and_policy_provenance_on_drafts -q` -> `passed (4 passed)`
- `2026-04-06 13:22 KST` `./.venv/bin/pytest tests/test_storage.py tests/test_generate_drafts_workflow.py tests/test_x_draft_generator.py -q` -> `passed (62 passed)`
- `2026-04-06 13:45 KST` `./.venv/bin/pytest tests/test_prompt_renderer.py tests/test_x_draft_generator.py tests/test_draft_validation.py -q` -> `passed (31 passed)`
- `2026-04-06 13:45 KST` `./.venv/bin/pytest tests/test_generate_drafts_workflow.py tests/test_config.py::test_registry_loads_sample_config_directory tests/test_config.py::test_registry_loads_all_domain_example_config_directory -q` -> `passed (12 passed)`
- `2026-04-06 14:23 KST` `./.venv/bin/pytest tests/test_draft_validation.py tests/test_review_queue_workflow.py -q` -> `passed (36 passed)`
- `2026-04-06 14:24 KST` `./.venv/bin/pytest tests/test_cli.py -q` -> `passed (32 passed)`
- `2026-04-06 14:41 KST` `./.venv/bin/pytest tests/test_history_queries.py -q` -> `passed (3 passed)`
- `2026-04-06 14:42 KST` `./.venv/bin/pytest tests/test_run_local_pipeline_workflow.py tests/test_generate_drafts_workflow.py tests/test_phase6_config_routing.py -q` -> `passed (58 passed)`

## Blockers
- `None currently`

## Follow-up
- `This initiative is complete; current follow-on operator publish-lifecycle work continues in docs/multichannel-manual-publish-readiness-roadmap.md`
- `Future CLI or API surfaces can render the new policy-aware history fields directly without additional storage changes`
- `Implementation-alignment Task 03 later refreshed README and operator wording on `master` in `f86bc9c` (merged as `3327cb6`) without changing the Task 12 runtime behavior`

## Completion Summary
- `Task 12 complete: history queries now expose policy-aware run metadata plus intentional policy skips, run-local summaries record policy counts and rewrite providers, and the repository includes a dedicated all-domain operator guide`
