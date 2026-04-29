# Global Country News Phase 1.5 Quality Hardening Execution Guide

## Purpose
This document guides quality hardening after the Korea/Japan country-news MVP can generate reviewable drafts and at least one controlled X live post has been proven.

Progress must be tracked in:
- `docs/global-country-news-phase-1-5-quality-hardening-progress-tracker.md`

## Repository Context
Important files:
- `config/global_country_news/`
- `app/services/x_draft_generator.py`
- `app/services/draft_validation.py`
- `app/workflows/review_queue.py`
- `app/scheduler/planner.py`
- `docs/all-domain-news-operator-guide.md`

High-signal tests:
- `tests/test_draft_validation.py`
- `tests/test_x_draft_generator.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_scheduler.py`
- `tests/test_run_local_pipeline_workflow.py`

## Execution Environment
- Base branch: `master`
- Preferred branch format:
  - `codex/task-01-source-quality`
  - `codex/task-03-sensitive-guardrails`
- Narrow verification commands:
  - `./.venv/bin/python -m app.cli discover --config-dir config/global_country_news`
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_quality.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_quality.db`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py tests/test_scheduler.py -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Package install policy: `not_allowed`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
- Do not add blog or funnel behavior in Phase 1.5.
- Do not change the live publish approval boundary.
- Do not make LinkedIn automatically publish.
- Prefer config, prompt, and validation refinements before new architecture.
- Record source quality decisions in docs so future operators know why a source was kept or removed.

## Task Guidance

### Attribution Generation
- Start here after the Korea X live smoke evidence from 2026-04-29.
- The observed failure was useful: `review schedule` rejected draft `199` with `required_attribution_missing` until an operator edited another draft to include `Source: koreaherald.com`.
- Keep the validation gate intact; improve generation so restricted-source drafts naturally mention a source candidate such as source name or hostname.
- Preserve the required article/source URL and X character limit.
- Verify that a fresh restricted-source Korea X draft can be approved and scheduled without manual attribution edits.

### Source Health
- Run discovery and inspect source item counts, failures, duplicate patterns, and feed quality.
- Prune feeds that return non-article content, stale items, or excessive duplicates.
- Keep official and reputable sources but do not assume every official feed is reusable for full-text rewriting.

### Category Tuning
- Keep broad coverage.
- Avoid overfitting to a single category such as politics or finance.
- Use source sets and matching config first; only add code if existing config cannot express the desired behavior.

### Sensitive Topics
- Treat politics, legal, security, disasters, health, finance, and diplomacy as review-sensitive.
- Prompts should explain uncertainty and avoid speculation.
- Validation should block missing attribution and provenance before scheduling.

### Cadence
- Start with low backlog targets.
- Ensure dry-run does not produce multiple unintended due X jobs.
- Keep country accounts one-at-a-time for live rollout decisions.

## Progress Tracking Rules
Update the tracker when:
- attribution-generation behavior changes or a schedule gate failure is analyzed
- source health observations are made
- prompts or config are changed
- tests run
- a source is disabled or demoted
- cadence changes

## Master Prompt
```text
You are implementing Global Country News Phase 1.5 quality hardening.

Read:
- docs/global-country-news-phase-1-5-quality-hardening-roadmap.md
- docs/global-country-news-phase-1-5-quality-hardening-execution-guide.md
- docs/global-country-news-phase-1-5-quality-hardening-progress-tracker.md

Inspect the Phase 1 config and generated drafts before editing.
Choose the smallest unfinished task. If the 2026-04-29 Korea X smoke evidence has not been addressed, start with attribution generation hardening.
Preserve manual review, dry-run-first publishing, and independent channel drafts.
Do not add blog or funnel behavior in this phase.
```

## Output Contract
End each task with:
- Summary
- Changed files
- Tests run
- Branch and commit
- Follow-up
