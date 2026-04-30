# Global Country News Phase 1.5 Quality Hardening Progress Tracker

## Usage
This file tracks quality hardening for the Korea/Japan global news MVP.

When an autonomous agent works from `docs/global-country-news-phase-1-5-quality-hardening-execution-guide.md`, it should update this file at task start, meaningful progress, checks, completion, and blockers.

## Related Files
- `docs/global-country-news-phase-1-5-quality-hardening-vibe-coding-prompt.md`
- `docs/global-country-news-phase-1-5-quality-hardening-roadmap.md`
- `docs/global-country-news-phase-1-5-quality-hardening-execution-guide.md`
- `docs/global-country-news-phase-1-country-news-mvp-progress-tracker.md`

## Current Status
- Current milestone: `M2_draft_safety_and_cadence`
- Current task: `04_cadence_and_workload_tuning`
- Active status: `pending`
- Last updated: `2026-04-30 16:35 KST`
- Base branch: `master`
- Active branch: `codex/task-05-live-publish`
- Latest task commit: `pending`
- Resume decision: `continue_cadence_and_workload_tuning_after_sensitive_guardrails`
- Stop reason: `task_03_done`

## Scope For Current Task
- Goal: `Tune schedule, backlog, and duplicate-window settings so review-led country news does not flood the operator.`
- In scope: `X schedule review, backlog targets, duplicate windows, dry-run predictability checks, operator-facing cadence notes`
- Out of scope: `blog publishing, channel funnel, live publish automation`
- Dependencies: `Phase 1 config, Task 00 attribution generation hardening, Task 02 matching coverage baseline, Task 03 sensitive topic guardrails`
- Verification commands:
  - `./.venv/bin/pytest tests/test_scheduler.py tests/test_review_queue_workflow.py -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`

## Environment Notes
- Required services status: `network_required_for_rss_discovery`
- Env or fixture status: `Phase 1 Korea X smoke used X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS; Phase 1.5 should not require live publish`
- Existing unrelated failures: `none recorded for this phase`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M0 | 00 | Attribution Generation Hardening | done | 2026-04-29 20:09 KST | X generation now preserves/appends compact `Source: ...` attribution for `require_attribution=true` drafts while keeping the required URL and character limit |
| M1 | 01 | Source Health And Priority Review | done | 2026-04-29 22:41 KST | Live discovery found all 5 RSS sources healthy; priority and monitoring notes recorded in `config/global_country_news/sources.yaml` |
| M1 | 02 | Category And Matching Tuning | done | 2026-04-29 23:14 KST | Weak topic-only matches remain at 0; KBS `domestic`, `science`, and `inter korea` tags now preserve Korean society/legal/science/inter-Korean coverage without enabling broad `international` noise |
| M2 | 03 | Sensitive Topic Guardrails | done | 2026-04-30 16:35 KST | Lightweight detection now covers politics, security, legal, disaster, health, finance, and diplomacy; API/console review detail exposes matched terms and reviewer notes |
| M2 | 04 | Cadence And Workload Tuning | pending | 2026-04-29 16:50 KST | Tune backlog and schedules for human review |
| M2 | 05 | Operator Quality Checklist | pending | 2026-04-29 16:50 KST | Review checklist before live publishing |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files Through Task 03 Completion
- `.secrets.baseline`
- `app/api/app.py`
- `app/api/console.py`
- `app/api/templates/console/review_detail.html`
- `app/services/x_draft_generator.py`
- `app/services/draft_validation.py`
- `app/services/prompt_renderer.py`
- `app/services/topic_matching.py`
- `config/accounts.yaml`
- `config/global_country_news/accounts.yaml`
- `config/prompts.yaml`
- `config/global_country_news/prompts.yaml`
- `config/sources.yaml`
- `config/global_country_news/sources.yaml`
- `docs/operator-console-guide.md`
- `tests/test_account_matching.py`
- `tests/test_api.py`
- `tests/test_console.py`
- `tests/test_config.py`
- `tests/test_draft_validation.py`
- `tests/test_prompt_renderer.py`
- `tests/test_x_draft_generator.py`
- `docs/global-country-news-phase-1-5-quality-hardening-progress-tracker.md`

