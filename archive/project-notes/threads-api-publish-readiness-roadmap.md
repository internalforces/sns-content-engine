# Threads API Publish Readiness Roadmap

## Goal
Extend the current X-live plus LinkedIn or Threads manual-handoff workflow into a Threads-token-ready live publishing workflow that:
- preserves the current manual review gate and dry-run publish defaults
- lets operators enable Threads live publishing through one env-referenced credential bundle instead of ad hoc code or DB work
- reuses the existing scheduled publish job, scheduler, publish log, API, and console surfaces instead of introducing a separate Threads-only pipeline
- keeps LinkedIn manual handoff behavior unchanged while Threads gains a safe config-gated live path

## Generated document naming
When instantiating this template, use a filename that clearly shows the document identity.

- Roadmap file: `docs/threads-api-publish-readiness-roadmap.md`
- Execution guide file: `docs/threads-api-publish-readiness-execution-guide.md`
- Progress tracker file: `docs/threads-api-publish-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/threads-api-publish-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `plan.md`, or `notes.md` when multiple initiatives may exist.

## Roadmap construction rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- Define only as many milestones and tasks as are needed to reach the goal while keeping each unit safely implementable.
- Choose task and milestone boundaries so the work can be completed without breaking the existing architecture, workflow semantics, safety gates, or operator experience.
- Prefer the smallest additive slices that reuse the current structure instead of forcing a broad redesign.
- Split a task when it would otherwise span unrelated surfaces, require unclear rollback, or make testing too broad.
- Merge adjacent tiny tasks when they share the same code path, verification surface, and branch scope.
- If the roadmap shape changes during implementation, update this file and `docs/threads-api-publish-readiness-progress-tracker.md` before continuing.

## Current implementation snapshot

### Already implemented
- Config-driven multichannel draft generation already supports `x`, `linkedin`, and `threads`, with stored review, publish-job, and publish-log state.
- The repository already has a live X publisher adapter, a config-backed publisher resolver, scheduler-driven `publish-due`, and operator-facing API and console surfaces.
- LinkedIn and Threads already have explicit manual handoff creation, outcome recording, publish-job visibility, and regression coverage.

### Current limitations relevant to the new goal
- `app/connectors/publishers/resolver.py` hard-rejects any non-`x` channel for live publishing, even if a channel-level publisher config is present.
- `app/workflows/review_queue.py` and `app/api/console.py` currently treat Threads as a static manual-upload-only channel instead of a config-gated live-publish candidate.
- There is no Threads publisher adapter, isolated HTTP client boundary, or normalized error-handling path comparable to `XPublisher`.
- README, operator docs, and sample config do not yet describe a token-ready Threads live publish setup path.

## Environment and execution assumptions
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands already available:
  - `./.venv/bin/pytest tests/test_x_publisher.py tests/test_scheduler.py -q`
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_scheduler.py tests/test_review_queue_workflow.py tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest -q`
- Required local services:
  - `none for adapter, workflow, and UI regression work`
  - `optional live Threads API access only for an explicit operator smoke test after implementation`
- Required env files, secrets, or fixtures:
  - `.env is optional unless a live Threads publish smoke test is being exercised`
  - `temporary SQLite databases, per-test config directories, and fixture helpers already exist in the repository`
- Package install policy: `ask_first`

## Target architecture

### Publisher adapter layer
- `threads_publisher_adapter`
  - isolates Threads API post creation behind the existing `Publisher` interface
  - normalizes credential validation, provider responses, and error payloads into `PublishResult`
- `config_publisher_resolution`
  - keeps `publisher.credential_ref` as the operator-facing setup mechanism
  - resolves `x` versus `threads` publishers from the existing account or channel config without inventing a second resolver path

### Workflow gating layer
1. An operator approves a Threads draft under the current review gate.
2. If the Threads channel has a live publisher configured, the draft uses the existing scheduled publish workflow; otherwise it falls back to the current manual handoff path.
3. Scheduler backfill and `publish-due --live` execute stored Threads publish jobs through the new adapter using the configured credential bundle.
4. API, console, and docs expose the exact Threads-live versus LinkedIn-manual semantics.

