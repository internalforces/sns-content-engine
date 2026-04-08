# Operator Control Plane API

This guide documents the operator-facing HTTP surfaces that sit on top of the existing review workflow, publish-job storage, and scheduler helpers.

## Safety Model

- Manual review remains the gate. Drafts stay in `pending_review` until an operator explicitly approves, rejects, edits, or schedules them.
- `POST /scheduler/publish-due` stays dry-run by default. Real publishing only happens when the request body includes `"live": true`.
- Read routes stay read-only. Only the review action and scheduler action routes can mutate stored state.

## Request Conventions

- Most routes accept `database_url` as an optional query parameter.
- Review and scheduler actions accept JSON request bodies.
- Review action routes accept `reviewer` and `config_dir`.
- Scheduler action routes accept `config_dir`, and `publish-due` also accepts `live`.
- Response timestamps are ISO 8601 strings in UTC.

## Review Surfaces

| Route | Kind | Purpose | Notes |
| --- | --- | --- | --- |
| `GET /reviews/pending` | read | List drafts waiting for review. | Returns `pending_count` plus queue rows for table views. |
| `GET /reviews/{draft_id}` | read | Load one operator-ready draft detail payload. | Includes `provenance`, `brief`, `source_item`, optional `article_enrichment`, `review_actions`, and `sibling_variants`. |
| `POST /reviews/{draft_id}/approve` | action | Approve a pending draft. | Preserves existing validation and manual review requirements. |
| `POST /reviews/{draft_id}/reject` | action | Reject a pending draft with a reason. | Requires `reason` in the request body. |
| `POST /reviews/{draft_id}/edit` | action | Replace the draft body while keeping it in review. | Requires `body` in the request body. |
| `POST /reviews/{draft_id}/schedule` | action | Create one publish job for an approved draft. | Requires explicit `scheduled_for`; returns the created `publish_job_id`. |

Minimal detail response shape:

```json
{
  "draft_id": 42,
  "draft_state": "pending_review",
  "body": "Useful AI automation workflows for operators",
  "provenance": {
    "source_name": "AI Tools Daily",
    "source_url": "https://example.com/drafts/42"
  },
  "brief": {
    "brief_id": 7,
    "title": "Brief for draft"
  },
  "source_item": {
    "source_item_id": 99,
    "title": "Draft source 42"
  },
  "review_actions": [],
  "sibling_variants": []
}
```

## Publish Surfaces

| Route | Kind | Purpose | Notes |
| --- | --- | --- | --- |
| `GET /publish-jobs` | read | List publish jobs for operator queue views. | Supports `state`, `account_key`, `channel`, and `limit` filters. |
| `GET /publish-jobs/{publish_job_id}` | read | Load one publish job with linked draft and publish-log context. | Includes `draft`, `provenance`, `brief`, `source_item`, and ordered `publish_logs`. |

Example list request:

```text
GET /publish-jobs?state=failed&account_key=ai_tools_daily&channel=x&limit=20
```

Example detail fields:

```json
{
  "publish_job_id": 5,
  "state": "scheduled",
  "draft": {
    "draft_id": 42,
    "draft_state": "approved"
  },
  "publish_logs": []
}
```

## Scheduler Action Surfaces

| Route | Kind | Purpose | Notes |
| --- | --- | --- | --- |
| `POST /scheduler/discover` | action | Run the configured discovery workflow and return a summary. | Returns processed source names plus failure messages. |
| `POST /scheduler/backfill` | action | Create missing future publish jobs from already approved drafts. | Reuses the current backlog planner and publish-job persistence. |
| `POST /scheduler/publish-due` | action | Evaluate due publish jobs. | Defaults to dry-run; set `"live": true` only for an explicit live publish run. |

Safe default request:

```json
{
  "config_dir": "config"
}
```

Explicit live request:

```json
{
  "config_dir": "config",
  "live": true
}
```

The `publish-due` response always echoes whether the run was dry-run or live through the top-level `dry_run` field.
