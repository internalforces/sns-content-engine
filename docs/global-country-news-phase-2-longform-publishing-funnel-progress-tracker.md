# Global Country News Phase 2 Longform Publishing Funnel Progress Tracker

## Usage
This file tracks Phase 2 work for long-form blog/newsletter publishing while preserving source-linked social draft behavior.

When an autonomous agent works from `docs/global-country-news-phase-2-longform-publishing-funnel-execution-guide.md`, it should update this file at task start, meaningful progress, checks, completion, and blockers.

## Related Files
- `docs/global-country-news-phase-2-longform-publishing-funnel-vibe-coding-prompt.md`
- `docs/global-country-news-phase-2-longform-publishing-funnel-roadmap.md`
- `docs/global-country-news-phase-2-longform-publishing-funnel-execution-guide.md`
- `docs/global-country-news-phase-1-5-quality-hardening-progress-tracker.md`
- `docs/global-country-news-phase-2-longform-platform-strategy.md`

## Current Status
- Current milestone: `M4_social_source_link_guardrail`
- Current task: `06_confirm_original_source_social_links`
- Active status: `done`
- Last updated: `2026-05-11 11:12 KST`
- Base branch: `master`
- Active branch: `codex/task-05-live-publish`
- Latest task commit: `pending`
- Resume decision: `operator_decided_social_links_remain_original_source`
- Stop reason: `tasks_01_to_06_completed_with_social_original_source_guardrail`

## Scope For Current Task
- Goal: `Keep social drafts pointed to the original article URL while Ghost long-form handoff remains separate.`
- In scope: `document original-source decision, preserve prompt URL selection, add regression coverage for social channels`
- Out of scope: `blog-funnel URL selector, forcing social channels through Ghost, community automation, live Ghost API publishing`
- Dependencies: `Task 05 manual Ghost handoff and final URL recording`
- Verification commands:
  - `./.venv/bin/pytest tests/test_x_draft_generator.py tests/test_draft_validation.py tests/test_review_queue_workflow.py -q`
  - `git diff --check`

## Environment Notes
- Required services status: `not_required_for_strategy`
- Env or fixture status: `platform credentials not needed until an integration task`
- Existing unrelated failures: `none recorded for this phase`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Choose Longform Platform Strategy | done | 2026-05-10 21:24 KST | Ghost selected as primary owned home; WordPress fallback; first rollout is manual handoff, then Ghost dry-run adapter before live API publishing |
| M1 | 02 | Design Longform Draft Model | done | 2026-05-10 21:35 KST | First slice reuses `DraftVariant` for single-source Ghost long-form drafts and existing `PublishJob`/`PublishLog` manual handoff rows; multi-source daily briefs are deferred until explicit provenance schema |
| M2 | 03 | Add Longform Prompt And Generation Flow | done | 2026-05-10 21:35 KST | Added `ghost` long-form prompt constraints and deterministic fake-provider long-form output; active country-news config now includes review-led Ghost drafts |
| M2 | 04 | Expose Longform Review Or Handoff | done | 2026-05-10 21:35 KST | Existing review queue/API/console surfaces now handle Ghost as manual handoff through the same pending-review and publish-job lifecycle |
| M3 | 05 | Add First Platform Handoff Or Adapter | done | 2026-05-10 21:35 KST | Added manual Ghost handoff and final Ghost URL recording through manual publish completion; no live Ghost API adapter or credentials added |
| M4 | 06 | Confirm Original-Source Social Links | done | 2026-05-11 11:08 KST | Operator decided social drafts should keep pointing at original article URLs; blog-funnel mode is not part of this phase |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files Through Task 06 Completion
- `app/connectors/llm/fake.py`
- `app/connectors/publishers/resolver.py`
- `app/services/x_draft_generator.py`
- `app/workflows/review_queue.py`
- `.secrets.baseline`
- `config/accounts.yaml`
- `config/global_country_news/accounts.yaml`
- `config/prompts.yaml`
- `config/global_country_news/prompts.yaml`
- `docs/global-country-news-phase-2-longform-platform-strategy.md`
- `docs/global-country-news-phase-2-longform-publishing-funnel-progress-tracker.md`
- `docs/operator-console-guide.md`
- `docs/operator-control-plane-api.md`
- `docs/global-country-news-phase-2-longform-publishing-funnel-vibe-coding-prompt.md`
- `docs/global-country-news-phase-2-longform-publishing-funnel-roadmap.md`
- `docs/global-country-news-phase-2-longform-publishing-funnel-execution-guide.md`
- `tests/test_config.py`
- `tests/test_generate_drafts_workflow.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_x_draft_generator.py`

