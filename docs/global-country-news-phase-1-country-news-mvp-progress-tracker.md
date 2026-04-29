# Global Country News Phase 1 Country News MVP Progress Tracker

## Usage
This file tracks Phase 1 work for the `korea_global_news` and `japan_global_news` MVP.

When an autonomous agent works from `docs/global-country-news-phase-1-country-news-mvp-execution-guide.md`, it should update this file before starting a task, during meaningful progress, after checks, and at completion or blocker.

## Related Files
- `docs/global-country-news-phase-1-country-news-mvp-vibe-coding-prompt.md`
- `docs/global-country-news-phase-1-country-news-mvp-roadmap.md`
- `docs/global-country-news-phase-1-country-news-mvp-execution-guide.md`
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-progress-tracker.md`

## Current Status
- Current milestone: `M3_controlled_live_smoke`
- Current task: `phase_1_korea_x_live_smoke_closeout`
- Active status: `done`
- Last updated: `2026-04-29 19:48 KST`
- Base branch: `master`
- Active branch: `codex/task-05-live-publish`
- Latest task commit: `pending`
- Resume decision: `start_phase_1_5_attribution_generation_hardening_before_repeated_operation`
- Stop reason: `korea_x_isolated_db_live_smoke_succeeded; japan_live_smoke_and_repeated_operation_pending`

## Scope For Current Task
- Goal: `Create and locally verify a placeholder-free Korea/Japan RSS config for korea_global_news and japan_global_news.`
- In scope: `active default config replacement, mirrored Phase 1 config directory, accounts, sources, prompts, providers, local validation`
- Out of scope: `blog publishing, X funnel behavior, live publish, scheduler redesign`
- Dependencies: `Phase 0 pause/source cleanup decision`
- Verification commands:
  - `rg -n 'example\\.com|example\\.org|example\\.net' config/global_country_news`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config/global_country_news`
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_phase1.db`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`

