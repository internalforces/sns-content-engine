# Global Country News Phase 2 Longform Publishing Funnel Roadmap

## Goal
Extend the stable country-news MVP into a long-form publishing funnel that:
- creates deeper blog/newsletter drafts from country news briefs
- keeps source attribution and review controls
- supports Ghost or WordPress as an owned content home
- preserves original-article URL behavior for X, Threads, and LinkedIn drafts
- uses Substack, beehiiv, LinkedIn Newsletter, Medium, Reddit, and Hacker News intentionally rather than automatically

## Generated Document Naming
- Roadmap file: `docs/global-country-news-phase-2-longform-publishing-funnel-roadmap.md`
- Execution guide file: `docs/global-country-news-phase-2-longform-publishing-funnel-execution-guide.md`
- Progress tracker file: `docs/global-country-news-phase-2-longform-publishing-funnel-progress-tracker.md`
- Vibe coding prompt file: `docs/global-country-news-phase-2-longform-publishing-funnel-vibe-coding-prompt.md`

## Current Implementation Snapshot

### Already Implemented
- Phase 1 should provide real country-news briefs and social drafts.
- Manual review and handoff patterns exist.
- API and console patterns exist for operator control.
- Publisher adapters exist for X and Threads; LinkedIn is manual handoff.

### Current Limitations Relevant To The New Goal
- Ghost blog/article drafts now exist as review-led manual handoffs.
- No aggregation of multiple source items into a single long-form brief exists.
- No live Ghost, WordPress, Substack, or newsletter integration exists.
- Social drafts intentionally link to original source URLs, not blog URLs.

## Environment And Execution Assumptions
- Base branch: `master`
- Depends on Phase 1 and Phase 1.5 stability unless reprioritized.
- Narrow verification commands:
  - `./.venv/bin/pytest tests/test_storage.py tests/test_review_queue_workflow.py -q`
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Required env:
  - platform credentials only after an integration task is explicitly selected

## Target Architecture

### Content Model Layer
- Country news source items can remain single-item drafts for social.
- Long-form content can be:
  - single-story explainer
  - country daily brief
  - category weekly brief
  - multi-source context article
- Drafts must retain provenance and source links.

### Publishing Layer
1. Generate a long-form draft.
2. Review and edit it.
3. Publish manually or through a dry-run-first adapter.
4. Store external URL.
5. Keep X/Threads/LinkedIn variants source-linked to the original article URL; the stored Ghost URL is for long-form handoff records, not social draft replacement.

### Distribution Layer
- Owned home: Ghost first, WordPress alternate.
- Newsletter: Substack or beehiiv.
- Professional distribution: LinkedIn Newsletter.
- Optional cross-post: Medium.
- Manual community testing: Reddit and Hacker News.

## Milestones

### Milestone M1: Longform Strategy And Model
- Goal: decide the minimum long-form shape.
- Includes:
  - platform decision
  - content type design
  - data model or handoff-only approach decision
- Excludes:
  - external live integration
- Ship when:
  - implementation shape is safe and small

### Milestone M2: Review-Led Draft Workflow
- Goal: generate and review long-form drafts without publishing externally.
- Includes:
  - prompt profiles
  - storage or handoff records
  - API/console visibility if needed
- Excludes:
  - auto-posting
- Ship when:
  - operator can review long-form drafts

### Milestone M3: Platform Handoff Or Adapter
- Goal: publish or hand off reviewed long-form content to the chosen platform.
- Includes:
  - Ghost or WordPress first
  - dry-run or manual handoff
  - external URL recording
- Excludes:
  - community automation
- Ship when:
  - one long-form article can be safely published or recorded

### Milestone M4: Social Source-Link Guardrail
- Goal: explicitly keep social posts pointed at the original source URL while long-form handoff remains separate.
- Includes:
  - X original-source URL behavior
  - Threads original-source URL behavior
  - LinkedIn original-source URL behavior
- Excludes:
  - adding blog-funnel mode in this phase
- Ship when:
  - regression coverage and docs confirm social drafts use original article URLs

## Implementation Roadmap

