# Global Country News Phase 2 Longform Publishing Funnel Execution Guide

## Purpose
This document guides Phase 2: adding long-form blog/newsletter publishing and optional social funnel behavior after the country-news MVP is stable.

Progress must be tracked in:
- `docs/global-country-news-phase-2-longform-publishing-funnel-progress-tracker.md`

## Repository Context
Important files:
- `app/workflows/run_local_pipeline.py`
- `app/workflows/generate_drafts.py`
- `app/workflows/review_queue.py`
- `app/storage/models.py`
- `app/storage/repositories.py`
- `app/storage/bootstrap.py`
- `app/api/`
- `app/connectors/publishers/`

High-signal tests:
- `tests/test_storage.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_api.py`
- `tests/test_console.py`
- `tests/test_draft_validation.py`
- `tests/test_x_draft_generator.py`

## Execution Environment
- Base branch: `master`
- Preferred branch format:
  - `codex/task-01-longform-platform-strategy`
  - `codex/task-03-longform-generation`
- Narrow verification commands:
  - `./.venv/bin/pytest tests/test_storage.py tests/test_review_queue_workflow.py -q`
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Required env:
  - platform credentials only when an adapter task explicitly requires them
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
- Do not begin Phase 2 implementation until Phase 1 and Phase 1.5 are stable unless the operator explicitly reprioritizes.
- Preserve manual review for long-form content.
- Keep external platform credentials in environment variables only.
- Start with handoff/dry-run behavior before live external posting.
- Do not automate Reddit, Hacker News, or other community posting.
- Keep original-source social mode available even if blog-funnel mode is added.

## Platform Guidance
- Prefer Ghost for first owned-home integration if the operator has no stronger preference.
- Use WordPress if SEO/plugin ecosystem matters more than simple API ownership.
- Use Substack or beehiiv primarily for newsletter distribution.
- Treat LinkedIn Newsletter as professional distribution, likely manual first.
- Treat Medium as optional cross-posting, not canonical home.
- Treat Reddit/Hacker News as manual community testing only.

## Task Guidance

### Platform Strategy
- Record one selected primary home and one fallback.
- Record whether the first implementation is manual handoff, dry-run adapter, or live adapter.
- Do not add credentials during strategy work.

### Model Design
- Inspect existing draft and publish job states before adding tables.
- Prefer extending existing handoff patterns if they fit.
- Add schema only when long-form state cannot be represented safely otherwise.

### Generation Flow
- Separate short-form and long-form prompt constraints.
- Preserve source list and attribution.
- For multi-source articles, require a source table or clear source list in the draft.

### Review And Handoff
- Reuse existing review queue ideas where possible.
- Keep approval separate from publication.
- Store external URL after manual or adapter-based publication.

### Funnel Mode
- Make blog-funnel mode opt-in.
- Preserve current Phase 1 behavior where social posts link directly to original sources.
- Verify link count and required URL validation carefully.

## Progress Tracking Rules
Update the tracker when:
- platform strategy is selected
- model shape changes
- schema or storage changes occur
- API or console surfaces change
- tests run
- external publication is attempted or explicitly skipped

## Master Prompt
```text
You are implementing Global Country News Phase 2.

Read:
- docs/global-country-news-phase-2-longform-publishing-funnel-roadmap.md
- docs/global-country-news-phase-2-longform-publishing-funnel-execution-guide.md
- docs/global-country-news-phase-2-longform-publishing-funnel-progress-tracker.md

Start only if Phase 1 and Phase 1.5 are stable or the operator explicitly reprioritized.
Choose the next unfinished task.
Preserve manual review, env-only secrets, attribution, and dry-run/handoff-first behavior.
Do not automate community posting.
```

## Output Contract
End each task with:
- Summary
- Changed files
- Tests run
- Branch and commit
- Follow-up