## Environment Notes
- Required services status: `network_required_for_rss_discovery`
- Env or fixture status: `X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS verified present on production and used for the controlled Korea X smoke post`
- Existing unrelated failures: `none recorded for this phase`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Create Global Country News Config Skeleton | done | 2026-04-29 18:10 KST | Added `config/global_country_news/` and mirrored the active default config to Korea/Japan country-news accounts |
| M1 | 02 | Add Korea And Japan RSS Sources | done | 2026-04-29 18:10 KST | Active sources use KBS World, Yonhap English, Korea Herald, Japan Times, and Japan Today RSS; Korea.net, The Japan News, and NHK Radio remain pruned until they return connector-clean feeds |
| M1 | 03 | Add Global Reader Prompt Profile | done | 2026-04-29 18:10 KST | Added `global_country_news_explainer` with attribution and original URL requirements |
| M2 | 04 | Generate Reviewable Drafts Locally | done | 2026-04-29 18:10 KST | Local review-only `run-local` succeeded with 1,494 pending draft variants from real RSS URLs |
| M2 | 05 | Production Dry-Run Handoff | done | 2026-04-29 19:42 KST | Isolated production DB dry-run processed exactly one due Korea X job with no state changes |
| M3 | 06 | Controlled Korea X Live Publish | done | 2026-04-29 19:45 KST | One Korea X post published through `X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS`; external_post_id `2049439510929580197` |
| M3 | 07 | Controlled Japan X Live Publish | pending | 2026-04-29 19:48 KST | Defer until attribution generation hardening and explicit Japan credential/operator approval |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `.env.example`
- `.env.production.example`
- `README.md`
- `config/accounts.yaml`
- `config/sources.yaml`
- `config/prompts.yaml`
- `config/providers.yaml`
- `config/global_country_news/accounts.yaml`
- `config/global_country_news/sources.yaml`
- `config/global_country_news/prompts.yaml`
- `config/global_country_news/providers.yaml`
- `data/ai_tools_manual.csv`
- `data/seo_tools_manual.csv`
- `tests/test_config.py`
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-progress-tracker.md`
- `docs/global-country-news-phase-1-country-news-mvp-progress-tracker.md`

## Progress Log
- `2026-04-29 16:50 KST` Initialized Phase 1 planning documents from the country-news MVP plan.
- `2026-04-29 18:00 KST` Verified RSS candidates directly before editing. KBS World, Yonhap English, Korea Herald, Japan Times, and Japan Today returned parseable RSS/Atom items.
- `2026-04-29 18:00 KST` Pruned Korea.net because it returned an unresolved CloudFront 302, The Japan News because `/feed/` returned an empty 202 body, and NHK World Radio because its podcast item has no article URL for the current normalizer.
- `2026-04-29 18:05 KST` Replaced the active default AI/SEO manual CSV config with `korea_global_news` and `japan_global_news`, and added the same config under `config/global_country_news/` for Phase 1 commands.
- `2026-04-29 18:06 KST` Removed the checked-in placeholder manual CSV files after they were no longer referenced by active config.
- `2026-04-29 18:07 KST` Tightened country matching after initial review output showed Japan Times all-feed items could include off-country global stories; matching now requires country signals instead of source-host hits.
- `2026-04-29 18:10 KST` Local `run-local` succeeded against `data/global_country_news_phase1.db`: 231 discovered, 226 saved, 5 duplicates, 166 briefs, 1,494 draft variants, 0 failures, all restricted-policy skips intentional.
- `2026-04-29 18:20 KST` Updated the one-account X verification path so `korea_global_news/x` reuses the already provisioned `X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS` bundle; `japan_global_news/x` keeps its country-news credential ref.
- `2026-04-29 19:20 KST` Production `rollout-summary` confirmed two X publisher channels and `first_rollout_x_only=true`: Korea X uses `X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS`, Japan X uses `X_JAPAN_GLOBAL_NEWS_PUBLISHER_CREDENTIALS`.
- `2026-04-29 19:30 KST` Production healthcheck passed for `config/global_country_news` against the production SQLite DB after fixing service-account DB directory ownership.
- `2026-04-29 19:42 KST` Phase 0 production cleanup gate passed: no pending, scheduled/publishing, or approved placeholder-backed reuse candidates remain; one already published placeholder job is preserved as historical evidence.
- `2026-04-29 19:42 KST` Isolated production verification DB `global_country_news_verify_20260429103002.db` was initialized and `run-local` succeeded: 232 discovered, 227 saved, 5 duplicates, 170 briefs, 1,530 draft variants, 0 failures.
- `2026-04-29 19:42 KST` First selected Korea X draft `199` correctly failed schedule validation with `required_attribution_missing`, proving the restricted-source attribution gate blocks scheduling until explicit source attribution is present.
- `2026-04-29 19:43 KST` Edited pending Korea X draft `200` to include `Source: koreaherald.com` and the real Korea Herald URL, then approved and scheduled it in the isolated verification DB.
- `2026-04-29 19:43 KST` Dry-run `publish-due` processed exactly one due job for `korea_global_news/x`, `publish_job_id=1`, with `dry_run=true` and no state changes.
- `2026-04-29 19:45 KST` Controlled live smoke published exactly one Korea X post through the configured X publisher: `external_post_id=2049439510929580197`, `published_count=1`, `failed_count=0`, `dry_run=false`.

## Test Log
- `2026-04-29 18:01 KST` `rg -n 'example\\.com|example\\.org|example\\.net' config data` -> `passed` `no active config/data placeholder URLs after removing legacy manual CSV files`
- `2026-04-29 18:02 KST` `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/global_country_news_phase1.db` -> `passed` `status=ok; accounts=2; profiles=1; sources=5`
- `2026-04-29 18:02 KST` `./.venv/bin/python -m app.cli healthcheck --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db` -> `passed` `status=ok; accounts=2; profiles=1; sources=5`
- `2026-04-29 18:02 KST` `./.venv/bin/python -m app.cli discover --config-dir config/global_country_news` -> `passed` `231 candidates from 5 sources`
- `2026-04-29 18:04 KST` `OPENAI_API_KEY= ANTHROPIC_API_KEY= CODEX_WRAPPER_API_KEY= CODEX_WRAPPER_BASE_URL= ./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db` -> `passed` `status=succeeded; discovered=231; saved=226; briefs=166; drafts=1494; failures=0`
- `2026-04-29 18:04 KST` `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_phase1.db` -> `passed` `pending drafts: 1494`
- `2026-04-29 18:04 KST` `./.venv/bin/python -m app.cli history runs --database-url sqlite:///data/global_country_news_phase1.db --limit 5` -> `passed` `run_id=1 status=succeeded; policy_modes=restricted:226; rewrite_providers=fake`
- `2026-04-29 18:05 KST` `./.venv/bin/pytest tests/test_config.py tests/test_discover_workflow.py tests/test_run_local_pipeline_workflow.py -q` -> `passed` `35 passed in 0.80s`
- `2026-04-29 18:05 KST` `./.venv/bin/pytest tests/test_prompt_renderer.py tests/test_x_draft_generator.py -q` -> `passed` `23 passed in 0.41s`
- `2026-04-29 18:05 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_cli.py -q` -> `passed` `46 passed in 1.29s`
- `2026-04-29 18:05 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-29 18:05 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-29 19:30 KST` production `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config/global_country_news --database-url sqlite:////opt/sns-content-engine/data/sns_content_engine.db` -> `passed` `check_count=3 failed_check_count=0`
- `2026-04-29 19:42 KST` production isolated `./.venv/bin/sns-engine run-local --config-dir /opt/sns-content-engine/config/global_country_news --database-url sqlite:////opt/sns-content-engine/data/global_country_news_verify_20260429103002.db` -> `passed` `status=succeeded; discovered=232; saved=227; briefs=170; drafts=1530; failures=0`
- `2026-04-29 19:42 KST` isolated `review schedule` for draft `199` -> `expected_failed` `required_attribution_missing; mention korea_herald_all_news, koreaherald.com`
- `2026-04-29 19:43 KST` isolated `review edit/approve/schedule` for draft `200` -> `passed` `Source: koreaherald.com attribution added and publish_job_id=1 scheduled`
- `2026-04-29 19:43 KST` isolated `scheduler publish-due` -> `passed` `dry_run=true; processed_count=1; failed_count=0; skipped_count=0`
- `2026-04-29 19:45 KST` isolated `scheduler publish-due --live` -> `passed` `status=published; external_post_id=2049439510929580197; published_count=1; failed_count=0`

