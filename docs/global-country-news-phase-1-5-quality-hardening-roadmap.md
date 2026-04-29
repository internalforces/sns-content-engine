# Global Country News Phase 1.5 Quality Hardening Roadmap

## Goal
Harden the Phase 1 country news MVP so repeated operation:
- favors higher-quality source items
- avoids duplicate or low-value drafts
- highlights sensitive topics for careful review
- keeps operator workload manageable

## Generated Document Naming
- Roadmap file: `docs/global-country-news-phase-1-5-quality-hardening-roadmap.md`
- Execution guide file: `docs/global-country-news-phase-1-5-quality-hardening-execution-guide.md`
- Progress tracker file: `docs/global-country-news-phase-1-5-quality-hardening-progress-tracker.md`
- Vibe coding prompt file: `docs/global-country-news-phase-1-5-quality-hardening-vibe-coding-prompt.md`

## Current Implementation Snapshot

### Already Implemented
- Phase 1 config should provide real Korea/Japan RSS inputs.
- Draft validation can enforce attribution and provenance.
- The prompt layer already has domain sensitivity support.
- Channel config has duplicate windows and schedule settings.

### Current Limitations Relevant To The New Goal
- Broad RSS feeds can produce repetitive wire coverage.
- Some categories may be overrepresented.
- Sensitive topics need clearer review guidance.
- Backlog and schedule settings may not match real operator capacity.

## Environment And Execution Assumptions
- Base branch: `master`
- Depends on completed or mostly-complete Phase 1 config in `config/global_country_news/`
- Narrow verification commands:
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_quality.db`
  - `./.venv/bin/python -m app.cli history failures --database-url sqlite:///data/global_country_news_quality.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_quality.db`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_draft_validation.py tests/test_x_draft_generator.py tests/test_review_queue_workflow.py -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`

## Target Architecture

### Quality Configuration Layer
- source priority notes and pruning criteria
- category and keyword balancing
- channel duplicate window tuning
- backlog target and schedule tuning

### Review Safety Layer
1. Drafts keep source attribution.
2. Sensitive topic prompts add caution and context.
3. Reviewers can see why a draft exists and what to verify.
4. No automatic live escalation is introduced.

## Milestones

### Milestone M1: Source Quality And Coverage
- Goal: prune or prioritize sources so generated drafts are useful.
- Includes:
  - source health observations
  - category coverage review
  - source-specific notes
- Excludes:
  - new connectors
  - blog aggregation
- Ship when:
  - source list is stable enough for repeated review runs

### Milestone M2: Draft Safety And Cadence
- Goal: make review safer and workload predictable.
- Includes:
  - prompt refinements
  - sensitivity notes
  - duplicate and schedule tuning
- Excludes:
  - live automation changes
- Ship when:
  - review queue quality and cadence are acceptable to the operator

## Implementation Roadmap

## Phase 1.5: Quality Hardening

### Task 01: Source Health And Priority Review
- Goal: decide which Korea/Japan feeds are primary, secondary, or disabled.
- Actions:
  - run discovery multiple times or inspect recent source outputs
  - classify noisy, duplicate-heavy, or non-article feeds
  - update source notes and source sets as needed
- Dependencies:
  - Phase 1 config exists
- Verification commands:
  - `./.venv/bin/python -m app.cli discover --config-dir config/global_country_news`
  - `git diff --check`
- Risk or rollback note:
  - source pruning can reduce coverage; keep rationale in docs
- Done when:
  - source priority and disabled-source rationale are recorded

### Task 02: Category And Matching Tuning
- Goal: keep broad country coverage without flooding one category.
- Actions:
  - tune include/exclude keywords if needed
  - adjust source sets or account matching
  - document category expectations for politics, economy, society, culture, science, sports, and entertainment
- Dependencies:
  - Task 01 observations
- Verification commands:
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_quality.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_quality.db`
- Risk or rollback note:
  - over-filtering can hide important news
- Done when:
  - review queue shows a balanced set or blockers are documented

### Task 03: Sensitive Topic Guardrails
- Goal: make high-risk topics safer for global-reader summaries.
- Actions:
  - review current sensitivity prompt guidance
  - add prompt or validation refinements if needed
  - ensure politics, security, legal, disaster, health, and finance topics stay review-first
- Dependencies:
  - Task 02 draft observations
- Verification commands:
  - `./.venv/bin/pytest tests/test_x_draft_generator.py tests/test_draft_validation.py -q`
  - `git diff --check`
- Risk or rollback note:
  - guardrails should guide review, not erase news coverage
- Done when:
  - sensitive drafts carry clear caution and source attribution

### Task 04: Cadence And Workload Tuning
- Goal: set schedule and backlog values that match human review capacity.
- Actions:
  - tune X schedule, backlog targets, and duplicate windows
  - document initial daily limits
  - keep live publish manual
- Dependencies:
  - source and prompt quality observations
- Verification commands:
  - `./.venv/bin/pytest tests/test_scheduler.py tests/test_review_queue_workflow.py -q`
  - `scripts/scan_secrets.sh check`
- Risk or rollback note:
  - schedule tuning should not create multiple due jobs unexpectedly
- Done when:
  - cadence is documented and dry-run behavior remains predictable

### Task 05: Operator Quality Checklist
- Goal: give the operator a repeatable checklist before live publishing.
- Actions:
  - document checks for URL, source attribution, summary accuracy, category, and sensitivity
  - include reject/edit/schedule guidance
  - include stop conditions
- Dependencies:
  - Tasks 01 through 04
- Verification commands:
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Risk or rollback note:
  - docs-only checklist; rollback is reverting the doc update
- Done when:
  - operator can review drafts consistently before live runs

## Suggested Execution Order
1. Task 01: Source Health And Priority Review
2. Task 02: Category And Matching Tuning
3. Task 03: Sensitive Topic Guardrails
4. Task 04: Cadence And Workload Tuning
5. Task 05: Operator Quality Checklist

## Initial Milestone Recommendation
Start with source health. It is the smallest useful step after Phase 1 and prevents prompt work from compensating for weak inputs.
