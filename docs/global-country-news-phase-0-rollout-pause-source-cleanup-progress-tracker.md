# Global Country News Phase 0 Rollout Pause Source Cleanup Progress Tracker

## Usage
This file tracks Phase 0 work: pausing the placeholder-backed rollout and preparing safe source cleanup before country-news config work begins.

When an autonomous agent works from `docs/global-country-news-phase-0-rollout-pause-source-cleanup-execution-guide.md`, it should update this file before starting a task, after meaningful progress, after checks, and at completion or blocker.

## Related Files
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-vibe-coding-prompt.md`
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-roadmap.md`
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-execution-guide.md`
- `docs/first-live-rollout-operations-progress-tracker.md`

## Current Status
- Current milestone: `M1_pause_and_audit`
- Current task: `production_placeholder_audit_handoff`
- Active status: `blocked`
- Last updated: `2026-04-29 18:10 KST`
- Base branch: `master`
- Active branch: `codex/task-05-live-publish`
- Latest task commit: `pending`
- Resume decision: `phase_1_local_source_gate_verified`
- Stop reason: `production_placeholder_audit_and_cleanup_required_before_next_live_run`

## Scope For Current Task
- Goal: `Keep the first live rollout paused until active placeholder source data is removed locally and audited in production.`
- In scope: `decision capture, local placeholder-source verification, production handoff planning, local source replacement evidence`
- Out of scope: `production DB mutation, approval/scheduling, a second live publish`
- Dependencies: `operator confirmation that the posted URL used example.com; production shell access for server-side source and DB audit`
- Verification commands:
  - `rg -n 'example\\.com|example\\.org|example\\.net' config data`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`

## Environment Notes
- Required services status: `not_required_for_docs_and_audit`
- Env or fixture status: `production access required for /opt/sns-content-engine config/data/DB audit execution`
- Existing unrelated failures: `none recorded for this phase`
- No-live boundary: `preserved; no scheduler publish-due --live command was run during Phase 0`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Record Rollout Pause Decision | done | 2026-04-29 17:30 KST | First live publish remains a technical success; next operating decision is `pause` until source cleanup passes |
| M1 | 02 | Audit Placeholder Sources | done | 2026-04-29 18:10 KST | Local audit first found active manual CSV placeholders; Phase 1 replacement removed those active config/data placeholders locally |
| M1 | 03 | Add Production Source Cleanup Handoff | done | 2026-04-29 17:30 KST | Read-only production config/data scan and DB inspection commands are documented |
| M1 | 04 | Define Phase 1 Entry Gate | done | 2026-04-29 17:30 KST | Phase 1 is gated on real Korea/Japan sources, zero active placeholders, clean healthcheck, and review-only dry run |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `app/operations.py`
- `tests/test_operations.py`
- `tests/test_cli.py`
- `.secrets.baseline`
- `docs/first-live-rollout-operations-progress-tracker.md`
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-roadmap.md`
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-execution-guide.md`
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-progress-tracker.md`

## Progress Log
- `2026-04-29 16:50 KST` Initialized Phase 0 planning documents from the global country news rollout plan.
- `2026-04-29 17:30 KST` Read the first-live rollout tracker and recorded the post-publish operating decision as `pause` rather than content-quality approval.
- `2026-04-29 17:30 KST` Local placeholder scan found four active runtime URLs in checked-in manual CSV data: `data/ai_tools_manual.csv:2`, `data/ai_tools_manual.csv:3`, `data/seo_tools_manual.csv:2`, and `data/seo_tools_manual.csv:3`.
- `2026-04-29 17:30 KST` Confirmed `config/sources.yaml` references `../data/ai_tools_manual.csv` and `../data/seo_tools_manual.csv`, so the CSV placeholders are active inputs, not only examples or docs.
- `2026-04-29 17:30 KST` Added a targeted healthcheck guardrail so manual CSV URL rows are inspected for `example.com`, `example.org`, and `example.net` placeholder hosts.
- `2026-04-29 17:30 KST` Added a read-only production handoff for config/data scanning, SQLite placeholder inspection as `sns-engine`, and a clean healthcheck rerun.
- `2026-04-29 17:30 KST` Defined the Phase 1 entry gate: approved Korea/Japan RSS sources, zero active placeholders locally and in production DB state, clean healthcheck, review-only `run-local`, and no live publish until a later explicit approval.
- `2026-04-29 17:45 KST` Re-read the Phase 0 prompt, roadmap, execution guide, progress tracker, and first-live rollout tracker before making any update.
- `2026-04-29 17:45 KST` Re-ran the local placeholder audit and confirmed the same four active runtime CSV placeholder URLs remain present.
- `2026-04-29 17:45 KST` Re-ran local guardrail checks; healthcheck still fails for the intended placeholder-source reason, while secret scan, focused tests, script tests, and diff whitespace checks pass.
- `2026-04-29 18:06 KST` Phase 1 replaced the active checked-in AI/SEO manual CSV source path with Korea/Japan RSS sources and removed the legacy placeholder CSV files from `data/`.
- `2026-04-29 18:10 KST` Re-ran the local placeholder scan over `config data`; no `example.com`, `example.org`, or `example.net` references remain in active config/data.
- `2026-04-29 18:10 KST` Active config and `config/global_country_news/` now pass healthcheck against `data/global_country_news_phase1.db`; production DB cleanup remains blocked pending read-only server audit, backup, and operator approval.

## Local Placeholder Audit
- Active runtime config references:
  - `config/sources.yaml` now references Korea/Japan RSS sources only.
  - `config/global_country_news/sources.yaml` mirrors the same Korea/Japan RSS source set.
- Active runtime placeholder rows:
  - `none after Phase 1 local source replacement`
- Intentional docs-only references:
  - Phase 0 docs mention `example.com` as the stop reason and audit target.
- Current local healthcheck result:
  - `passed` for `config` and `config/global_country_news` against `sqlite:///data/global_country_news_phase1.db`.