## Source Health Decisions
| Source | Decision | 2026-04-29 evidence | Follow-up |
| --- | --- | --- | --- |
| `korea_kbs_world_latest` | `primary` | 30 current items, useful politics/economy/domestic tags, no failures | Keep; use as high-signal Korea baseline |
| `korea_yonhap_english` | `secondary_wire` | 92 current items, no failures, some repeated summary/title groups and overlap with Korea Herald | Keep but monitor volume and duplicate-heavy wire updates |
| `korea_herald_all_news` | `primary_secondary` | 50 current all-news items, no failures, useful business/culture/public-interest coverage, title overlap with Yonhap | Keep; watch overlap before scheduling |
| `japan_japan_times_latest` | `primary_with_matching` | 30 current items, no failures, useful tags but includes world/sports coverage | Keep; rely on matching to retain Japan-specific stories |
| `japan_japan_today_atom` | `secondary_with_matching` | 30 current items, no failures, Atom categories unavailable and world/sports items mixed in | Keep; rely on matching and review sampling |

No source was disabled in this pass because all feeds were live and reusable with review-led matching. Pruning remains open if repeated runs show persistent low-value drafts.

## Category Coverage Decisions
| Decision | 2026-04-29 evidence | Rationale |
| --- | --- | --- |
| Keep broad country include keywords but avoid generic `president` | Earlier Task 02 pass removed weak audience/topic matches and narrowed Korea president matching to Korea-specific phrases | Reduces false positives from broad feeds while preserving country-specific political coverage |
| Add Korea source-tag matches for `domestic`, `science`, and `inter korea` | Live discovery showed KBS domestic/legal and science/inter-Korean stories were no-match despite being country-relevant; KBS matched count moved from 25 to 29 while no-match fell from 5 to 1 | These tags come from the primary KBS Korea feed and improve society/legal/science coverage without relying on newspaper-specific wording |
| Keep `international` out of Korea source tags | KBS no-match examples included non-Korea international stories such as OPEC coverage | Avoids flooding Korea review queues with general world news |

## Sensitive Topic Guardrail Decisions
| Decision | 2026-04-30 evidence | Rationale |
| --- | --- | --- |
| Split the old crime/disaster sensitivity bucket into legal and disaster cues, and add security plus diplomacy | Country-news drafts often involve courts, prosecutors, defense, missiles, summits, sanctions, and disaster updates | Operators need domain-specific review notes without adding a heavy classifier or blocking broad coverage |
| Keep high-risk domain detection as warnings unless wording is clearly unsafe | Focused validator tests now prove sensitive country-news drafts remain approvable while carrying `high_risk_domain` metadata | Guardrails should prompt careful review, not silently erase important news |
| Surface sensitivity context in API and console review detail | API and console tests now cover `sensitivity` response data and the browser-visible `민감 주제 검토` note | Reviewers can see matched terms, guidance, and what to verify before approving |

