# Operator Console Readiness Roadmap

## Goal
Extend the current control-plane-ready backend into a local operator-console-ready web surface that:
- provides a browser-based operator console for run history, article status, review work, and publish visibility
- reuses the existing FastAPI, workflow, repository, and scheduler surfaces instead of introducing a separate platform
- allows operators to perform the current review and safe scheduler actions without shell access
- preserves manual review and dry-run publish defaults while keeping the first UI stage small and local-friendly

## Generated document naming
When instantiating this template, use a filename that clearly shows the document identity.

- Roadmap file: `docs/operator-console-readiness-roadmap.md`
- Execution guide file: `docs/operator-console-readiness-execution-guide.md`
- Progress tracker file: `docs/operator-console-readiness-progress-tracker.md`
- Avoid ambiguous names like `todo.md`, `plan.md`, or `notes.md` when multiple initiatives may exist.

## Roadmap construction rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- Define only as many milestones and tasks as are needed to reach the goal while keeping each unit safely implementable.
- Choose task and milestone boundaries so the work can be completed without breaking the existing architecture, workflow semantics, safety gates, or operator experience.
- Prefer the smallest additive slices that reuse the current FastAPI and workflow structure instead of forcing a separate SPA or service split.
- Split a task when it would otherwise span unrelated UI surfaces, require unclear rollback, or make testing too broad.
- Merge adjacent tiny tasks when they share the same code path, verification surface, and branch scope.
- If the roadmap shape changes during implementation, update this file and `docs/operator-console-readiness-progress-tracker.md` before continuing.

## Current implementation snapshot

### Already implemented
- A working FastAPI application already exposes health, runs, failures, articles, pending review drafts, review detail, publish-job reads, review actions, and scheduler action wrappers.
- The repository already has explicit UI-facing data contract notes for run overview, article status, draft review, and failure visibility.
- Manual review, publish validation, and dry-run publish defaults are already enforced in the workflow and API layers.
- `jinja2` is already a project dependency, so a server-rendered web console can be added without introducing a Node toolchain by default.

### Current limitations relevant to the new goal
- There is no browser-facing operator console yet, so operators still need CLI output or raw API calls.
- The repository has no template, static-asset, or page-route structure for an operator web surface.
- No browser-facing regression coverage exists yet for linked run, article, review, publish, and scheduler workflows.
- Operator-facing docs explain the API and CLI surfaces, but not how to run or use a local console.

## Environment and execution assumptions
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `sns-engine db init --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands already available:
  - `PYTHONPATH=$PWD pytest tests/test_api.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_review_queue_workflow.py tests/test_scheduler.py`
- Broader regression commands:
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py tests/test_review_queue_workflow.py`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_cli.py`
- Required local services:
  - `none for read-only and dry-run console work`
  - `a local SQLite database file when testing against real data instead of fixtures`
- Required env files, secrets, or fixtures:
  - `config/` or another operator-approved config directory
  - `temporary SQLite fixtures or sqlite:///data/sns_content_engine.db`
- Package install policy: `ask_first`

## Target architecture

### Console shell
- `server_rendered_pages`
  - FastAPI routes under a dedicated console path render operator pages through Jinja templates.
  - Shared layout, navigation, and lightweight static assets keep the first version local-friendly and dependency-light.
- `shared_presenters`
  - Page handlers reuse the existing workflow and repository-backed read/action helpers.
  - If duplication appears, extract shared serialization or presentation helpers instead of routing page logic through in-process HTTP calls.

### Operator workflows
1. Load run, failure, and article data into browser-friendly pages.
2. Render pending-review list and one-draft review detail with linked provenance and audit context.
3. Expose approve, reject, edit, and schedule actions through form posts or small progressive-enhancement handlers that reuse current validation.
4. Surface publish-job visibility and scheduler actions with explicit dry-run and live-publish safety messaging.

## Milestones

### Milestone M1: Read-Only Console Foundation
- Goal: Add a small operator console shell and the first read-only pages that make current run, article, and review queue data usable in a browser.
- Includes:
  - console shell, base template, and navigation
  - read-only dashboard, article list, and pending-review queue pages
- Excludes:
  - review mutation forms
  - publish-job and scheduler action pages
- Verification target:
  - focused console route coverage
  - existing API and query regressions for the same linked data
- Ship when:
  - an operator can browse the latest run, failure, article, and pending-review data without the CLI
  - the console reuses current backend queries without weakening safety semantics