## Milestones
Use as many milestone blocks as needed. Keep each milestone small enough to be completed without breaking the current structure or requiring a broad redesign.

### Milestone M1: Threads Publisher Foundation
- Goal: add the smallest Threads adapter and config-backed credential resolution path needed for live publishing
- Includes:
  - Threads HTTP client boundary and normalized publisher adapter
  - resolver support for channel `threads`
- Excludes:
  - review-flow changes that alter manual versus live branching
  - LinkedIn direct publishing
- Verification target:
  - `./.venv/bin/pytest tests/test_x_publisher.py tests/test_threads_publisher.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -k "publish_due_jobs_marks_jobs_published_with_publisher_resolver or publish_due_jobs_live_defaults_to_config_publisher_resolver" -q`
- Ship when:
  - a Threads credential bundle can build a publisher from config and env only
  - resolver failures for missing or malformed Threads credentials are normalized and test-covered

### Milestone M2: Threads Workflow Integration
- Goal: let Threads use the existing scheduled publish lifecycle when live publishing is configured, while preserving manual fallback when it is not
- Includes:
  - config-gated Threads schedule or backfill eligibility
  - approval-time Threads manual handoff fallback only when live publish is unavailable
- Excludes:
  - LinkedIn workflow changes
  - auth, permission, or scheduler redesign
- Verification target:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_scheduler.py -q`
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
- Ship when:
  - approved Threads drafts can enter the scheduled publish path when configured
  - Threads still falls back to manual handoff when no live publisher is configured

### Milestone M3: Operator Surfacing And Docs
- Goal: make token-ready Threads setup discoverable to operators and protect the shipped behavior with focused regressions
- Includes:
  - README, API, console, and config example updates for Threads live publishing
  - focused live versus manual branching regressions across workflow, API, console, and scheduler surfaces
- Excludes:
  - deployment automation, secret management redesign, or OAuth refresh automation
  - direct LinkedIn live publishing
- Verification target:
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py tests/test_review_queue_workflow.py tests/test_scheduler.py -q`
  - `git diff --check`
- Ship when:
  - operator-facing docs show how to enable Threads live publishing through one credential env bundle
  - browser and API behavior match the documented Threads-live versus LinkedIn-manual split

## Implementation roadmap

## Phase 1: Publisher Foundation

### Task 01: Define Threads credential bundle and publisher adapter
- Goal: add the smallest Threads publisher that can publish a stored draft body through the existing `PublishRequest` or `PublishResult` contract
- Actions:
  - inspect the current `XPublisher` implementation and confirm the smallest safe Threads credential contract from official provider requirements before locking the adapter shape
  - implement a `ThreadsPublisher` and isolated HTTP client boundary with normalized success, provider-error, and malformed-response handling
  - keep `credential_ref`, `provider`, and provider-payload reporting aligned with `PublishResult` so scheduler logging and publish-job detail remain useful
- Dependencies:
  - none
  - existing publisher boundary in `app/connectors/publishers/base.py`
- Verification commands:
  - `./.venv/bin/pytest tests/test_x_publisher.py tests/test_threads_publisher.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -k "publish_due_jobs_marks_jobs_published_with_publisher_resolver" -q`
- Risk or rollback note:
  - keep the adapter scoped to text-only publishing first; do not expand into media uploads, reply chains, or token refresh flow in the same slice
- Done when:
  - a Threads adapter returns normalized published or failed `PublishResult` values from the chosen credential bundle
  - malformed or non-2xx provider responses produce readable failure messages
  - existing X publisher behavior remains green
  - `docs/threads-api-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 02: Expand config-backed publisher resolution for Threads
- Goal: make the existing `publisher.credential_ref` env lookup sufficient to resolve Threads publishers without one-off operator steps
- Actions:
  - extend `ConfigPublisherResolver` to parse and validate a Threads credential bundle through the same env lookup path already used for X
  - keep per-channel resolver caching and failure normalization aligned across X and Threads
  - add focused resolver tests for success, missing env, invalid JSON, and missing required credential fields
- Dependencies:
  - Task 01
  - existing account or channel config loading
- Verification commands:
  - `./.venv/bin/pytest tests/test_x_publisher.py tests/test_threads_publisher.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -k "publish_due_jobs_live_defaults_to_config_publisher_resolver" -q`
- Risk or rollback note:
  - avoid config-schema redesign if `credential_ref` plus channel name is enough; only add extra non-secret config fields if Threads API requirements make them unavoidable
- Done when:
  - `threads` can resolve a live publisher from `accounts.yaml` plus one env bundle only
  - resolver continues to fail cleanly for incomplete Threads setup
  - X resolver behavior stays unchanged
  - `docs/threads-api-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 2: Workflow Integration

