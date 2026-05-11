# Global Country News Phase 2 Longform Publishing Funnel Vibe Coding Prompt

## Purpose
This document is the kickoff brief for expanding the country news MVP into a long-form publishing funnel after Phase 1 and Phase 1.5 are stable.

Use it when you want an autonomous coding agent to design and implement blog/newsletter long-form workflows while keeping X, Threads, and LinkedIn safe and review-led.

## Generated Document Naming
- Vibe coding prompt file: `docs/global-country-news-phase-2-longform-publishing-funnel-vibe-coding-prompt.md`
- Roadmap file: `docs/global-country-news-phase-2-longform-publishing-funnel-roadmap.md`
- Execution guide file: `docs/global-country-news-phase-2-longform-publishing-funnel-execution-guide.md`
- Progress tracker file: `docs/global-country-news-phase-2-longform-publishing-funnel-progress-tracker.md`

## Initiative Brief
- Initiative name: `Global Country News Phase 2 Longform Publishing Funnel`
- One-sentence outcome: `Add a review-led long-form content layer while keeping X, Threads, and LinkedIn drafts pointed at the original article URL.`
- Why this matters now:
  - Phase 1 keeps channel drafts independent for safety.
  - Once source quality is stable, long-form posts can create durable value beyond short social summaries.
- Primary owner:
  - operator managing editorial review
  - autonomous agent designing blog/newsletter workflows and integrations
- Core workflow to improve:
  - group news items into long-form briefs
  - generate blog/newsletter drafts
  - review and publish or hand off to a chosen platform
  - keep social drafts independent and source-linked instead of turning them into a blog funnel
- Explicit non-goals:
  - no Phase 2 work before Phase 1 and Phase 1.5 are stable
  - no automatic publication of long-form content without review
  - no unapproved platform integration storing secrets in code or YAML
  - no community spam automation

## Repository Context
The repository already has:
- source ingestion and content brief generation
- channel-specific draft generation
- manual review and publish handoff concepts
- X and Threads publisher adapters
- LinkedIn manual handoff behavior

Important files and patterns:
- Current workflows: `app/workflows/run_local_pipeline.py`, `app/workflows/generate_drafts.py`, `app/workflows/review_queue.py`
- Storage: `app/storage/models.py`, `app/storage/repositories.py`, `app/storage/bootstrap.py`
- Publisher patterns: `app/connectors/publishers/`
- API/console patterns: `app/api/`
- Docs: `docs/operator-console-guide.md`, `docs/operator-control-plane-api.md`

## Product Intent And Quality Bar
The desired implementation should:
- choose a primary long-form home, likely Ghost or WordPress
- treat Substack or beehiiv as newsletter/distribution channels
- support LinkedIn Newsletter or LinkedIn article handoff for professional context
- keep Reddit/Hacker News as manual community distribution, not automated spam
- preserve X, Threads, and LinkedIn drafts as source-linked posts that use the original article URL

The agent should preserve:
- manual review before publishing
- dry-run or handoff-first behavior for new external surfaces
- env-only secrets
- source attribution and provenance
- the existing original-article URL behavior for social drafts

The agent should avoid:
- implementing every platform at once
- weakening article/source policy checks
- cross-posting automatically to communities
- replacing Phase 1's stable independent channel model until a dedicated task changes it
- adding a blog-funnel URL selector for social drafts in this phase

## Platform Direction
Recommended platform roles:
- `Ghost`: primary owned blog/newsletter home and best first API integration candidate
- `WordPress`: alternate owned blog home if SEO/plugin ecosystem is prioritized
- `Substack`: newsletter and reader-network distribution, likely manual or semi-manual first
- `beehiiv`: newsletter growth/monetization alternative
- `LinkedIn Newsletter`: professional audience distribution and manual or API-limited handoff
- `Medium`: optional human-edited cross-post, not the primary home
- `Reddit` and `Hacker News`: manual community testing only

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands:
  - `./.venv/bin/pytest tests/test_storage.py tests/test_review_queue_workflow.py -q`
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Required services:
  - none until a specific platform adapter is selected
- Required env:
  - platform API credentials only in environment variables, never YAML or docs
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## First-Pass Definition Of Done
- platform decision is documented
- long-form content model and review flow are scoped
- first implementation slice is additive and review-led
- no external platform auto-post happens without dry-run or manual handoff

## Prompt Template
```text
You are implementing Global Country News Phase 2 longform publishing funnel.

Read:
- docs/global-country-news-phase-2-longform-publishing-funnel-vibe-coding-prompt.md
- docs/global-country-news-phase-2-longform-publishing-funnel-roadmap.md
- docs/global-country-news-phase-2-longform-publishing-funnel-execution-guide.md
- docs/global-country-news-phase-2-longform-publishing-funnel-progress-tracker.md

Design and implement the smallest review-led long-form publishing slice.
Do not start until Phase 1 and Phase 1.5 are stable or the operator explicitly reprioritizes.
Preserve manual review, env-only secrets, attribution, and dry-run/handoff-first behavior.
```