## Platform Strategy Decisions
| Decision | Value | Notes |
| --- | --- | --- |
| Primary owned home | `Ghost` | Canonical long-form URL and first future API candidate |
| Fallback owned home | `WordPress` | Use if operator prefers existing WordPress hosting, SEO, or plugin ecosystem |
| First rollout mode | `manual_handoff_first` | Approved long-form content is copied to Ghost manually; external URL is recorded after operator confirmation |
| First adapter mode | `ghost_dry_run_before_live` | Future Ghost adapter must support dry-run before live API publishing |
| Newsletter distribution | `Substack manual`, `beehiiv later candidate` | Substack is not selected for programmatic posting; beehiiv create-post API access is beta/Enterprise-gated |
| Professional distribution | `LinkedIn Newsletter manual handoff` | Preserve existing manual review and handoff semantics |
| Community distribution | `manual_only` | No Reddit or Hacker News automation |

## Model And Handoff Decisions
| Decision | Value | Notes |
| --- | --- | --- |
| First long-form draft type | `single_story_explainer` | Uses one existing `content_brief` and its source provenance |
| First storage shape | `DraftVariant(channel="ghost")` | Additive reuse; no schema migration required for the single-source slice |
| Manual handoff storage | `PublishJob` / `PublishLog` | Approval creates a scheduled-state manual handoff with `scheduled_for=None` |
| Final Ghost URL field | `PublishJob.external_post_id` | Existing manual completion route records the Ghost article URL here |
| Multi-source briefs | `deferred_schema_needed` | Daily/country briefs need explicit multi-source provenance before implementation |

## Social URL Decision
| Decision | Value | Notes |
| --- | --- | --- |
| Social link target | `original_article_url` | X, Threads, and LinkedIn drafts continue to use the source article URL selected from article enrichment or `landing.strategy: source` |
| Ghost URL usage | `handoff_record_only` | Final Ghost URLs may be recorded on manual publish jobs, but they do not replace social draft URLs in this phase |
| Blog-funnel mode | `not_in_phase` | Any future blog-funnel selector needs a separate opt-in task with explicit storage, validation, and review semantics |

## Progress Log
- `2026-04-29 16:50 KST` Initialized Phase 2 planning documents from the long-form publishing and distribution plan.
- `2026-05-10 21:24 KST` Started Phase 2 from an explicit operator request despite Phase 1 Japan live smoke still pending; Phase 1.5 quality hardening is complete and this task has no external side effects.
- `2026-05-10 21:24 KST` Completed Task 01 platform strategy: selected Ghost as primary, WordPress as fallback, manual Ghost handoff as the first rollout mode, Ghost dry-run adapter as the later API path, and manual-only boundaries for Substack, LinkedIn Newsletter, Medium, Reddit, and Hacker News.
- `2026-05-10 21:35 KST` Completed Task 02 model design with an additive first slice: `ghost` long-form drafts reuse `DraftVariant`, manual Ghost handoffs reuse `PublishJob`/`PublishLog`, and multi-source daily briefs remain deferred until explicit provenance schema.
- `2026-05-10 21:35 KST` Completed Task 03 generation flow: added Ghost long-form prompt constraints, fake-provider article-shaped output, and active Korea/Japan `ghost` channel config with 12,000 character cap and 8-link review allowance.
- `2026-05-10 21:35 KST` Completed Task 04 review exposure by reusing existing pending-review, approve/reject/edit, API, console, and publish-job surfaces for Ghost manual handoffs.
- `2026-05-10 21:35 KST` Completed Task 05 first platform handoff in manual mode: approving Ghost creates a manual handoff, schedule rejects Ghost as manual-only, and manual completion records the final Ghost article URL. No live adapter or credentials were added.
- `2026-05-11 11:08 KST` Completed Task 06 by recording the operator decision to keep X, Threads, and LinkedIn pointed at original article URLs, updating Phase 2 docs, and adding social-channel regression coverage for original URL selection.

