# Operator Console Guide

## What the console is

The operator console is the browser surface for the same FastAPI app, database, and review workflow that back the CLI and operator API.

- Manual review still gates publishing.
- Browser `publish-due` stays in dry-run mode unless you explicitly opt into one live run.
- The console does not add authentication, auto-approval, or hidden publish behavior.
- For remote personal-server use, keep the console behind an HTTPS edge layer and start from the [single-server deployment guide](./single-server-deployment-guide.md).

## Before you start

1. Prepare a config directory such as `config/` or your own copied example config.
2. Initialize or upgrade the database you want the console to read.
3. Seed data through the existing CLI if you want populated dashboard, review, or publish pages.

Example local setup:

```bash
sns-engine db init --database-url sqlite:///data/sns_content_engine.db
sns-engine run-local --config-dir config --database-url sqlite:///data/sns_content_engine.db
```

If you are reusing an older SQLite file, run `sns-engine db upgrade --database-url ...` before opening the console.

## Start the console locally

Run the FastAPI app with an ASGI server such as `uvicorn`:

```bash
python -m uvicorn app.api.app:app --reload
```

If `uvicorn` is not installed in your environment yet:

```bash
python -m pip install uvicorn
```

## Open the console

Open the console with the same operator context you use for the CLI:

```text
http://127.0.0.1:8000/console/?config_dir=config&database_url=sqlite:///data/sns_content_engine.db
```

Notes:

- `config_dir` tells review and scheduler actions which config set to use.
- `database_url` tells the console which SQLite database to read and mutate.
- The console keeps these query parameters across navigation so dashboard, review, publish, and scheduler pages stay on the same operator context.

## Main pages

- `Home`: quick orientation plus safety reminders.
- `Runs & Failures`: recent pipeline runs, technical failures, and policy skips.
- `Articles`: stored article and enrichment status rows.
- `Pending Review`: drafts waiting for manual review.
- `Review Detail`: approve, reject, edit, or schedule one draft while keeping current validation and audit behavior. Approved LinkedIn drafts always show copy-ready manual upload guidance. Approved Threads drafts show the schedule form when a live publisher resolves successfully and fall back to manual upload guidance when it does not.
- `Publish Jobs`: queued, published, failed, and cancelled jobs plus linked draft context. LinkedIn handoffs and manual-fallback Threads handoffs stay here until an operator records the final outcome.
- `Scheduler`: discover, backfill, and publish-due actions with dry-run-first messaging.

## Recommended local flow

1. Run `sns-engine run-local` to discover, enrich, build briefs, and generate drafts.
2. Open `Pending Review` and inspect one draft workspace.
3. Approve, reject, or edit the draft.
4. If the approved draft is `x`, use the schedule form and then follow its queued or published state through `Publish Jobs`.
5. If the approved draft is `threads` and the review page still shows the schedule form, treat it like a live-publish channel: schedule it directly or let `Scheduler -> Backfill` create a future slot.
6. If the approved draft is `linkedin`, or `threads` still shows manual upload guidance, copy the rendered body from the review page, publish it manually on the external platform, then open the linked publish job and record `완료`, `실패`, or `취소`.
7. Use `Scheduler` only for discovery, backfill, and due scheduled jobs after confirming the current live-publish queue.

## Manual handoff flow for LinkedIn and manual-fallback Threads

1. Approval creates an explicit publish-job record automatically for LinkedIn, and for Threads only when that account does not currently resolve a live publisher from `publisher.credential_ref`.
2. The review detail page keeps the approved body available as operator copy for the external platform.
3. The publish-job detail page shows manual action forms only while the handoff is still open.
4. `발행 완료 기록` stores the final state as `published` and can include an external post ID or link.
5. `발행 실패 기록` stores the handoff as `failed` with the readable error message you provide.
6. `전달 취소` closes the handoff as `cancelled` without sending it to the scheduler queue.

## Enabling Threads live publishing

1. Add `publisher.credential_ref` under the target `threads` channel in your chosen `accounts.yaml`.
2. Export the referenced environment variable as a JSON bundle with `access_token` and `threads_user_id`.
3. Reopen the console with the same `config_dir` and `database_url` so review and scheduler actions read the updated operator context.
4. Confirm the change by opening an approved Threads draft. When live publishing is configured correctly, the review page shows the schedule form instead of manual upload guidance.

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

Example env bundle:

```bash
export THREADS_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS='{"access_token":"replace-with-threads-user-access-token","threads_user_id":"replace-with-threads-user-id"}'
```

## Safety reminders

- Drafts stay in `pending_review` until an operator acts.
- Browser scheduling still uses the same validation, attribution, and provenance checks as the CLI and API.
- `publish-due` stays dry-run by default in the browser. Live publish only runs when you explicitly select the one-run live option.
- Live publish still depends on configured channel credentials from environment variables, not YAML secrets.
- LinkedIn handoffs are never auto-published by the browser. Threads handoffs are also manual-only whenever live credentials are missing, invalid, or not configured for that account.
- Scheduler backfill and review-page scheduling only treat Threads as live-publish-capable when the configured account can resolve a live Threads publisher. Otherwise the console keeps Threads on the manual handoff path.
- Manual handoff forms disappear after a job reaches `published`, `failed`, or `cancelled`; if a fresh post is needed later, start from a new approved draft or new handoff instead of reopening the terminal job.

## Related guides

- [Operator control-plane API guide](./operator-control-plane-api.md)
- [Finance Local MVP guide](./finance-local-operator-guide.md)
- [All-domain news guide](./all-domain-news-operator-guide.md)
