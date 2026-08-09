# Global Country News Phase 0 Rollout Pause Source Cleanup Vibe Coding Prompt

## Purpose
This document is the kickoff brief for pausing the first live rollout after the successful X publish that used placeholder source URLs, then preparing a clean source-data baseline for the country news rollout.

Use it when you want an autonomous coding agent to inspect the current production rollout evidence, preserve the successful live-publish learning, and create the smallest safe cleanup slice before any new live post.

## Generated Document Naming
- Vibe coding prompt file: `docs/global-country-news-phase-0-rollout-pause-source-cleanup-vibe-coding-prompt.md`
- Roadmap file: `docs/global-country-news-phase-0-rollout-pause-source-cleanup-roadmap.md`
- Execution guide file: `docs/global-country-news-phase-0-rollout-pause-source-cleanup-execution-guide.md`
- Progress tracker file: `docs/global-country-news-phase-0-rollout-pause-source-cleanup-progress-tracker.md`

## Initiative Brief
- Initiative name: `Global Country News Phase 0 Rollout Pause Source Cleanup`
- One-sentence outcome: `Close the first live rollout as technically successful but operationally paused, then remove placeholder source risk before the country-news config work begins.`
- Why this matters now:
  - The first live X publish succeeded, proving the publisher path works.
  - The published URL came from sample CSV data and used `example.com`, so the next live run must not continue from the same source baseline.
- Primary owner:
  - Operator of the single-server `sns-content-engine` deployment
  - Autonomous coding agent maintaining the rollout documents and safety gates
- Core workflow to improve:
  - Record the post-publish decision as `pause` or `hold_for_investigation`.
  - Audit checked-in and production config/data for placeholder URLs.
  - Define a clean handoff into Phase 1 country news config work.
- Explicit non-goals:
  - Do not create new publishers.
  - Do not run a second live publish.
  - Do not build the Korea/Japan config in this phase.
  - Do not redesign storage, review, or scheduling.

## Repository Context
The repository already has:
- CLI healthcheck, rollout-summary, run-local, review, scheduler, and publish-due commands.
- A dry-run-first scheduler and one-off live publish path.
- Source connectors for RSS, sitemap, manual CSV, and GDELT.
- Manual review, approval, scheduling, and publish job persistence.

Important files and patterns:
- Core entrypoints: `app/cli.py`, `app/scheduler/runtime.py`
- Workflows/services: `app/workflows/run_local_pipeline.py`, `app/workflows/build_content_briefs.py`, `app/workflows/generate_drafts.py`
- Current config/data: `config/accounts.yaml`, `config/sources.yaml`, `data/ai_tools_manual.csv`, `data/seo_tools_manual.csv`
- Current rollout tracker: `docs/first-live-rollout-operations-progress-tracker.md`
- Existing tests to reuse first: `tests/test_operations.py`, `tests/test_cli.py`, `tests/test_run_local_pipeline_workflow.py`, `tests/test_scripts.py`
- Existing docs to align with: `README.md`, `docs/single-server-deployment-guide.md`, `docs/operator-console-guide.md`

## Product Intent And Quality Bar
The desired implementation should:
- preserve the first live publish success evidence without normalizing placeholder content as acceptable
- make the next operator decision explicit before any new live command
- identify where placeholder URLs can enter config, data, or persisted DB state
- hand off cleanly to the country-news config phase

The agent should preserve:
- dry-run-first behavior
- manual review before scheduling
- no second live publish without explicit approval
- env-only secret handling

The agent should avoid:
- weakening healthcheck or source-readiness gates
- editing production data blindly
- deleting DB state without an operator-approved backup/rollback note
- adding new automation surfaces

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `./.venv/bin/python -m app.cli version`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config`
- Narrow verification commands:
  - `rg -n 'example\\.com|example\\.org|example\\.net' config data docs/first-live-rollout-operations-progress-tracker.md`
  - `scripts/scan_secrets.sh check`
- Broader regression commands:
  - `git diff --check`
  - `./.venv/bin/pytest tests/test_operations.py tests/test_cli.py -q`
- Required local services:
  - none for docs-only cleanup planning
- Required env files, secrets, or fixtures:
  - production checks require `/opt/sns-content-engine/.env`, `/opt/sns-content-engine/config`, and `/opt/sns-content-engine/data`
- Package install policy: `not_allowed`
- Push and PR policy: `do_not_push_without_explicit_request`

## Expected Agent Behavior
- Read the current first-live rollout tracker before updating any new Phase 0 documents.
- Treat the successful live publish and the placeholder URL issue as separate facts.
- Prefer documentation, audit commands, and operator handoff before any code or data mutation.
- Record blockers clearly if production access is unavailable.
- Keep branch, staging, and commit scope limited to Phase 0 documents and any targeted guardrail changes.

## First-Pass Definition Of Done
- Phase 0 roadmap, execution guide, and progress tracker exist.
- The current live rollout decision is represented as paused or blocked until source cleanup.
- Placeholder audit commands are documented for both local and production contexts.
- No live publish command is run.
- Targeted checks are run, or the reason they could not run is recorded.

## Prompt Template
```text
You are working in an existing repository, not a blank project.

Read this document first:
- docs/global-country-news-phase-0-rollout-pause-source-cleanup-vibe-coding-prompt.md

Then inspect and use:
- docs/global-country-news-phase-0-rollout-pause-source-cleanup-roadmap.md
- docs/global-country-news-phase-0-rollout-pause-source-cleanup-execution-guide.md
- docs/global-country-news-phase-0-rollout-pause-source-cleanup-progress-tracker.md

Your job is to pause the placeholder-source rollout safely and prepare the repository for the Korea/Japan global news config phase.

Preserve dry-run-first behavior, manual review, env-only secrets, and the no-second-live-command boundary.
Do not run `scheduler publish-due --live`.
Do not mutate production data unless the roadmap task explicitly requires it and the operator has approved the exact command.
```
