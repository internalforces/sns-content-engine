# Global Country News Phase 1.5 Quality Hardening Vibe Coding Prompt

## Purpose
This document is the kickoff brief for hardening the Korea/Japan global news MVP after the first controlled X posts work.

Use it when you want an autonomous coding agent to improve source quality, duplicate control, category coverage, sensitivity handling, and cadence before expanding into long-form publishing.

## Generated Document Naming
- Vibe coding prompt file: `docs/global-country-news-phase-1-5-quality-hardening-vibe-coding-prompt.md`
- Roadmap file: `docs/global-country-news-phase-1-5-quality-hardening-roadmap.md`
- Execution guide file: `docs/global-country-news-phase-1-5-quality-hardening-execution-guide.md`
- Progress tracker file: `docs/global-country-news-phase-1-5-quality-hardening-progress-tracker.md`

## Initiative Brief
- Initiative name: `Global Country News Phase 1.5 Quality Hardening`
- One-sentence outcome: `Make the Korea/Japan global news MVP reliable enough for repeated review-led operation without changing the Phase 1 publishing model.`
- Why this matters now:
  - Phase 1 proves real RSS sourcing and first-post publishing, but repeated operation needs better quality controls.
  - Country news includes politics, disasters, legal, security, finance, and public-interest topics that need stricter review cues.
- Primary owner:
  - operator reviewing daily drafts
  - autonomous agent tightening config, prompts, validation, and docs
- Core workflow to improve:
  - required source attribution generation for restricted-source drafts
  - source prioritization and pruning
  - duplicate and near-duplicate avoidance
  - sensitive topic guardrails
  - schedule and backlog tuning
- Explicit non-goals:
  - no blog publishing
  - no cross-channel funnel
  - no auto-approval
  - no broad NLP classifier rewrite unless a small config/test slice proves necessary

## Repository Context
The repository already has:
- source policy fields and attribution validation
- duplicate windows in channel validation
- domain sensitivity prompt guidance
- pipeline run and failure history
- dry-run and manual review gates

Most recent Phase 1 evidence:
- Production placeholder cleanup gate passed with no pending/scheduled/approved placeholder reuse candidates.
- Isolated production `run-local` created Korea/Japan reviewable drafts.
- The first Korea X schedule attempt failed as intended with `required_attribution_missing`.
- A manually edited Korea X draft with `Source: koreaherald.com` passed approve/schedule/dry-run.
- One controlled live X smoke post succeeded via `X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS`, external_post_id `2049439510929580197`.

Important files and patterns:
- Config: `config/global_country_news/`
- Prompting: `app/services/x_draft_generator.py`, `app/services/prompt_renderer.py`
- Validation: `app/services/draft_validation.py`, `app/workflows/review_queue.py`
- Matching: `app/services/account_matcher.py`, `app/domain/source_ingestion.py`
- Tests: `tests/test_draft_validation.py`, `tests/test_x_draft_generator.py`, `tests/test_run_local_pipeline_workflow.py`, `tests/test_review_queue_workflow.py`

## Product Intent And Quality Bar
The desired implementation should:
- make required source attribution appear naturally in restricted-source X drafts before scheduling
- reduce low-value or repetitive news drafts
- keep attribution clear and source names visible
- make sensitive topic review cues obvious
- tune cadence so operators are not flooded
- keep Phase 1 independent channel structure intact

The agent should preserve:
- real source URLs
- manual review before schedule
- dry-run-first publishing
- LinkedIn manual handoff
- no blog/funnel behavior

The agent should avoid:
- weakening the existing attribution validation gate
- hiding sensitive topics by silently dropping everything
- overfitting to one newspaper's wording
- adding a heavy ranking subsystem before simple config rules are exhausted
- changing live publish behavior

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands:
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_quality.db`
  - `./.venv/bin/python -m app.cli history runs --database-url sqlite:///data/global_country_news_quality.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_quality.db`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Required services:
  - network access for live RSS source verification
- Required env:
  - same draft provider config as Phase 1
- Package install policy: `not_allowed`
- Push and PR policy: `do_not_push_without_explicit_request`

## First-Pass Definition Of Done
- source set quality rules are documented and tested where code changes occur
- prompts clearly target overseas readers without speculation
- sensitive and high-risk topic handling is visible to reviewers
- cadence/backlog settings are tuned for review-led operation
- no live publish command is required to complete this phase

## Prompt Template
```text
You are implementing Global Country News Phase 1.5 quality hardening.

Read:
- docs/global-country-news-phase-1-5-quality-hardening-vibe-coding-prompt.md
- docs/global-country-news-phase-1-5-quality-hardening-roadmap.md
- docs/global-country-news-phase-1-5-quality-hardening-execution-guide.md
- docs/global-country-news-phase-1-5-quality-hardening-progress-tracker.md

Improve source attribution generation, source quality, duplicate control, sensitive topic review cues, and cadence for the Korea/Japan global news MVP.
Start with attribution generation hardening if it is still unfinished, because the first Korea X smoke required a manual source-attribution edit before scheduling.
Do not add blog publishing or X funnel behavior.
Do not weaken manual review or dry-run-first publishing.
```
