# Operator Control Plane API

This guide documents the operator-facing HTTP surfaces that sit on top of the existing review workflow, publish-job storage, and scheduler helpers.

## Remote personal-server access

The same FastAPI app serves both the browser console and these JSON routes. For `sns.gilgop.cloud`, keep that app bound to `127.0.0.1:8000` and put the checked-in Caddy plus Basic Auth layer in front of the operator API.

- Do not expose `/reviews/...`, `/publish-jobs/...`, or `/scheduler/...` directly on a public bind.
- The checked-in edge baseline leaves `/health` open for simple probes and protects every other route with Basic Auth.
- This API does not add in-app auth, so use a stricter edge policy such as IP allowlists, a VPN, or a zero-trust gateway when Basic Auth alone is not enough for your environment.

## Safety Model

- Manual review remains the gate. Editing keeps a draft in `pending_review`; approval or rejection records the decision, and only an approved live-capable draft can be scheduled.
- Approving `ghost` and `linkedin` drafts always creates an explicit manual publish handoff job instead of a scheduled live-publish slot.
- Approving `threads` drafts creates that same manual handoff only when the configured account does not resolve a live Threads publisher from `publisher.credential_ref`. Otherwise the approved draft stays on the normal scheduled publish path.
- `POST /scheduler/publish-due` stays dry-run by default. Real publishing only happens when the request body includes `"live": true`.
- Manual Ghost, LinkedIn, and manual-fallback Threads handoffs are never picked up by `publish-due`; operators finish them through the manual publish routes after uploading on the external platform.
- X, Threads, and LinkedIn draft generation keeps pointing at the original article URL; a Ghost URL recorded on a manual publish job is not used as a replacement social link in this phase.
- Read routes stay read-only. Only the review action and scheduler action routes can mutate stored state.

## Request Conventions

- Most routes accept `database_url` as an optional query parameter.
- Review and scheduler actions accept JSON request bodies.
- Review action routes accept `reviewer` and `config_dir`.
- Manual publish action routes accept `operator` and optionally `external_post_id` or `reason`; the failure route requires `error_message`.
- Scheduler action routes accept `config_dir`, and `publish-due` also accepts `live`.
- Response timestamps are ISO 8601 strings in UTC.

Remote access examples:

```bash
curl -fsS "http://127.0.0.1:8000/health?config_dir=/opt/sns-content-engine/config"
curl -u operator:replace-with-password \
  "https://sns.gilgop.cloud/reviews/pending?database_url=sqlite:////opt/sns-content-engine/data/sns_content_engine.db"
```

## Health And Read-Only Operations

| Route | Purpose | Notes |
| --- | --- | --- |
| `GET /health` | Validate config and database readiness. | Accepts `config_dir` and `database_url`; returns a non-`ok` response status when required checks fail. |
| `GET /runs` | List persisted pipeline runs. | Includes stage counts, policy-skip counts, attribution counts, and rewrite providers. |
| `GET /failures` | List enrichment failures and policy skips. | Returns ordinary failures and intentional policy skips in separate arrays. |
| `GET /articles` | List article/enrichment status rows. | Supports a `limit` parameter. |

These routes are read-only. `/health` uses the selected config and database context; the history and article routes use `database_url`.

## Review Surfaces

