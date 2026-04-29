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
- Current milestone: `M2_reviewable_drafts`
- Current task: `05_production_dry_run_handoff`
- Active status: `blocked`
- Last updated: `2026-04-29 18:10 KST`
- Base branch: `master`
- Active branch: `codex/task-05-live-publish`
- Latest task commit: `pending`
- Resume decision: `local_phase1_gate_verified`
- Stop reason: `production_placeholder_audit_and_cleanup_approval_required_before_live`

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
- Env or fixture status: `draft provider env needed for production-quality generation; fake provider may be used for local shape tests if no provider is configured`
- Existing unrelated failures: `none recorded for this phase`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Create Global Country News Config Skeleton | done | 2026-04-29 18:10 KST | Added `config/global_country_news/` and mirrored the active default config to Korea/Japan country-news accounts |
| M1 | 02 | Add Korea And Japan RSS Sources | done | 2026-04-29 18:10 KST | Active sources use KBS World, Yonhap English, Korea Herald, Japan Times, and Japan Today RSS; Korea.net, The Japan News, and NHK Radio remain pruned until they return connector-clean feeds |
| M1 | 03 | Add Global Reader Prompt Profile | done | 2026-04-29 18:10 KST | Added `global_country_news_explainer` with attribution and original URL requirements |
| M2 | 04 | Generate Reviewable Drafts Locally | done | 2026-04-29 18:10 KST | Local review-only `run-local` succeeded with 1,494 pending draft variants from real RSS URLs |
| M2 | 05 | Production Dry-Run Handoff | blocked | 2026-04-29 18:10 KST | Wait for production placeholder audit/cleanup decision before any approval, scheduling, dry-run handoff, or live command |
| M3 | 06 | Controlled Korea X Live Publish | pending | 2026-04-29 16:50 KST | One Korea X post after explicit approval |
| M3 | 07 | Controlled Japan X Live Publish | pending | 2026-04-29 16:50 KST | One Japan X post after explicit approval |

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

## Open Questions
- `Production cleanup path is still undecided: fresh DB baseline, reject/cancel stale records, or targeted exclusion must wait for read-only production audit evidence, backup, and explicit operator approval.`
- `The active default config now mirrors config/global_country_news/; production can deploy either path, but must not approve, schedule, dry-run, or live publish until Phase 0 production DB audit is clean or cleanup is approved and completed.`
- `Korea.net, The Japan News, and NHK World Radio can be reconsidered after source-specific connector behavior is fixed or alternate feed URLs are approved.`

## Blockers
- `Production placeholder scan and DB inspection have not been executed in this local workspace.`
- `Production DB cleanup method has no approval yet; no mutation command was added or run.`
- `No country-news approval, scheduling, dry-run handoff, or live publish should start until production placeholder state is clean.`

## Follow-up
- `Run the Phase 0 read-only production audit bundle on the server and capture DB findings.`
- `After backup and explicit operator approval, choose and execute the production cleanup path for any placeholder-backed records.`
- `Only after cleanup passes, run production healthcheck and review-only run-local before preparing the one-job X dry-run handoff.`

## Completion Summary
- `Local Phase 1 config and reviewable-draft gates are complete: active config and config/global_country_news/ now use real Korea/Japan RSS sources, no placeholder URLs remain under config data, healthcheck passes, and review-only run-local created 1,494 pending draft variants without live publishing. Production cleanup remains the blocking gate.`