## Test Log
- `2026-04-29 16:50 KST` `not_run` `phase_waiting_for_phase_1_and_phase_1_5`
- `2026-05-10 21:24 KST` `./.venv/bin/python -m app.cli version` -> `passed` `sns-content-engine 0.1.0`
- `2026-05-10 21:24 KST` `scripts/scan_secrets.sh check` -> `passed`
- `2026-05-10 21:24 KST` `git diff --check` -> `passed`
- `2026-05-10 21:35 KST` `./.venv/bin/python -m app.cli healthcheck --config-dir config/global_country_news` -> `passed` `status=ok; accounts=2; profiles=1; sources=5`
- `2026-05-10 21:35 KST` `diff -u config/accounts.yaml config/global_country_news/accounts.yaml` and `diff -u config/prompts.yaml config/global_country_news/prompts.yaml` -> `passed`
- `2026-05-10 21:35 KST` `./.venv/bin/pytest tests/test_x_draft_generator.py tests/test_generate_drafts_workflow.py tests/test_review_queue_workflow.py tests/test_config.py -q` -> `passed` `98 passed`
- `2026-05-10 21:35 KST` `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q` -> `passed` `81 passed`
- `2026-05-10 21:41 KST` `./.venv/bin/pytest tests/test_storage.py tests/test_review_queue_workflow.py -q` -> `passed` `81 passed`
- `2026-05-10 21:41 KST` `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_generate_drafts_workflow.py tests/test_run_local_pipeline_workflow.py tests/test_config.py -q` -> `passed` `94 passed`
- `2026-05-10 21:41 KST` `./.venv/bin/pytest -q` -> `passed` `557 passed`
- `2026-05-10 21:41 KST` `scripts/scan_secrets.sh refresh-baseline && scripts/scan_secrets.sh check` -> `passed`
- `2026-05-10 21:41 KST` `git diff --check` -> `passed`
- `2026-05-11 11:12 KST` `./.venv/bin/pytest tests/test_x_draft_generator.py tests/test_draft_validation.py tests/test_review_queue_workflow.py -q` -> `passed` `81 passed`
- `2026-05-11 11:12 KST` `git diff --check` -> `passed`

## Open Questions
- `What source-count limit and grouping rules should a future multi-source country daily brief use?`

## Blockers
- `none_for_tasks_01_to_06`
- `Phase 1 Japan live smoke remains pending, but the operator explicitly requested Phase 2 work and Task 01 had no external side effects.`

## Follow-up
- `Open a separate opt-in task only if the operator later wants social drafts to link to Ghost URLs; that task needs explicit storage, validation, and review semantics.`

## Completion Summary
- `Tasks 01 through 06 are complete for the first safe Phase 2 slice. Ghost is the selected primary long-form home, WordPress is the fallback, single-source Ghost article drafts are generated into pending review, Ghost approval creates a manual publish handoff, and the operator can record the final Ghost URL after manual publication. X, Threads, and LinkedIn remain independent social drafts that point to original article URLs. No external integration credentials, live Ghost API posting, blog-funnel selector, or community automation were added.`