| Route | Kind | Purpose | Notes |
| --- | --- | --- | --- |
| `GET /reviews/pending` | read | List drafts waiting for review. | Returns `pending_count` plus queue rows for table views. |
| `GET /reviews/{draft_id}` | read | Load one operator-ready draft detail payload. | Includes `provenance`, `brief`, `source_item`, optional `article_enrichment`, `review_actions`, and `sibling_variants`. |
| `POST /reviews/{draft_id}/approve` | action | Approve a pending draft. | Preserves existing validation and manual review requirements. `ghost` and `linkedin` always return the created manual handoff `publish_job_id`. `threads` returns that field only when the account falls back to manual handoff instead of live scheduling. |
| `POST /reviews/{draft_id}/reject` | action | Reject a pending draft with a reason. | Requires `reason` in the request body. |
| `POST /reviews/{draft_id}/edit` | action | Replace the draft body while keeping it in review. | Requires `body` in the request body. |
| `POST /reviews/{draft_id}/schedule` | action | Create one publish job for an approved draft. | Requires explicit `scheduled_for`; returns the created `publish_job_id`. This route accepts channels with a live publisher, including live-configured Threads, and rejects LinkedIn plus manual-fallback Threads so the scheduler queue stays limited to scheduled publisher flows. |

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
| `GET /publish-jobs/{publish_job_id}` | read | Load one publish job with linked draft and publish-log context. | Includes `draft`, `provenance`, `brief`, `source_item`, and ordered `publish_logs`. Manual handoffs start with a `manual_handoff_created` log entry. |
| `POST /publish-jobs/{publish_job_id}/manual/complete` | action | Record a successful manual Ghost, LinkedIn, or Threads fallback publish. | Accepts optional `external_post_id`; for Ghost, store the final article URL here. Returns the previous and final publish state. |
| `POST /publish-jobs/{publish_job_id}/manual/fail` | action | Record a failed manual Ghost, LinkedIn, or Threads fallback publish. | Requires `error_message`; stores the message in the publish job and log timeline. |
| `POST /publish-jobs/{publish_job_id}/manual/cancel` | action | Cancel an open manual handoff without publishing. | Accepts an optional `reason`; closes the handoff as `cancelled`. |

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

Example manual completion request:

```json
{
  "operator": "publisher-a",
  "external_post_id": "linkedin-post-456"
}
```

Example manual outcome response:

```json
{
  "publish_job_id": 5,
  "channel": "linkedin",
  "operator": "publisher-a",
  "previous_state": "scheduled",
  "publish_job_state": "published",
  "external_post_id": "linkedin-post-456",
  "last_error": null,
  "published_at": "2026-03-18T13:05:00+00:00"
}
```

Manual publish error behavior:

- `409 manual_publish_state_conflict`: the handoff is already in a terminal state such as `published`, `failed`, or `cancelled`
- `422 manual_publish_invalid`: the route was used for a non-manual channel or the request payload was invalid, such as an empty failure message

## Threads live setup

Threads uses the same env-referenced credential lookup shape as X. Add a `publisher.credential_ref` entry under the target `threads` channel and export the referenced JSON bundle through the environment only.

Example config fragment:

```yaml
threads:
  schedule:
    cron: "0 11 * * *"
  render:
    max_chars: 10000
  publisher:
    credential_ref: THREADS_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS
```

Example credential bundle:

```bash
export THREADS_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS='{"access_token":"replace-with-threads-user-access-token","threads_user_id":"replace-with-threads-user-id"}'
```

When that bundle is missing, malformed, or incomplete, the API keeps Threads on the manual handoff path. When it resolves successfully, `POST /reviews/{draft_id}/approve`, `POST /reviews/{draft_id}/schedule`, `POST /scheduler/backfill`, and `POST /scheduler/publish-due` treat Threads as a live-publish-capable channel.

## Ghost long-form handoff

The `ghost` channel is manual-only in this slice. Generated Ghost drafts stay in the same review queue, but approval creates a manual handoff publish job rather than a scheduled job. After the operator publishes or saves the article in Ghost, call `POST /publish-jobs/{publish_job_id}/manual/complete` and place the final Ghost article URL in `external_post_id`. That recorded URL is the long-form handoff outcome only; social drafts keep their original article URLs.

## Scheduler Action Surfaces

| Route | Kind | Purpose | Notes |
| --- | --- | --- | --- |
| `POST /scheduler/discover` | action | Run the configured discovery workflow and return a summary. | Returns processed source names plus failure messages. |
| `POST /scheduler/backfill` | action | Create missing future publish jobs from already approved drafts. | Reuses the current backlog planner and publish-job persistence. Only channels with a live publisher are eligible, so LinkedIn and manual-fallback Threads are skipped automatically. |
| `POST /scheduler/publish-due` | action | Evaluate due publish jobs. | Defaults to dry-run; set `"live": true` only for an explicit live publish run. Only scheduled jobs are eligible, so manual Ghost, LinkedIn, and manual-fallback Threads handoffs stay outside this queue. |

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
