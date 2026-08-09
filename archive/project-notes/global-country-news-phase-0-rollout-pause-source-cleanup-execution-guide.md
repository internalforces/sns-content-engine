# Global Country News Phase 0 Rollout Pause Source Cleanup Execution Guide

## Purpose
This document guides an autonomous agent through Phase 0: safely pausing the placeholder-backed first rollout and preparing the source cleanup handoff.

Progress must be tracked in:
- `docs/global-country-news-phase-0-rollout-pause-source-cleanup-progress-tracker.md`

## Repository Context
The repository already has:
- dry-run-first scheduler and one-off `--live` publish path
- manual review and schedule workflow
- RSS, sitemap, manual CSV, and GDELT source connectors
- healthcheck readiness checks and secret scanning

Important files:
- `docs/first-live-rollout-operations-progress-tracker.md`
- `config/accounts.yaml`
- `config/sources.yaml`
- `data/ai_tools_manual.csv`
- `data/seo_tools_manual.csv`
- `app/operations.py`
- `app/workflows/review_queue.py`

High-signal tests:
- `tests/test_operations.py`
- `tests/test_cli.py`
- `tests/test_run_local_pipeline_workflow.py`
- `tests/test_scripts.py`

## Execution Environment
- Base branch: `master`
- Preferred branch format: `codex/phase-0-source-cleanup`
- Bootstrap commands:
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands:
  - `rg -n 'example\\.com|example\\.org|example\\.net' config data`
  - `scripts/scan_secrets.sh check`
- Broader regression commands:
  - `git diff --check`
  - `./.venv/bin/pytest tests/test_operations.py tests/test_cli.py -q`
- Required services:
  - none locally for docs/audit tasks
- Required env or fixtures:
  - production audit requires `/opt/sns-content-engine` access
- Package install policy: `not_allowed`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
- Read the roadmap and progress tracker before editing.
- Preserve the first live publish success evidence.
- Treat placeholder URL publication as a content-source blocker.
- Do not run any `--live` command.
- Do not mutate production DB or data unless a later explicit task and operator approval require it.
- Keep docs and handoff commands redacted.

## Task Rules

### Task 01: Record Rollout Pause Decision
- Inspect the current first-live rollout tracker.
- Record a Phase 0 status that says the system worked but content source data was not production-ready.
- If the operator has not made a final decision, recommend `pause`.
- Run `scripts/scan_secrets.sh check` and `git diff --check` for docs-only updates.

### Task 02: Audit Placeholder Sources
- Run local placeholder scans over active runtime config and data.
- Record whether the findings are active runtime inputs, examples, tests, or docs.
- Do not remove active placeholders until replacement source strategy is approved.
- Treat `config/sources.yaml` references to manual CSV files as active runtime inputs; scan the referenced CSV row URLs, not only YAML URL fields.

### Task 03: Add Production Source Cleanup Handoff
- Document read-only production commands:
  - scan `/opt/sns-content-engine/config`
  - scan `/opt/sns-content-engine/data`
  - inspect DB references as `sns-engine`
- Keep the commands safe and redacted.
- Do not include destructive SQL or file deletion.

Read-only production command bundle:

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

If the production query returns placeholder-backed rows, stop before approval or scheduling. Choose a cleanup path only after backup and explicit operator approval.

### Task 04: Define Phase 1 Entry Gate
- Define the minimum checklist for Phase 1:
  - approved Korea/Japan RSS source list
  - zero active placeholder URLs
  - clean `healthcheck`
  - `run-local` creates reviewable drafts
  - no live publish until dry-run shows exactly one intended due X job
- Require the production DB query from Task 03 to show no placeholder-backed scheduled, pending-review, approved, or published records that could be reused accidentally.

## Progress Tracking Rules
Update the progress tracker:
- at task start
- after local scans
- after adding any production handoff
- after verification commands
- at completion or blocker

## Master Prompt
```text
You are implementing Global Country News Phase 0 in this repository.

Read:
- docs/global-country-news-phase-0-rollout-pause-source-cleanup-roadmap.md
- docs/global-country-news-phase-0-rollout-pause-source-cleanup-execution-guide.md
- docs/global-country-news-phase-0-rollout-pause-source-cleanup-progress-tracker.md

Then inspect current rollout and source config before editing.
Choose the next unfinished task.
Preserve dry-run-first behavior, manual review, env-only secrets, and the no-second-live-command boundary.
Do not run `scheduler publish-due --live`.
```

## Output Contract
End each task with:
- Summary
- Changed files
- Tests run
- Branch and commit
- Follow-up
