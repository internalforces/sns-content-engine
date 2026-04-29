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
- Current milestone: `M0_smoke_followup`
- Current task: `00_attribution_generation_hardening`
- Active status: `pending`
- Last updated: `2026-04-29 19:48 KST`
- Base branch: `master`
- Active branch: `codex/task-05-live-publish`
- Latest task commit: `pending`
- Resume decision: `start_attribution_generation_hardening`
- Stop reason: `phase_1_korea_x_live_smoke_succeeded_but_manual_attribution_edit_was_required`

## Scope For Current Task
- Goal: `Harden restricted-source draft generation so source attribution is present before scheduling without routine manual edits.`
- In scope: `attribution prompt/generator behavior, X max-char preservation, required URL preservation, validation tests, isolated DB dry-run evidence`
- Out of scope: `blog publishing, channel funnel, live publish automation`
- Dependencies: `Phase 1 config, production cleanup gate, Korea X live smoke evidence`
- Verification commands:
  - `./.venv/bin/pytest tests/test_x_draft_generator.py tests/test_draft_validation.py tests/test_review_queue_workflow.py -q`
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_quality.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_quality.db`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`

## Environment Notes
- Required services status: `network_required_for_rss_discovery`
- Env or fixture status: `Phase 1 Korea X smoke used X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS; Phase 1.5 should not require live publish`
- Existing unrelated failures: `none recorded for this phase`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M0 | 00 | Attribution Generation Hardening | pending | 2026-04-29 19:48 KST | First Korea X schedule gate required a manual `Source: koreaherald.com` edit; generation should include required attribution by default |
| M1 | 01 | Source Health And Priority Review | pending | 2026-04-29 19:48 KST | Start after attribution generation no longer forces routine manual edits |
| M1 | 02 | Category And Matching Tuning | pending | 2026-04-29 16:50 KST | Keep broad country coverage balanced |
| M2 | 03 | Sensitive Topic Guardrails | pending | 2026-04-29 16:50 KST | Politics, security, legal, disaster, health, finance |
| M2 | 04 | Cadence And Workload Tuning | pending | 2026-04-29 16:50 KST | Tune backlog and schedules for human review |
| M2 | 05 | Operator Quality Checklist | pending | 2026-04-29 16:50 KST | Review checklist before live publishing |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `docs/global-country-news-phase-1-5-quality-hardening-roadmap.md`
- `docs/global-country-news-phase-1-5-quality-hardening-execution-guide.md`
- `docs/global-country-news-phase-1-5-quality-hardening-vibe-coding-prompt.md`
- `docs/global-country-news-phase-1-5-quality-hardening-progress-tracker.md`

## Progress Log
- `2026-04-29 16:50 KST` Initialized Phase 1.5 planning documents from the country-news quality hardening plan.
- `2026-04-29 19:42 KST` Phase 1 isolated production run-local created real Korea/Japan drafts: 232 discovered, 227 saved, 5 duplicates, 170 briefs, 1,530 draft variants, 0 failures.
- `2026-04-29 19:42 KST` Korea X draft `199` failed schedule validation with `required_attribution_missing`, proving the scheduling gate works for restricted-source attribution requirements.
- `2026-04-29 19:43 KST` Korea X draft `200` passed after an operator edit added `Source: koreaherald.com` plus the real Korea Herald URL; dry-run processed exactly one due job.
- `2026-04-29 19:45 KST` Controlled Korea X live smoke succeeded through `X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS`, external_post_id `2049439510929580197`.
- `2026-04-29 19:48 KST` Reframed Phase 1.5 first task to attribution generation hardening before broader source quality and cadence work.

## Test Log
- `2026-04-29 19:42 KST` production isolated `run-local` -> `passed` `status=succeeded; drafts=1530; failures=0`
- `2026-04-29 19:42 KST` isolated `review schedule` for draft `199` -> `expected_failed` `required_attribution_missing`
- `2026-04-29 19:43 KST` isolated `review edit/approve/schedule` for draft `200` -> `passed` `manual Source attribution allowed scheduling`
- `2026-04-29 19:43 KST` isolated `scheduler publish-due` -> `passed` `dry_run=true; processed_count=1`
- `2026-04-29 19:45 KST` isolated `scheduler publish-due --live` -> `passed` `published_count=1; external_post_id=2049439510929580197`

## Open Questions
- `Should attribution formatting be "Source: hostname", source display name, or a compact phrase that varies by channel?`
- `Should generated X drafts always reserve character budget for attribution when require_attribution is true?`
- `Which sources generate useful unique items after several production runs?`
- `What daily draft volume can the operator review comfortably?`

## Blockers
- `none_for_task_00_start`

## Follow-up
- `Implement Task 00 by updating prompt/generator behavior and tests so restricted-source X drafts preserve URL, fit 280 characters, and include an attribution candidate without manual edits.`
- `After Task 00, run a fresh isolated DB run-local and attempt approve/schedule/dry-run for one Korea X draft without manual body editing.`
- `Then continue Task 01 source health and priority review before Japan live smoke or recurring production runs.`

## Completion Summary
- `Phase 1.5 is ready to start from attribution generation hardening. The Korea X live smoke succeeded, but the first schedule attempt showed generated restricted-source drafts may still require manual attribution edits.`
