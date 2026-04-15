# Threads API Publish Readiness Progress Tracker

## Usage
This file is the live implementation tracker for the Threads API Publish Readiness roadmap.

When an autonomous agent works from `docs/threads-api-publish-readiness-execution-guide.md`, it should update this file:
- before starting a task,
- during meaningful implementation progress,
- after running tests,
- when a blocker or stop reason appears,
- when the task is complete.

Keep updates short, factual, and current.

## Generated document naming
When instantiating this template, keep the filename explicit so this file is easy to distinguish from planning or prompt documents.

- Recommended filename: `docs/threads-api-publish-readiness-progress-tracker.md`
- Related files:
  - `docs/threads-api-publish-readiness-vibe-coding-prompt.md`
  - `docs/threads-api-publish-readiness-roadmap.md`
  - `docs/threads-api-publish-readiness-execution-guide.md`

If `Current task` is already marked `in_progress` or `blocked`, resume or resolve that task before picking a new one unless the roadmap was intentionally reprioritized.

## Current Status
- Current milestone: `M1_threads_publisher_foundation`
- Current task: `02_expand_config_backed_publisher_resolution_for_threads`
- Active status: `done`
- Last updated: `2026-04-15 17:02 KST`
- Base branch: `master`
- Active branch: `codex/task-02-threads-publisher-resolution`
- Latest task commit: `self-referential commit SHA cannot be recorded in-band; see git history for the Task 02 commit created after this tracker update`
- Resume decision: `task_02_complete`
- Stop reason: `task_complete`

## Scope For Current Task
- Goal: `Make publisher.credential_ref sufficient to resolve Threads live publishers through the same config and env path already used for X`
- In scope: `ConfigPublisherResolver channel expansion, Threads credential-bundle parsing and validation, failure normalization, and focused resolver regression coverage`
- Out of scope: `Review-flow branching changes, LinkedIn direct publishing, auth, and any console or API behavior changes`
- Dependencies: `Task 01 Threads publisher adapter plus the existing config loading and X resolver patterns`
- Verification commands:
  - `./.venv/bin/pytest tests/test_x_publisher.py tests/test_threads_publisher.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -k "publish_due_jobs_live_defaults_to_config_publisher_resolver" -q`

## Environment Notes
- Required services status: `running (none required beyond local tests and SQLite fixtures)`
- Env or fixture status: `ready (.venv, temp-db helpers, and config fixtures are already present)`
- Existing unrelated failures: `none confirmed for this initiative yet`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Define Threads credential bundle and publisher adapter | done | 2026-04-15 16:53 KST | Added a text-only Threads publisher adapter, package exports, focused adapter tests, and scheduler coverage for normalized Threads provider payload logging |
| M1 | 02 | Expand config-backed publisher resolution for Threads | done | 2026-04-15 17:02 KST | `ConfigPublisherResolver` now resolves `threads` alongside `x`, validates one env-referenced Threads JSON bundle, preserves channel-level caching, and is covered by focused resolver regressions |
| M2 | 03 | Make Threads review and scheduling flow publisher-aware | pending | 2026-04-15 16:34 KST | Threads should become live-capable only when channel config and credentials support it |
| M2 | 04 | Carry Threads live jobs through scheduler, API, and console surfaces | pending | 2026-04-15 16:34 KST | Existing operator surfaces should reflect the new live/manual branching without duplicate business logic |
| M3 | 05 | Document token-ready Threads setup and expand regressions | pending | 2026-04-15 16:34 KST | Final slice should align README and operator docs with shipped behavior and regression coverage |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `app/connectors/publishers/resolver.py`
- `tests/test_threads_publisher.py`
- `docs/threads-api-publish-readiness-progress-tracker.md`