## Open Questions
- `Should repeated Korea country-news publishing continue on the existing aitoo1news account via X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS, or move later to a dedicated Korea credential bundle?`
- `Should Japan live smoke wait for X_JAPAN_GLOBAL_NEWS_PUBLISHER_CREDENTIALS confirmation and attribution-generation hardening?`
- `The active default config now mirrors config/global_country_news/; decide whether production recurring runs should use the mirrored directory or the root config path.`
- `Korea.net, The Japan News, and NHK World Radio can be reconsidered after source-specific connector behavior is fixed or alternate feed URLs are approved.`

## Blockers
- `none_for_korea_x_controlled_live_smoke`
- `Japan X live smoke remains pending explicit credential/operator approval.`
- `Repeated operation should wait for Phase 1.5 attribution-generation hardening so operators do not need to manually add source attribution for routine schedules.`

## Follow-up
- `Start Phase 1.5 Task 00: make generated restricted-source drafts include explicit source attribution such as source name or hostname before schedule validation.`
- `After attribution generation hardening, run a fresh isolated DB run-local, approve/schedule one Korea X draft without manual source edits if possible, then dry-run.`
- `Decide whether to proceed to Japan X live smoke or first tune source quality/cadence from the Phase 1.5 plan.`

## Completion Summary
- `Phase 1 Korea X controlled smoke is complete: active config and config/global_country_news/ use real Korea/Japan RSS sources, production placeholder reuse risk was cleaned up, isolated production run-local created reviewable real-source drafts, dry-run processed exactly one Korea X job, and the live smoke published one post to https://x.com/aitoo1news with external_post_id 2049439510929580197. Japan live smoke and repeated operation remain pending Phase 1.5 hardening and explicit approval.`
