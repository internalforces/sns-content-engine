# Operator Control Plane Readiness TODO (Historical)

## Status
- This roadmap is complete and kept as historical context.
- Do not resume implementation from this file; active follow-on publish workflow work now lives in `docs/multichannel-manual-publish-readiness-roadmap.md`.
- See `docs/operator-control-plane-readiness-progress.md` for the shipped task record and commit history.

## Goal
Extend the current backend-ready operator API into a control-plane-ready next stage that:
- exposes full review-draft context needed for a real operator screen,
- exposes publish-job state and publish logs without requiring CLI output or direct DB access,
- adds safe scheduler action endpoints for remote operator workflows,
- preserves the current manual-review gate and dry-run publish defaults.

## Current implementation snapshot

### Already implemented
- A real FastAPI application with read endpoints for health, runs, failures, articles, and pending review drafts.
- Review action API routes for approve, reject, edit, and schedule that reuse the existing review workflow and validation path.
- Scheduler workflows for discover, backfill, and publish-due execution, plus operational logging and dry-run publish behavior.
- Stored review audit rows, publish jobs, and publish logs in the SQLite-backed local persistence layer.

### Current limitations relevant to the new goal
- The pending-review API only exposes queue rows, not the full draft context a review screen would need.
- No API route exposes review-action history, sibling draft variants, or linked brief/provenance details for one draft.
- Publish jobs and publish logs are persisted, but operators cannot inspect them through the current API.
- Scheduler workflows can only be triggered through the CLI today, so a future UI or remote operator layer would need shell access.
- Live publishing should remain explicitly guarded and not become the default API behavior.

## Target architecture

### Review surfaces
- `queue_reads`
  - Pending review listing for table views and counters.
- `draft_detail`
  - Full review context for one draft: source provenance, regenerated summary, key points, draft body, state, sibling variants, and audit timeline.

### Operations surfaces
1. Publish-job listing with modest filters for state, account, and channel.
2. Publish-job detail with linked draft metadata and publish-log timeline.
3. Scheduler-safe action endpoints for discover, backfill, and dry-run publish execution.

## Historical roadmap

## Phase 1: Review detail surfaces

### 1. Add a review-draft detail endpoint
- Add a query/helper path that can load one draft variant together with its linked brief, source item, and article enrichment data.
- Expose one operator-ready API route for a single draft detail view.
- Keep the API handler thin and prefer reuse over a new parallel workflow layer.
- Done when:
  - a future UI can fetch one review draft with source, summary, key points, and state in one request,
  - missing drafts return a clear API error,
  - focused tests cover both populated and not-found cases.

### 2. Add review audit and sibling-variant visibility
- Expose review-action history for a draft, including approve, reject, edit, and schedule events.
- Expose sibling variants for the same content brief and channel so operators can compare alternatives.
- Keep response ordering stable and practical for UI rendering.
- Done when:
  - a future review screen can render an action timeline and alternative variants,
  - API responses stay aligned with stored audit data instead of reconstructing history from logs,
  - tests cover empty-history and populated-history behavior.

## Phase 2: Publish visibility

### 3. Add a publish-job list endpoint
- Expose scheduled, publishing, published, failed, and cancelled jobs through the API.
- Support modest filters for state, account key, channel, and limit.
- Reuse the existing publish-job persistence model and linked draft metadata instead of inventing a separate read model.
- Done when:
  - operators can inspect queued and failed publish work through HTTP,
  - filters behave predictably,
  - tests cover representative state mixes and empty states.

### 4. Add publish-job detail and log timeline endpoints
- Expose one job's timestamps, last error, external post id, linked draft/source context, and publish-log events.
- Keep the first version additive and serialization-focused.
- Prefer using the existing `publish_logs` table and repository methods instead of new logging abstractions.
- Done when:
  - a future UI or remote operator can inspect why one publish job succeeded or failed,
  - publish-log events are visible in API responses,
  - tests cover successful, failed, and no-log paths.

## Phase 3: Scheduler-safe control surfaces

### 5. Add scheduler action endpoints with safe defaults
- Add thin API wrappers for scheduler discover, backfill, and publish-due execution.
- Keep `publish-due` dry-run by default.
- If live execution is exposed at all, require an explicit opt-in flag and preserve the current publisher validation path.
- Done when:
  - operator automation can trigger safe scheduler workflows through the API,
  - dry-run remains the default behavior for publish execution,
  - tests cover happy-path results and the default dry-run guardrail.

## Phase 4: Contract hardening and operator docs

### 6. Document the control-plane API and expand regression coverage
- Update README and/or add focused docs for review-detail, publish-job, and scheduler-action API usage.
- Extend API tests so the new contract is protected by realistic linked-data fixtures.
- Keep docs operator-facing and consistent with the existing safety model.
- Done when:
  - future UI or automation work has one clear API contract reference,
  - focused API and scheduler-adjacent tests cover the new surfaces,
  - docs make it explicit that manual review and safe publish defaults still apply.

## Suggested execution order
1. Review-draft detail endpoint.
2. Review audit and sibling-variant visibility.
3. Publish-job list endpoint.
4. Publish-job detail and log timeline endpoints.
5. Scheduler action endpoints with safe defaults.
6. Contract docs and regression coverage.

## Follow-on initiative
This roadmap is complete. Current follow-on operator publish-lifecycle work continues in `docs/multichannel-manual-publish-readiness-roadmap.md`.

## Recommended first milestone
Ship a small "operator control plane basics" milestone with:
- a single-draft review detail API,
- review audit and sibling-variant visibility,
- publish-job list and detail reads,
- scheduler discover/backfill/dry-run publish action endpoints.

This keeps the next stage focused on making the current backend actually operable by a UI or remote operator layer before considering auth, frontend implementation, or broader platform changes.