### Milestone M2: Review Workspace
- Goal: Make the browser console sufficient for day-to-day manual review work without changing review semantics.
- Includes:
  - one-draft detail page with provenance, brief, enrichment, audit history, and sibling variants
  - approve, reject, edit, and schedule interactions with readable validation feedback
- Excludes:
  - publish-job detail pages
  - auth and multi-user review ownership
- Verification target:
  - focused console review tests
  - broader review-workflow and API regressions
- Ship when:
  - an operator can complete the current review flow in the console
  - validation failures stay aligned with the current review queue behavior

### Milestone M3: Publish And Scheduler Controls
- Goal: Complete the first local operator console by exposing publish-job visibility and safe scheduler controls in the browser.
- Includes:
  - publish-job list and detail pages
  - scheduler discover, backfill, and publish-due controls with dry-run-first UX
  - operator docs and browser-facing regression coverage
- Excludes:
  - authentication and remote multi-user deployment hardening
  - background websocket or real-time refresh infrastructure
- Verification target:
  - focused publish and scheduler console coverage
  - broader API and scheduler regressions
- Ship when:
  - an operator can inspect publish history and trigger safe scheduler workflows from the console
  - dry-run publish remains the default browser path and live publish still requires explicit opt-in

## Implementation roadmap

## Phase 1: Console Foundation

### Task 01: Console shell and template infrastructure
- Goal: Add the smallest shared template and static-asset structure needed to serve browser pages from the existing FastAPI app.
- Actions:
  - add a dedicated console route namespace, base template, and navigation shell
  - add minimal static assets and rendering helpers without introducing a Node build step by default
  - add focused route tests for the shell and top-level console landing behavior
- Dependencies:
  - none
  - existing FastAPI app structure in `app/api/app.py`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -k "console_shell"`
  - `PYTHONPATH=$PWD pytest tests/test_api.py -k "health"`
- Risk or rollback note:
  - keep the shell additive so it can be removed cleanly if a later frontend approach changes direction
- Done when:
  - a dedicated console route exists
  - templates and static assets are wired without a separate frontend toolchain
  - focused tests cover the new page entrypoint
  - `docs/operator-console-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 02: Run overview and failure dashboard pages
- Goal: Expose current run and failure history in a browser-friendly operator dashboard.
- Actions:
  - build a dashboard page that surfaces recent run summaries and the latest readable failures or policy skips
  - reuse `history_queries` instead of duplicating read logic
  - add focused page tests for empty and populated dashboard states
- Dependencies:
  - Task 01
  - `app.workflows.history_queries`
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -k "dashboard"`
  - `PYTHONPATH=$PWD pytest tests/test_history_queries.py tests/test_api.py -k "runs or failures"`
- Risk or rollback note:
  - keep dashboard shaping presentational so the underlying run/failure query contract stays unchanged
- Done when:
  - the console shows recent runs, policy-aware counts, and readable failure rows
  - empty-state and populated-state dashboard behavior are covered
  - the backend query path remains shared with the existing API and CLI surfaces
  - `docs/operator-console-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 03: Article status and pending-review queue pages
- Goal: Render article status rows and pending-review queue data in browser pages that match the existing UI contract notes.
- Actions:
  - add article list and pending-review pages with stable table-friendly ordering
  - reuse the current article status and pending-review helpers instead of introducing a new read model
  - add focused tests for empty and populated list states
- Dependencies:
  - Task 01
  - Task 02
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -k "articles or pending_review"`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_review_queue_workflow.py -k "articles or pending_review"`
- Risk or rollback note:
  - keep list filtering and ordering modest in the first version so browser work does not force query redesign
- Done when:
  - an operator can browse article status rows and pending review drafts without using the CLI
  - linked fields stay aligned with the current stored data and UI contract notes
  - focused console coverage protects empty and populated states
  - `docs/operator-console-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 2: Review Workspace

### Task 04: Review draft detail page
- Goal: Add a browser detail page for one draft that reuses the existing operator-ready review detail read path.
- Actions:
  - render the linked draft, provenance, brief, source-item, enrichment, review-action, and sibling-variant context into a detail page
  - keep route handlers thin and reuse the existing detail fetcher
  - add focused tests for populated and not-found detail states
- Dependencies:
  - Task 03
  - current review detail API and workflow helpers
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -k "review_detail"`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_review_queue_workflow.py -k "review_detail"`
- Risk or rollback note:
  - avoid page-specific data access shortcuts that diverge from the current review detail contract
- Done when:
  - one draft detail page shows the same high-value context already exposed through the API
  - missing drafts return a clear browser-friendly not-found response
  - focused tests cover empty and populated states
  - `docs/operator-console-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 05: Review action forms and safe mutation feedback