## Read-Only Production Handoff
Run only inside the production server shell. These commands inspect state and do not mutate files or DB rows:

```bash
cd /opt/sns-content-engine
rg -n 'example\.com|example\.org|example\.net' /opt/sns-content-engine/config /opt/sns-content-engine/data
sudo -u sns-engine sqlite3 'file:/opt/sns-content-engine/data/sns_content_engine.db?mode=ro' <<'SQL'
.headers on
.mode column
SELECT 'source_items' AS table_name, id, source_key, source_url AS url, state
FROM source_items
WHERE source_url LIKE '%example.com%' OR source_url LIKE '%example.org%' OR source_url LIKE '%example.net%';
SELECT 'article_enrichments' AS table_name, id, source_item_id, article_url AS url
FROM article_enrichments
WHERE article_url LIKE '%example.com%' OR article_url LIKE '%example.org%' OR article_url LIKE '%example.net%';
SELECT 'content_briefs' AS table_name, id, source_item_id, account_key, landing_url AS url
FROM content_briefs
WHERE landing_url LIKE '%example.com%' OR landing_url LIKE '%example.org%' OR landing_url LIKE '%example.net%';
SELECT 'draft_variants' AS table_name, id, content_brief_id, channel, state, source_url AS url, article_url
FROM draft_variants
WHERE source_url LIKE '%example.com%' OR source_url LIKE '%example.org%' OR source_url LIKE '%example.net%'
   OR article_url LIKE '%example.com%' OR article_url LIKE '%example.org%' OR article_url LIKE '%example.net%'
   OR body LIKE '%example.com%' OR body LIKE '%example.org%' OR body LIKE '%example.net%';
SELECT 'publish_jobs' AS table_name, publish_jobs.id, publish_jobs.channel, publish_jobs.state, draft_variants.id AS draft_variant_id, draft_variants.source_url AS url
FROM publish_jobs
JOIN draft_variants ON draft_variants.id = publish_jobs.draft_variant_id
WHERE draft_variants.source_url LIKE '%example.com%' OR draft_variants.source_url LIKE '%example.org%' OR draft_variants.source_url LIKE '%example.net%'
   OR draft_variants.article_url LIKE '%example.com%' OR draft_variants.article_url LIKE '%example.org%' OR draft_variants.article_url LIKE '%example.net%'
   OR draft_variants.body LIKE '%example.com%' OR draft_variants.body LIKE '%example.org%' OR draft_variants.body LIKE '%example.net%';
SQL
sudo -u sns-engine bash -lc 'cd /opt/sns-content-engine && ./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config --database-url sqlite:////opt/sns-content-engine/data/sns_content_engine.db'
```

If any query returns rows, keep the rollout paused. Do not delete, update, reject, cancel, approve, schedule, or publish until the operator chooses a cleanup path after backup.