## Progress Log
- `2026-04-29 16:50 KST` Initialized Phase 1.5 planning documents from the country-news quality hardening plan.
- `2026-04-29 19:42 KST` Phase 1 isolated production run-local created real Korea/Japan drafts: 232 discovered, 227 saved, 5 duplicates, 170 briefs, 1,530 draft variants, 0 failures.
- `2026-04-29 19:42 KST` Korea X draft `199` failed schedule validation with `required_attribution_missing`, proving the scheduling gate works for restricted-source attribution requirements.
- `2026-04-29 19:43 KST` Korea X draft `200` passed after an operator edit added `Source: koreaherald.com` plus the real Korea Herald URL; dry-run processed exactly one due job.
- `2026-04-29 19:45 KST` Controlled Korea X live smoke succeeded through `X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS`, external_post_id `2049439510929580197`.
- `2026-04-29 19:48 KST` Reframed Phase 1.5 first task to attribution generation hardening before broader source quality and cadence work.
- `2026-04-29 20:00 KST` Implemented restricted-source X attribution post-processing in `XDraftGenerator`; generated X drafts now append or preserve a compact `Source: ...` cue before the required article URL when `require_attribution=true`.
- `2026-04-29 20:00 KST` Updated the global country news prompt to explicitly reserve X attribution room before the URL.
- `2026-04-29 20:06 KST` Initialized isolated quality DB and started `run-local`; full run was stopped after extended external-provider wait, but partial draft generation produced 123 Japan review drafts with required X source attribution present.
- `2026-04-29 20:07 KST` Verified no-edit review flow on isolated draft `1`: approve passed, schedule passed, and dry-run `publish-due` processed exactly one X job.
- `2026-04-29 20:09 KST` Tightened overlong X compaction so existing attribution cues are deduplicated before appending the canonical source cue.
- `2026-04-29 20:09 KST` Refreshed `.secrets.baseline`; diff only moved the existing `tests/test_x_draft_generator.py` finding line number and generated timestamp after test insertions.
- `2026-04-29 22:39 KST` Ran live source discovery for Task 01: 232 candidates from 5 RSS sources, 0 failures; counts were KBS 30, Yonhap 92, Korea Herald 50, Japan Times 30, Japan Today 30.
- `2026-04-29 22:40 KST` Classified all five sources as keepable, with KBS and Japan Times as primary baselines, Yonhap and Japan Today as volume/broad-feed sources needing review-led monitoring, and Korea Herald as useful but overlap-prone.
- `2026-04-29 22:41 KST` Started Task 02 matching tuning based on source-health evidence: audience words from account topics no longer become topic keywords, and Korea `president` matching was narrowed to Korea-specific phrases.
- `2026-04-29 22:41 KST` Rechecked matching after tuning: Korea eligible counts are Herald 38, KBS 25, Yonhap 87; Japan eligible counts are Japan Times 11 and Japan Today 9; weak topic-only matches dropped to 0.
- `2026-04-29 22:42 KST` Refreshed `.secrets.baseline` after test line-number changes; final secret scan passed.
- `2026-04-29 23:14 KST` Completed Task 02 category coverage review: added KBS-backed Korea `domestic`, `science`, and `inter korea` source tags while keeping broad `international` excluded; active root `config/` now mirrors `config/global_country_news/` again for the attribution prompt and source notes.
- `2026-04-29 23:14 KST` Rechecked live discovery matching after category tuning: 232 candidates, 0 failures; KBS matched 29/no-match 1, Yonhap 87/no-match 5, Korea Herald 38/no-match 12, Japan Times 11/no-match 19, Japan Today 9/no-match 21.
- `2026-04-30 16:30 KST` Started Task 03 sensitive topic guardrails: expanded lightweight sensitivity detection beyond politics/finance/health into security, legal, disaster, and diplomacy, and started surfacing review notes in the API and console review detail context.
- `2026-04-30 16:35 KST` Completed Task 03 sensitive topic guardrails: prompt guidance now asks high-risk country-news drafts to keep dates, numbers, legal status, official statements, and attribution reviewer-checkable; validator warnings now carry review notes; API and console review detail expose sensitivity cues.