- Goal: Let operators approve, reject, edit, and schedule drafts from the console while preserving the current review guardrails.
- Actions:
  - add forms or small progressive-enhancement handlers for the four review actions
  - map current validation and state-conflict errors into readable page feedback without altering workflow semantics
  - add focused tests for successful actions and representative validation failures
- Dependencies:
  - Task 04
  - existing review action routes or underlying workflow helpers
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -k "review_actions"`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_review_queue_workflow.py -k "approve or reject or edit or schedule"`
- Risk or rollback note:
  - keep all mutations routed through existing validation paths so the console cannot bypass policy and attribution blockers
- Done when:
  - all four review actions can be triggered from the browser
  - validation failures remain readable and aligned with the current API behavior
  - manual review remains the explicit gate before publish scheduling
  - `docs/operator-console-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 3: Publish And Scheduler Controls

### Task 06: Publish job list and detail pages
- Goal: Expose publish-job queue and timeline visibility through browser pages.
- Actions:
  - add publish-job list and one-job detail pages
  - reuse the current publish-job list/detail helpers and serialize linked draft/source context into templates
  - add focused tests for empty, successful, and failed job states
- Dependencies:
  - Task 01
  - existing publish-job API and repository-backed read helpers
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -k "publish_jobs"`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py -k "publish_jobs or publish_job_detail"`
- Risk or rollback note:
  - keep the first version read-only so publish inspection lands before any new browser mutation surface
- Done when:
  - an operator can browse queued, published, and failed jobs in the console
  - one job detail page exposes timestamps, errors, linked draft metadata, and publish-log events
  - focused tests cover the expected empty and populated states
  - `docs/operator-console-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 07: Scheduler action console with safe defaults
- Goal: Expose discover, backfill, and publish-due controls in the browser without weakening the current safety model.
- Actions:
  - add scheduler action forms or buttons for discover, backfill, and publish-due
  - keep publish-due dry-run by default and require an explicit live opt-in control before real publish
  - add focused tests for default dry-run behavior, discover/backfill summaries, and explicit live confirmation wiring
- Dependencies:
  - Task 06
  - existing scheduler action wrappers
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py -k "scheduler_actions"`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py -k "scheduler_discover_endpoint or scheduler_backfill_endpoint or scheduler_publish_due_endpoint"`
- Risk or rollback note:
  - keep live publish behind an explicit operator step so the browser console cannot silently change the current publish default
- Done when:
  - an operator can trigger discover, backfill, and dry-run publish-due from the console
  - the UI makes dry-run status obvious and live publish explicit
  - focused tests cover safe defaults and representative action summaries
  - `docs/operator-console-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 08: Console operator docs and browser-facing regression coverage
- Goal: Document the console and add regression coverage that protects its linked browser contract.
- Actions:
  - add a concise operator guide for starting and using the console locally
  - expand console tests so read-only and mutation-heavy screens are protected by realistic linked fixtures
  - update README links only after the console surface exists and the guide matches reality
- Dependencies:
  - Tasks 01 through 07
  - existing operator docs
- Verification commands:
  - `PYTHONPATH=$PWD pytest tests/test_console.py`
  - `PYTHONPATH=$PWD pytest tests/test_api.py tests/test_scheduler.py tests/test_review_queue_workflow.py`
- Risk or rollback note:
  - keep docs tied to implemented behavior so planning language does not get mistaken for shipped operator guidance
- Done when:
  - the repository has one clear console operator reference
  - linked browser-facing regression coverage exists for the core console paths
  - README and console docs consistently restate manual-review and dry-run safety
  - `docs/operator-console-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Suggested execution order
1. Task 01
2. Task 02
3. Task 03
4. Task 04
5. Task 05
6. Task 06
7. Task 07
8. Task 08

## Initial milestone recommendation
Start with the smallest milestone that:
- adds a console shell without introducing a separate frontend build stack
- exposes current run, failure, article, and pending-review data in browser pages
- proves the browser surface can reuse the current backend queries and safety semantics
- can be implemented and verified without breaking the current structure

This keeps the next stage focused on making the current backend operable through a browser before expanding into mutation-heavy review workflows, publish controls, or later deployment hardening.