## Progress Log
- `2026-04-15 16:34 KST` Created the Threads API Publish Readiness initiative to turn Threads from a static manual-handoff channel into a config-gated live publisher path that an operator can enable through one env-referenced credential bundle.
- `2026-04-15 16:34 KST` Chose a staged shape that starts with adapter and resolver work, then moves into review or scheduler branching, then finishes with operator docs and regressions so current safety defaults stay intact while the integration is introduced.
- `2026-04-15 16:34 KST` Left all execution tasks in `pending` so implementation can begin cleanly from Task `01` on a dedicated task branch.
- `2026-04-15 16:48 KST` Switched to branch `codex/task-01-threads-publisher-adapter` and started Task `01`.
- `2026-04-15 16:48 KST` Confirmed from current Meta Threads docs that live publish requires a Threads user access token with `threads_basic` and `threads_content_publish`, plus a `THREADS_USER_ID`, and that posting is a two-step `POST /{threads-user-id}/threads` then `POST /{threads-user-id}/threads_publish` flow.
- `2026-04-15 16:50 KST` Implemented `ThreadsPublisher` with an isolated urllib HTTP client that creates a text-only Threads container, publishes it through the second API call, and normalizes provider success, provider failure, request exceptions, and malformed responses into `PublishResult`.
- `2026-04-15 16:51 KST` Re-exported the new Threads publisher types from `app.connectors.publishers` and added focused adapter tests plus scheduler coverage that proves Threads provider payload details survive through publish-job logging.
- `2026-04-15 16:53 KST` Completed Task `01` after the targeted adapter suite, focused scheduler slice, full scheduler regression file, and `git diff --check` all passed on the task branch.
- `2026-04-15 16:57 KST` Switched to branch `codex/task-02-threads-publisher-resolution`, marked Task `02` in progress, and narrowed the next slice to resolver-only changes that keep `publisher.credential_ref` as the single operator-facing setup path for both X and Threads.
- `2026-04-15 17:00 KST` Reworked `ConfigPublisherResolver` into a channel-aware resolver that preserves the existing X path, adds a Threads builder plus injected HTTP client support, and normalizes shared credential-bundle parsing before channel-specific validation.
- `2026-04-15 17:00 KST` Added focused Threads resolver regressions that cover success, cache reuse, missing env, invalid JSON, missing `access_token`, and missing `threads_user_id` without widening scope into review or scheduler branching.
- `2026-04-15 17:02 KST` Completed Task `02` after targeted publisher tests, focused scheduler verification, full scheduler regression coverage, and `git diff --check` all passed on the task branch.

## Test Log
- `2026-04-15 16:34 KST` `runtime tests` -> `not_run` `initiative documentation only; no product code changes were requested in this turn`
- `2026-04-15 16:51 KST` `./.venv/bin/pytest tests/test_x_publisher.py tests/test_threads_publisher.py -q` -> `failed` `2 failed, 15 passed; malformed Threads response assertions were expecting missing-id messaging while the first implementation returned a broader expected-object error`
- `2026-04-15 16:52 KST` `./.venv/bin/pytest tests/test_x_publisher.py tests/test_threads_publisher.py -q` -> `passed` `17 passed`
- `2026-04-15 16:52 KST` `./.venv/bin/pytest tests/test_scheduler.py -k "publish_due_jobs_marks_jobs_published_with_publisher_resolver or publish_due_jobs_records_threads_provider_payload_from_publisher_resolver" -q` -> `passed` `2 passed, 15 deselected`
- `2026-04-15 16:53 KST` `./.venv/bin/pytest tests/test_scheduler.py -q` -> `passed` `17 passed`
- `2026-04-15 16:53 KST` `git diff --check` -> `passed`
- `2026-04-15 17:00 KST` `./.venv/bin/pytest tests/test_x_publisher.py tests/test_threads_publisher.py -q` -> `passed` `22 passed`
- `2026-04-15 17:01 KST` `./.venv/bin/pytest tests/test_scheduler.py -k "publish_due_jobs_live_defaults_to_config_publisher_resolver" -q` -> `passed` `1 passed, 16 deselected`
- `2026-04-15 17:01 KST` `./.venv/bin/pytest tests/test_scheduler.py -q` -> `passed` `17 passed`
- `2026-04-15 17:02 KST` `git diff --check` -> `passed`

## Open Questions
- `Resolved for Task 02: Threads live publishing now uses the same `publisher.credential_ref` lookup pattern as X, with one env-referenced JSON bundle containing `access_token` plus `threads_user_id``

## Blockers
- `None currently`

## Follow-up
- `Task 03 should make review approval and scheduling branch on resolver-backed Threads live capability instead of treating Threads as permanently manual-only`
- `Container readiness polling remains intentionally deferred; the Task 01 adapter performs the required two-step publish immediately for text-only posts and returns normalized provider errors when Threads rejects the publish call`

## Completion Summary
- `Task 02 complete: the repository now resolves Threads live publishers through the same `accounts.yaml` plus `publisher.credential_ref` env-bundle path used for X, validates the confirmed Threads credential shape (`access_token` and `threads_user_id`), preserves resolver caching by account and channel, and adds focused regression coverage without changing the current review or scheduler safety model.`