## Phase 2: Longform Publishing Funnel

### Task 01: Choose Longform Platform Strategy
- Goal: decide the first platform and rollout mode.
- Actions:
  - compare Ghost, WordPress, Substack, beehiiv, LinkedIn Newsletter, Medium
  - recommend Ghost as the first owned-home integration unless operator chooses otherwise
  - document manual community distribution boundaries
- Dependencies:
  - Phase 1.5 quality baseline
- Verification commands:
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Risk or rollback note:
  - strategy doc only; no external side effects
- Done when:
  - one platform path and one fallback path are selected

### Task 02: Design Longform Draft Model
- Goal: decide whether long-form drafts need new storage tables or can start as manual handoff records.
- Actions:
  - inspect storage and review workflow
  - define article draft fields, provenance, state, and external URL needs
  - choose the smallest implementation shape
- Dependencies:
  - Task 01 platform strategy
- Verification commands:
  - `./.venv/bin/pytest tests/test_storage.py -q`
  - `git diff --check`
- Risk or rollback note:
  - schema changes require migration and broad regression
- Done when:
  - model decision and verification scope are documented

### Task 03: Add Longform Prompt And Generation Flow
- Goal: generate reviewable long-form drafts from one or more country news briefs.
- Actions:
  - define single-story and daily-brief prompt shapes
  - require source list and attribution
  - keep drafts pending review
- Dependencies:
  - Task 02 model decision
- Verification commands:
  - `./.venv/bin/pytest tests/test_x_draft_generator.py tests/test_run_local_pipeline_workflow.py -q`
  - `git diff --check`
- Risk or rollback note:
  - do not reuse short-form validators blindly for long-form content
- Done when:
  - long-form draft generation is reviewable and source-linked

### Task 04: Expose Longform Review Or Handoff
- Goal: let the operator inspect, approve, reject, and record long-form outcomes.
- Actions:
  - reuse review or publish-job patterns where practical
  - add API/console surfaces only if needed
  - preserve manual review
- Dependencies:
  - Task 03 generation flow
- Verification commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q`
  - `scripts/scan_secrets.sh check`
- Risk or rollback note:
  - avoid a full frontend redesign
- Done when:
  - operator can manage long-form drafts without direct DB edits

### Task 05: Add First Platform Handoff Or Adapter
- Goal: support publishing to the selected primary home.
- Actions:
  - start with manual handoff or dry-run adapter
  - store external article URL after publication
  - keep credentials in environment only
- Dependencies:
  - Task 04 review flow
- Verification commands:
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
  - `scripts/scan_secrets.sh check`
- Risk or rollback note:
  - no live external post without explicit approval
- Done when:
  - one reviewed long-form article can be published or recorded safely

### Task 06: Confirm Original-Source Social Links
- Goal: keep social drafts pointed at the original article URL even after reviewed Ghost URLs are recorded.
- Actions:
  - document that blog-funnel mode is not part of this phase
  - verify prompt rendering chooses the original article URL over any long-form landing URL for social channels
  - preserve validation that requires the expected source URL in draft bodies
  - avoid breaking Phase 1 behavior
- Dependencies:
  - Task 05 external URL recording decision
- Verification commands:
  - `./.venv/bin/pytest tests/test_x_draft_generator.py tests/test_draft_validation.py tests/test_review_queue_workflow.py -q`
  - `git diff --check`
- Risk or rollback note:
  - future funnel work must be opened as a separate opt-in task with explicit storage and review semantics
- Done when:
  - X, Threads, and LinkedIn remain source-linked while Ghost manual handoff can still record a final article URL

## Suggested Execution Order
1. Task 01: Choose Longform Platform Strategy
2. Task 02: Design Longform Draft Model
3. Task 03: Add Longform Prompt And Generation Flow
4. Task 04: Expose Longform Review Or Handoff
5. Task 05: Add First Platform Handoff Or Adapter
6. Task 06: Confirm Original-Source Social Links

## Initial Milestone Recommendation
Start with platform strategy and model design. Do not write integration code until the operator chooses the long-form home and confirms whether Phase 2 should begin.