## Test Log
- `2026-04-29 19:42 KST` production isolated `run-local` -> `passed` `status=succeeded; drafts=1530; failures=0`
- `2026-04-29 19:42 KST` isolated `review schedule` for draft `199` -> `expected_failed` `required_attribution_missing`
- `2026-04-29 19:43 KST` isolated `review edit/approve/schedule` for draft `200` -> `passed` `manual Source attribution allowed scheduling`
- `2026-04-29 19:43 KST` isolated `scheduler publish-due` -> `passed` `dry_run=true; processed_count=1`
- `2026-04-29 19:45 KST` isolated `scheduler publish-due --live` -> `passed` `published_count=1; external_post_id=2049439510929580197`
- `2026-04-29 20:00 KST` `./.venv/bin/python -m app.cli version` -> `passed` `sns-content-engine 0.1.0`
- `2026-04-29 20:00 KST` `./.venv/bin/pytest tests/test_x_draft_generator.py -q` -> `passed` `20 passed`
- `2026-04-29 20:01 KST` `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py -q` -> `passed` `71 passed`
- `2026-04-29 20:02 KST` `./.venv/bin/python -m app.cli db init --database-url sqlite:///data/global_country_news_quality.db` -> `passed`
- `2026-04-29 20:06 KST` `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_quality.db` -> `interrupted_after_external_wait` `partial output: 123 pending Japan drafts; pipeline_runs row remained running with zero counters`
- `2026-04-29 20:06 KST` `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_quality.db` -> `passed` `pending drafts: 123`
- `2026-04-29 20:07 KST` `review approve 1`, `review schedule 1`, `scheduler publish-due` on isolated DB -> `passed` `dry_run=true; processed_count=1; no body edit`
- `2026-04-29 20:08 KST` `./.venv/bin/pytest tests/test_generate_drafts_workflow.py tests/test_run_local_pipeline_workflow.py -q` -> `passed` `17 passed`
- `2026-04-29 20:08 KST` `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py tests/test_generate_drafts_workflow.py tests/test_run_local_pipeline_workflow.py -q` -> `passed` `89 passed`
- `2026-04-29 20:09 KST` `scripts/scan_secrets.sh check` -> `passed` after `scripts/scan_secrets.sh refresh-baseline`
- `2026-04-29 20:09 KST` `git diff --check` -> `passed`
- `2026-04-29 20:10 KST` final rerun of `pytest` focused workflow set, `scripts/scan_secrets.sh check`, and `git diff --check` -> `passed`
- `2026-04-29 20:11 KST` `./.venv/bin/pytest tests/test_x_draft_generator.py tests/test_prompt_renderer.py -q`, `scripts/scan_secrets.sh check`, and `git diff --check` -> `passed`
- `2026-04-29 22:39 KST` `./.venv/bin/python -m app.cli discover --config-dir config/global_country_news` -> `passed` `232 candidates; 0 failures`
- `2026-04-29 22:42 KST` `./.venv/bin/pytest tests/test_account_matching.py tests/test_config.py -q` -> `passed` `35 passed`
- `2026-04-29 22:42 KST` `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py -q` -> `passed` `72 passed`
- `2026-04-29 22:43 KST` `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_account_matching.py tests/test_config.py -q` -> `passed` `126 passed`
- `2026-04-29 22:43 KST` `scripts/scan_secrets.sh check` -> `passed`
- `2026-04-29 22:43 KST` `git diff --check` -> `passed`
- `2026-04-29 23:14 KST` `./.venv/bin/python -m app.cli discover --config-dir config/global_country_news` -> `passed` `232 candidates; 0 failures`
- `2026-04-29 23:14 KST` `./.venv/bin/pytest tests/test_account_matching.py tests/test_config.py -q` -> `passed` `36 passed`
- `2026-04-29 23:14 KST` `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_account_matching.py tests/test_config.py -q` -> `passed` `127 passed`
- `2026-04-29 23:15 KST` `scripts/scan_secrets.sh refresh-baseline`, `scripts/scan_secrets.sh check`, and `git diff --check` -> `passed`
- `2026-04-30 16:31 KST` `./.venv/bin/pytest tests/test_prompt_renderer.py tests/test_draft_validation.py -q` -> `passed` `34 passed`
- `2026-04-30 16:31 KST` focused API/console review-detail sensitivity tests -> `passed` `4 passed`
- `2026-04-30 16:33 KST` `./.venv/bin/python -m app.cli version` -> `passed` `sns-content-engine 0.1.0`
- `2026-04-30 16:33 KST` `./.venv/bin/python -m app.cli discover --config-dir config/global_country_news` -> `passed` `229 candidates from 5 sources; KBS 30, Yonhap 89, Korea Herald 50, Japan Times 30, Japan Today 30`
- `2026-04-30 16:33 KST` `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_account_matching.py tests/test_config.py tests/test_prompt_renderer.py tests/test_api.py::test_review_detail_endpoint_returns_full_draft_context tests/test_api.py::test_review_detail_endpoint_returns_sensitive_topic_context tests/test_console.py::test_review_detail_page_renders_sensitive_topic_review_note -q` -> `passed` `141 passed`
- `2026-04-30 16:34 KST` `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q` -> `passed` `81 passed`
- `2026-04-30 16:35 KST` `scripts/scan_secrets.sh refresh-baseline`, `scripts/scan_secrets.sh check`, and `git diff --check` -> `passed`

## Open Questions
- `Which sources generate useful unique items after several production runs?`
- `What daily draft volume can the operator review comfortably?`

## Blockers
- `none_for_task_04_start`

## Follow-up
- `Start Task 04 cadence and workload tuning before recurring production runs.`
- `Use the isolated partial Japan draft set and the 2026-04-29 discovery sample as initial review evidence, but run a clean full quality DB pipeline when the external draft provider is responsive.`
- `Run the no-edit approve/schedule/dry-run check on a fresh Korea X draft once the next full isolated run completes.`

## Completion Summary
- `Task 00 is complete. Restricted-source X generation now retains a source attribution candidate by default, keeps the required URL, fits the X character budget, and passed no-edit approve/schedule/dry-run verification on an isolated Japan X draft. Task 01 is complete for the first live RSS pass: all five sources were healthy, priority/monitoring notes were recorded, and no source was disabled. Task 02 is complete for the first category pass: weak topic-only matches remain removed, Korea primary-source domestic/science/inter-Korean coverage is restored, broad international noise remains excluded, and root config mirrors the explicit country-news config again. Task 03 is complete: country-news sensitivity detection now covers politics, security, legal, disaster, health, finance, and diplomacy; high-risk warnings carry reviewer guidance; and API/console review detail surfaces sensitivity notes without changing manual review or live publish boundaries.`