### Task 03: Make Threads review and scheduling flow publisher-aware
- Goal: let Threads drafts use the normal schedule or backfill path when live publish is configured, while preserving manual handoff fallback when it is not
- Actions:
  - replace static manual-only Threads branching in review approval and scheduling helpers with config-backed capability checks
  - preserve LinkedIn manual handoff semantics unchanged and keep manual Threads fallback active when no live publisher config exists
  - add workflow tests covering approve, schedule, and fallback permutations for Threads
- Dependencies:
  - Task 02
  - none
- Verification commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py -q`
- Risk or rollback note:
  - do not allow a Threads draft to create both a manual handoff and a scheduled publish job in the same state transition
- Done when:
  - Threads approval no longer auto-creates manual handoffs when live publishing is configured
  - `schedule_draft` accepts Threads only when a live publisher is configured
  - manual fallback remains explicit and test-covered when Threads live setup is absent
  - `docs/threads-api-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 04: Carry Threads live jobs through scheduler, API, and console surfaces
- Goal: make the existing operator surfaces reflect and execute the new Threads live path without duplicating publish logic
- Actions:
  - ensure backfill and `publish-due`, API responses, and console review hints or forms show Threads as live-publish-capable when configured
  - keep manual upload guidance visible only for channels or configs that genuinely require it
  - add focused API, console, and scheduler regressions for Threads live publish-job creation, visibility, and execution
- Dependencies:
  - Task 03
  - none
- Verification commands:
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest tests/test_scheduler.py tests/test_review_queue_workflow.py -q`
- Risk or rollback note:
  - preserve dry-run-by-default scheduler behavior and keep browser actions routed through the existing safe scheduler path instead of direct external publish calls
- Done when:
  - operator surfaces distinguish Threads-live and LinkedIn-manual paths using shared workflow data
  - scheduler can process due Threads jobs through the resolved publisher path
  - API and console regressions cover the live versus manual branching behavior
  - `docs/threads-api-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 3: Operator Docs And Hardening

### Task 05: Document token-ready Threads setup and expand regressions
- Goal: document how to enable Threads live publishing with a single env-referenced credential bundle and protect the shipped behavior with focused tests
- Actions:
  - update `README.md`, `docs/operator-console-guide.md`, and `docs/operator-control-plane-api.md` with Threads live setup, scheduler semantics, and fallback rules
  - add sample config or env examples that show Threads `publisher.credential_ref` usage without storing secrets in YAML
  - run focused regression and diff hygiene checks, then update the new progress tracker with final shipped behavior
- Dependencies:
  - Task 04
  - none
- Verification commands:
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py tests/test_review_queue_workflow.py tests/test_scheduler.py -q`
  - `git diff --check`
- Risk or rollback note:
  - document only the implemented Threads credential contract and publish shape; do not imply media upload, reply chaining, or LinkedIn live support unless they are actually shipped
- Done when:
  - docs show a concrete Threads token-ready setup path
  - tests and operator messaging match the shipped Threads-live versus LinkedIn-manual behavior
  - `docs/threads-api-publish-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Suggested execution order
1. Task 01
2. Task 02
3. Task 03
4. Task 04
5. Task 05

## Initial milestone recommendation
Start with the smallest milestone that:
- confirms the minimal official Threads credential contract and hides it behind one env-referenced bundle
- reuses the existing publisher resolver and scheduler path instead of building a new publish subsystem
- preserves manual fallback and the current review gate while Threads live publishing is being introduced
- can be implemented and verified without breaking the current structure

This keeps the next stage focused on token-ready Threads live publishing before expanding into LinkedIn adapters, token refresh automation, or richer media and reply features.
