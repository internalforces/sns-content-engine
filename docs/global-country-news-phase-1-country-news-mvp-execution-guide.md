# Global Country News Phase 1 Country News MVP Execution Guide

## Purpose
This document guides implementation of the Phase 1 country news MVP: two accounts, real RSS sources, reviewable drafts, and controlled one-post X live verification.

Progress must be tracked in:
- `docs/global-country-news-phase-1-country-news-mvp-progress-tracker.md`

## Repository Context
The repository already has:
- RSS discovery and source normalization
- pipeline execution through `run-local`
- all-domain news example config
- prompt rendering and channel draft generation
- manual review, scheduling, and dry-run publish

Important files:
- `config/examples/all_domain_news/sources.yaml`
- `config/examples/all_domain_news/accounts.yaml`
- `config/examples/all_domain_news/prompts.yaml`
- `app/workflows/run_local_pipeline.py`
- `app/workflows/build_content_briefs.py`
- `app/workflows/generate_drafts.py`
- `app/services/x_draft_generator.py`
- `app/connectors/sources/rss.py`

High-signal tests:
- `tests/test_config.py`
- `tests/test_discover_workflow.py`
- `tests/test_run_local_pipeline_workflow.py`
- `tests/test_x_draft_generator.py`
- `tests/test_cli.py`

## Execution Environment
- Base branch: `master`
- Preferred branch format:
  - `codex/task-01-global-country-config`
  - `codex/task-04-country-news-drafts`
- Narrow verification commands:
  - `rg -n 'example\\.com|example\\.org|example\\.net' config/global_country_news`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config/global_country_news`
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_phase1.db`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_config.py tests/test_discover_workflow.py tests/test_run_local_pipeline_workflow.py -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Required services:
  - network access for live RSS discovery
- Required env:
  - draft provider credentials for non-fake generation
  - X credentials only during the explicit production live task
- Package install policy: `not_allowed`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
- Preserve the current structure: X, Threads, and LinkedIn are separate drafts from the same source brief.
- Keep `landing.strategy: source`.
- Do not add blog or funnel behavior in Phase 1.
- Do not auto-approve, auto-schedule, or auto-publish.
- Keep LinkedIn manual handoff.
- Keep Threads manual fallback unless a separate approved Threads rollout changes it.
- Do not run `--live` outside the explicit controlled live tasks.

## Task Execution Notes

### Config Tasks
- Prefer copying the shape of `config/examples/all_domain_news/` rather than inventing a new config schema.
- Use `strict_topic_guard: false` for broad country news.
- Use `require_attribution: true`.
- Start with conservative publisher-source policy:
  - `policy_mode: restricted`
  - `allow_full_text_fetch: false`
  - `allow_llm_rewrite: false`
- If a source is official and explicitly reusable, document the rationale before enabling full-text fetch.

### Prompt Tasks
- Use one shared prompt profile first: `global_country_news_explainer`.
- Require:
  - what happened
  - why it matters outside the country
  - enough local context
  - natural source attribution
  - original article URL
- Avoid:
  - partisan framing
  - speculation
  - sensational language
  - investment advice or unsupported predictions

### Local Pipeline Tasks
- Use a dedicated local DB path such as `sqlite:///data/global_country_news_phase1.db`.
- If the DB already exists and blocks clean verification, record whether you reused or recreated it.
- Inspect `history failures` as well as `review list`; policy skips can be expected for restricted sources.

### Production Live Tasks
- Run one country account at a time.
- Before approval, summarize:
  - deployed revision
  - healthcheck result
  - dry-run due-job count
  - account and channel scope
  - source URL in the candidate draft
- Accept only explicit one-command approval.
- Stop after one live command and record external X observation.

## Progress Tracking Rules
Update the progress tracker at:
- task start
- config creation
- source discovery result
- draft generation result
- every production dry-run or live gate
- final task status

## Master Prompt
```text
You are implementing Global Country News Phase 1 in this repository.

Read:
- docs/global-country-news-phase-1-country-news-mvp-roadmap.md
- docs/global-country-news-phase-1-country-news-mvp-execution-guide.md
- docs/global-country-news-phase-1-country-news-mvp-progress-tracker.md

Then inspect the current config examples and workflows before editing.
Choose the next unfinished task and keep it additive.
Do not run live publishing unless the current task is a controlled live publish and the operator has approved the exact command.
```

## Output Contract
End each task with:
- Summary
- Changed files
- Tests run
- Branch and commit
- Follow-up
