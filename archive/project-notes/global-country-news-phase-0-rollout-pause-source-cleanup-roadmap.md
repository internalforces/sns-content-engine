# Global Country News Phase 0 Rollout Pause Source Cleanup Roadmap

## Goal
Turn the first live rollout outcome into a safe paused baseline that:
- records the X publisher path as technically successful
- treats the `example.com` published URL as a source-data blocker
- audits local and production config/data for placeholder URLs
- prepares a clean handoff into the Korea/Japan country news config phase

## Generated Document Naming
- Roadmap file: `docs/global-country-news-phase-0-rollout-pause-source-cleanup-roadmap.md`
- Execution guide file: `docs/global-country-news-phase-0-rollout-pause-source-cleanup-execution-guide.md`
- Progress tracker file: `docs/global-country-news-phase-0-rollout-pause-source-cleanup-progress-tracker.md`
- Vibe coding prompt file: `docs/global-country-news-phase-0-rollout-pause-source-cleanup-vibe-coding-prompt.md`

## Current Implementation Snapshot

### Already Implemented
- The production X live publisher path succeeded for one approved job.
- The scheduler remains dry-run by default.
- Manual review and scheduling gates exist.
- Healthcheck can detect placeholder URLs inside YAML config and manual CSV URL rows.

### Current Limitations Relevant To The Goal
- The active checked-in manual CSV data contains `example.com` URLs.
- The production database may contain already-created drafts or briefs that still reference placeholder URLs.
- The first live publish should not be repeated until source cleanup is complete.

## Environment And Execution Assumptions
- Base branch: `master`
- Active branch should be task-scoped, for example `codex/phase-0-source-cleanup`
- Narrow verification commands:
  - `rg -n 'example\\.com|example\\.org|example\\.net' config data`
  - `scripts/scan_secrets.sh check`
- Broader regression commands:
  - `git diff --check`
  - `./.venv/bin/pytest tests/test_operations.py tests/test_cli.py -q`
- Required production context:
  - `/opt/sns-content-engine/config`
  - `/opt/sns-content-engine/data`
  - `/opt/sns-content-engine/data/sns_content_engine.db`
  - service account `sns-engine` for DB access

## Target Architecture

### Decision And Evidence Layer
- Preserve the first publish result in the existing first-live rollout tracker.
- Add a Phase 0 tracker that records the operational decision and source cleanup state.
- Keep the first live result marked as a technical success, not a content-quality pass.

### Source Cleanup Layer
1. Find placeholder URLs in checked-in config/data.
2. Find placeholder URLs in production config/data.
3. Inspect or query persisted production drafts/briefs for placeholder URLs.
4. Decide whether stale placeholder records should be rejected, cancelled, or excluded from scheduling.

## Milestones

### Milestone M1: Pause And Audit
- Goal: stop the rollout from advancing while placeholder sources are present.
- Includes:
  - decision capture
  - local placeholder audit
  - production handoff commands
- Excludes:
  - new source config design
  - new live publishing
- Verification target:
  - local placeholder scan recorded
  - production scan command bundle documented
- Ship when:
  - the progress tracker has a concrete stop reason
  - the next phase can start without ambiguity

## Implementation Roadmap

## Phase 0: Rollout Pause And Source Cleanup

### Task 01: Record Rollout Pause Decision
- Goal: record that the first live publish succeeded technically but Phase 1 must not continue from placeholder source data.
- Actions:
  - inspect `docs/first-live-rollout-operations-progress-tracker.md`
  - record the recommended decision as `pause` unless the operator chooses another value
  - state that no second live command is allowed without new approval
- Dependencies:
  - operator confirmation of the placeholder URL issue
- Verification commands:
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Risk or rollback note:
  - docs-only decision capture; rollback is reverting the tracker update
- Done when:
  - Phase 0 tracker records the decision and stop reason
  - no live publish command has run

### Task 02: Audit Placeholder Sources
- Goal: identify all checked-in config and data surfaces that still contain placeholder URLs.
- Actions:
  - scan `config/`, `data/`, and relevant docs
  - distinguish sample/test placeholders from active runtime placeholders
  - document active blockers clearly
- Dependencies:
  - Task 01 decision capture
- Verification commands:
  - `rg -n 'example\\.com|example\\.org|example\\.net' config data`
  - `scripts/scan_secrets.sh check`
- Risk or rollback note:
  - do not delete or rewrite data until the Phase 1 source plan is approved
- Done when:
  - all active placeholder paths are listed
  - sample/test-only placeholders are not confused with production blockers

### Task 03: Add Production Source Cleanup Handoff
- Goal: give the operator safe commands to inspect production source files and DB records for placeholders.
- Actions:
  - document read-only production commands
  - require service-account DB access for SQLite checks
  - avoid printing secrets
- Dependencies:
  - Task 02 scan results
- Verification commands:
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Risk or rollback note:
  - production commands must be read-only unless a later task explicitly approves mutation
- Done when:
  - handoff includes config/data scan and DB query guidance
  - no production mutation command is included

### Task 04: Define Phase 1 Entry Gate
- Goal: define exactly what must be true before building and testing the country-news config.
- Actions:
  - list required real RSS sources
  - require zero active placeholder URLs
  - require review-only first run with no live command
- Dependencies:
  - Task 03 handoff
- Verification commands:
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Risk or rollback note:
  - entry gate protects against repeating the placeholder publish
- Done when:
  - Phase 1 can start from a clear checklist
  - the Phase 0 tracker is marked done or blocked with exact production evidence needed

## Suggested Execution Order
1. Task 01: Record Rollout Pause Decision
2. Task 02: Audit Placeholder Sources
3. Task 03: Add Production Source Cleanup Handoff
4. Task 04: Define Phase 1 Entry Gate

## Initial Milestone Recommendation
Start with Task 01 and Task 02. They are docs and audit focused, have no production side effects, and directly prevent a second placeholder-backed live post.