## Test Log
- `2026-04-29 17:30 KST` `rg -n 'example\\.com|example\\.org|example\\.net' config data docs/first-live-rollout-operations-progress-tracker.md docs/global-country-news-phase-0-rollout-pause-source-cleanup-*.md` -> `passed` `found four active CSV placeholder rows plus intentional Phase 0 docs references`
- `2026-04-29 17:30 KST` `./.venv/bin/python -m app.cli version` -> `passed` `sns-content-engine 0.1.0`
- `2026-04-29 17:30 KST` `./.venv/bin/python -m app.cli healthcheck --config-dir config` -> `expected_failed` `config_readiness now flags four active manual CSV placeholder URLs`
- `2026-04-29 17:30 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_cli.py -q` -> `passed` `46 passed in 1.02s`
- `2026-04-29 17:33 KST` `scripts/scan_secrets.sh check` -> `blocked` `baseline was out of date because the added CLI test shifted an existing test fixture finding line number`
- `2026-04-29 17:33 KST` `scripts/scan_secrets.sh refresh-baseline` -> `passed` `updated only the existing tests/test_cli.py baseline line number and generated_at timestamp`
- `2026-04-29 17:34 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-29 17:34 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-29 17:34 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_cli.py -q` -> `passed` `46 passed in 1.12s`
- `2026-04-29 17:34 KST` `scripts/scan_secrets.sh check docs/global-country-news-phase-0-rollout-pause-source-cleanup-*.md` -> `passed` `no output; exit code 0`
- `2026-04-29 17:45 KST` `rg -n 'example\\.com|example\\.org|example\\.net' config data docs/first-live-rollout-operations-progress-tracker.md docs/global-country-news-phase-0-rollout-pause-source-cleanup-*.md` -> `passed` `found the same four active CSV placeholder rows plus intentional Phase 0 docs references`
- `2026-04-29 17:45 KST` `./.venv/bin/python -m app.cli version` -> `passed` `sns-content-engine 0.1.0`
- `2026-04-29 17:45 KST` `./.venv/bin/python -m app.cli healthcheck --config-dir config` -> `expected_failed` `config_readiness flags four active manual CSV placeholder URLs`
- `2026-04-29 17:45 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-29 17:45 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-29 17:45 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_cli.py -q` -> `passed` `46 passed in 1.02s`
- `2026-04-29 17:45 KST` `./.venv/bin/pytest tests/test_run_local_pipeline_workflow.py tests/test_scripts.py -q` -> `passed` `8 passed in 3.90s`
- `2026-04-29 18:01 KST` `rg -n 'example\\.com|example\\.org|example\\.net' config data` -> `passed` `no output; exit code 1`
- `2026-04-29 18:02 KST` `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/global_country_news_phase1.db` -> `passed` `status=ok; accounts=2; profiles=1; sources=5`
- `2026-04-29 18:02 KST` `./.venv/bin/python -m app.cli healthcheck --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db` -> `passed` `status=ok; accounts=2; profiles=1; sources=5`
- `2026-04-29 18:04 KST` `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db` -> `passed` `status=succeeded; drafts=1494; failures=0`
- `2026-04-29 18:05 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-29 18:05 KST` `git diff --check` -> `passed` `no output; exit code 0`

## Open Questions
- `Will production placeholder cleanup use a fresh DB baseline, rejected/cancelled stale drafts, or targeted replacement after backup?`
- `Local Korea/Japan RSS replacement is complete; production deployment path and persisted placeholder cleanup still depend on server audit evidence.`

## Blockers
- `Production placeholder scan and DB inspection have not been executed in this local workspace.`
- `Production DB cleanup method has not been approved and no mutation command has been documented or run.`
- `No approval, scheduling, production dry-run handoff, or second live publish should start until the production audit is clean or cleanup is explicitly approved and completed.`

## Follow-up
- `Run the read-only production handoff, capture results, and choose the cleanup path for any placeholder-backed production records.`
- `Deploy the country-news config only after production placeholder state is clean or cleanup is approved and completed.`

## Completion Summary
- `Local Phase 0 source cleanup gate is verified: the first live rollout remains paused, active checked-in placeholder config/data has been replaced with Korea/Japan RSS sources, healthcheck passes locally, and production cleanup remains handed off as read-only audit plus backup and explicit approval before any mutation.`
