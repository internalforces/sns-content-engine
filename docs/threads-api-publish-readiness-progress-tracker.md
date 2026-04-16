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
- Current milestone: `M3_operator_docs_and_hardening`
- Current task: `05_document_token_ready_threads_setup_and_expand_regressions`
- Active status: `done`
- Last updated: `2026-04-16 13:50 KST`
- Base branch: `master`
- Active branch: `codex/task-05-threads-live-docs`
- Latest task commit: `self-referential commit SHA cannot be recorded in-band; see git history for the Task 05 commit created after this tracker update`
- Resume decision: `task_05_complete`
- Stop reason: `task_complete`

## Scope For Current Task
- Goal: `Document how to enable and operate the shipped Threads live/manual split with one env-referenced credential bundle and matching operator guidance`
- In scope: `README, operator console guide, control-plane API guide, safe env examples, and focused regression plus diff hygiene checks`
- Out of scope: `LinkedIn direct publishing, runtime behavior changes beyond doc-alignment fixes, auth, and media or reply-chain features`
- Dependencies: `Task 04 operator-surface behavior plus the existing Threads publisher and resolver implementation`
- Verification commands:
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py tests/test_review_queue_workflow.py tests/test_scheduler.py -q`
  - `git diff --check`

## Environment Notes
- Required services status: `running (none required beyond local tests and SQLite fixtures)`
- Env or fixture status: `ready (.venv, temp-db helpers, and config fixtures are already present)`
- Existing unrelated failures: `none confirmed for this initiative yet`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Define Threads credential bundle and publisher adapter | done | 2026-04-15 16:53 KST | Added a text-only Threads publisher adapter, package exports, focused adapter tests, and scheduler coverage for normalized Threads provider payload logging |
| M1 | 02 | Expand config-backed publisher resolution for Threads | done | 2026-04-15 17:02 KST | `ConfigPublisherResolver` now resolves `threads` alongside `x`, validates one env-referenced Threads JSON bundle, preserves channel-level caching, and is covered by focused resolver regressions |
| M2 | 03 | Make Threads review and scheduling flow publisher-aware | done | 2026-04-15 17:12 KST | Review approval and scheduling now branch on resolver-backed Threads live capability so configured accounts stay in the normal schedule path while missing credentials still fall back to manual handoff |
| M2 | 04 | Carry Threads live jobs through scheduler, API, and console surfaces | done | 2026-04-15 18:01 KST | Scheduler backfill, API review responses, and console review hints now all share the same resolver-backed Threads live/manual capability split, with focused regressions proving both fallback and live-configured behavior |
| M3 | 05 | Document token-ready Threads setup and expand regressions | done | 2026-04-16 13:50 KST | README, console guide, API guide, and env examples now describe the shipped Threads live/manual split, the single env-referenced credential bundle, and the exact scheduler plus review behavior for live-configured versus fallback Threads |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `README.md`
- `docs/operator-console-guide.md`
- `docs/operator-control-plane-api.md`
- `.env.example`
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
- `2026-04-15 17:08 KST` Switched to branch `codex/task-03-threads-review-scheduling`, marked Task `03` in progress, and narrowed the slice to review approval plus scheduling changes that treat Threads as live-capable only when resolver-backed config and env credentials are actually available.
- `2026-04-15 17:09 KST` Added a resolver-backed live-capability probe to `ConfigPublisherResolver` and reused it in the review workflow so Threads approval creates a manual handoff only when the configured credential bundle cannot resolve a live publisher.
- `2026-04-15 17:10 KST` Replaced static Threads-manual scheduling checks with the same resolver-backed branch and added focused workflow coverage for Threads live approval, Threads live scheduling, and fallback behavior when the env credential bundle is absent.
- `2026-04-15 17:12 KST` Completed Task `03` after the focused review-queue suite, full scheduler regression slice, and `git diff --check` all passed on the task branch.
- `2026-04-15 17:53 KST` Switched to branch `codex/task-04-threads-live-operator-surfaces`, marked Task `04` in progress, and narrowed the next slice to scheduler backfill gating plus API or console surfacing that still treats Threads as permanently manual in some operator-facing paths.
- `2026-04-15 17:55 KST` Promoted the Threads live/manual decision into a shared resolver helper, reused it from the review workflow and scheduler backfill path, and kept LinkedIn manual-only semantics unchanged while preventing backfill from creating Threads jobs when live credentials are unavailable.
- `2026-04-15 17:58 KST` Updated the console review-detail action state and approval success messaging so Threads only shows manual upload guidance when the configured account still requires manual handoff; live-configured Threads now keeps the schedule form visible after approval.
- `2026-04-15 18:01 KST` Completed Task `04` after adding focused API, console, and scheduler regressions for Threads live approval, Threads live scheduling, Threads live backfill, and manual fallback behavior, then rerunning the required shared regression slices successfully.
- `2026-04-16 13:42 KST` Switched to branch `codex/task-05-threads-live-docs`, marked Task `05` in progress, and narrowed the final slice to README plus operator-guide updates that still describe Threads as always manual even though the shipped workflow is now config-gated live when credentials are present.
- `2026-04-16 13:46 KST` Updated README, the console guide, and the control-plane API guide so operator-facing docs now distinguish LinkedIn manual-only behavior from Threads live-configured versus manual-fallback behavior, including backfill eligibility and review-page scheduling semantics.
- `2026-04-16 13:47 KST` Added safe Threads credential-bundle examples to `.env.example` and the docs, keeping secrets out of YAML while showing the exact `access_token` plus `threads_user_id` contract required by `publisher.credential_ref`.
- `2026-04-16 13:50 KST` Completed Task `05` after the focused shared regression slice and `git diff --check` both passed on the task branch.

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
- `2026-04-15 17:10 KST` `./.venv/bin/pytest tests/test_review_queue_workflow.py -q` -> `passed` `28 passed`
- `2026-04-15 17:10 KST` `./.venv/bin/pytest tests/test_scheduler.py -q` -> `passed` `17 passed`
- `2026-04-15 17:10 KST` `git diff --check` -> `passed`
- `2026-04-15 17:12 KST` `./.venv/bin/pytest tests/test_review_queue_workflow.py -q` -> `passed` `28 passed` `reran after fixture readability cleanup with no behavior changes`
- `2026-04-15 17:57 KST` `./.venv/bin/pytest tests/test_scheduler.py -q` -> `passed` `19 passed`
- `2026-04-15 18:00 KST` `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q` -> `failed` `1 failed, 78 passed; new Threads live scheduling API assertion expected a trailing Z while the shared serializer returns +00:00`
- `2026-04-15 18:00 KST` `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q` -> `passed` `79 passed`
- `2026-04-15 18:00 KST` `./.venv/bin/pytest tests/test_scheduler.py tests/test_review_queue_workflow.py -q` -> `passed` `47 passed`
- `2026-04-15 18:01 KST` `git diff --check` -> `passed`
- `2026-04-16 13:49 KST` `./.venv/bin/pytest tests/test_api.py tests/test_console.py tests/test_review_queue_workflow.py tests/test_scheduler.py -q` -> `passed` `126 passed`
- `2026-04-16 13:49 KST` `git diff --check` -> `passed`

## Open Questions
- `Resolved for Task 02: Threads live publishing now uses the same `publisher.credential_ref` lookup pattern as X, with one env-referenced JSON bundle containing `access_token` plus `threads_user_id``

## Blockers
- `None currently`

## Follow-up
- `Threads API Publish Readiness roadmap is complete for the current scope; any follow-up should be a new initiative or a post-ship hardening slice such as richer Threads provider observability, media upload, or container readiness polling`
- `Container readiness polling remains intentionally deferred; the Task 01 adapter performs the required two-step publish immediately for text-only posts and returns normalized provider errors when Threads rejects the publish call`

## Completion Summary
- `Task 05 complete: operator-facing docs now match the shipped behavior. README, the browser-console guide, and the control-plane API guide all describe Threads as a config-gated live channel that falls back to manual handoff when the referenced env bundle is missing or invalid, while LinkedIn remains manual-only. Safe example config and env snippets now show the exact `publisher.credential_ref` plus `access_token` and `threads_user_id` setup, and the focused shared regression slice still passes.`
