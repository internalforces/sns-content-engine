# Operator Console Guide

## What the console is

The operator console is the browser surface for the same FastAPI app, database, and review workflow that back the CLI and operator API.

- Manual review still gates publishing.
- Browser `publish-due` stays in dry-run mode unless you explicitly opt into one live run.
- The console does not add authentication, auto-approval, or hidden publish behavior.
- For remote personal-server use, keep the console and JSON API behind the checked-in Caddy plus Basic Auth edge layer from the [single-server deployment guide](./single-server-deployment-guide.md).

## Before you start

1. Prepare a config directory such as `config/` or your own copied example config.
2. Initialize or upgrade the database you want the console to read.
3. Seed data through the existing CLI if you want populated dashboard, review, or publish pages.
4. For the first protected live rollout, plan to keep `x` as the only live-publish channel. Leave LinkedIn manual-only and keep Threads on the manual fallback path unless you are intentionally doing a later Threads rollout.

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

`uvicorn` is now included in the runtime dependency set, so the normal project install is enough for local console startup.

## Open the console

Open the console with the same operator context you use for the CLI:

```text
http://127.0.0.1:8000/console/?config_dir=config&database_url=sqlite:///data/sns_content_engine.db
```

Notes:

- `config_dir` tells review and scheduler actions which config set to use.
- `database_url` tells the console which SQLite database to read and mutate.
- The console keeps these query parameters across navigation so dashboard, review, publish, and scheduler pages stay on the same operator context.
- This loopback URL is the local-only path. For remote use, keep the app on loopback and open the same console through `https://sns.gilgop.cloud/console/...` only after Caddy has applied the checked-in Basic Auth gate.

## Remote personal-server baseline

For `sns.gilgop.cloud`, the checked-in default is the Caddy reverse-proxy baseline under `deploy/caddy/`.

- Keep `uvicorn` bound to `127.0.0.1:8000`; do not expose the app port directly.
- Let Caddy terminate HTTPS and enforce Basic Auth before requests reach the app.
- Treat the Basic Auth layer as protecting the whole operator surface, not just `/console`, because the same FastAPI app also exposes state-changing JSON routes.
- The checked-in Caddy baseline leaves `/health` open for simple probes and protects every other route, including `/console`, `/reviews/...`, `/scheduler/...`, and publish-job actions.
- If you need remote browser access, use `https://sns.gilgop.cloud/console/?config_dir=/opt/sns-content-engine/config` after the Basic Auth prompt. Do not rebind `uvicorn` to `0.0.0.0` just to avoid the reverse proxy.
- If Basic Auth alone is not strong enough for your environment, add IP allowlists, a VPN, or a zero-trust gateway in front of the same Caddy entrypoint instead of removing the edge gate.

## Main pages

- `Home`: quick orientation plus safety reminders.
- `Runs & Failures`: recent pipeline runs, technical failures, and policy skips.
- `Articles`: stored article and enrichment status rows.
- `Pending Review`: drafts waiting for manual review.
- `Review Detail`: approve, reject, edit, or schedule one draft while keeping current validation and audit behavior. Sensitive country-news drafts show a review note when the title, summary, or tags match politics, security, legal, disaster, health, finance, or diplomacy cues. Approved Ghost and LinkedIn drafts always show copy-ready manual upload guidance. Approved Threads drafts show the schedule form when a live publisher resolves successfully and fall back to manual upload guidance when it does not.
- `Publish Jobs`: queued, published, failed, and cancelled jobs plus linked draft context. Ghost, LinkedIn, and manual-fallback Threads handoffs stay here until an operator records the final outcome.
- `Scheduler`: discover, backfill, and publish-due actions with dry-run-first messaging.

## Recommended local flow

1. Run `sns-engine run-local` to discover, enrich, build briefs, and generate drafts.
2. Open `Pending Review` and inspect one draft workspace.
3. Approve, reject, or edit the draft.
4. If the approved draft is `x`, use the schedule form and then follow its queued or published state through `Publish Jobs`.
5. For the first live rollout, do not use the optional Threads live path even if the review page could show the schedule form later. Keep Threads on the manual upload path until a separate Threads rollout is intentionally prepared.
6. If the approved draft is `ghost`, `linkedin`, or `threads` still shows manual upload guidance, copy the rendered body from the review page, publish it manually on the external platform, then open the linked publish job and record `완료`, `실패`, or `취소`.
7. Use `Scheduler` only for discovery, backfill, and due scheduled jobs after confirming the current live-publish queue.

## Country news cadence baseline

The Phase 1.5 Korea/Japan country-news config is tuned for review-led operation, not volume:

- Korea X keeps at most one future scheduled job, anchored at `09:00 UTC` with a 60-minute window and 15-minute deterministic jitter.
- Japan X keeps at most one future scheduled job, anchored at `09:30 UTC` with the same window and jitter.
- X schedules require a 720-minute same account/channel gap, so accidental backlog increases still avoid crowded same-day posting.
- Source ingestion and draft validation use 7-day duplicate windows to reduce repeated wire coverage and identical social drafts.
- LinkedIn and Threads remain manual handoff channels unless a separate live rollout intentionally configures a resolvable publisher.
- Ghost long-form drafts are generated as review-led manual handoffs with a 12,000 character cap, 8-link review allowance, and no live API publishing.

## Ghost long-form handoff baseline

The Phase 2 first slice adds a `ghost` draft channel for Korea/Japan country news. Ghost is the selected primary owned long-form home, but the app does not publish to Ghost directly yet.

1. Generate drafts through the normal local pipeline or `generate-drafts`; Ghost variants enter the same pending-review queue as social drafts.
2. Review the Ghost draft as a long-form article, checking headline, dek, context sections, source attribution, and the source URL.
3. Approve only after the article body is ready for manual Ghost copy/paste.
4. Approval creates a manual publish handoff job instead of a scheduled live-publish job.
5. Publish or save the article manually in Ghost, then record the final Ghost URL through the publish-job detail page.
6. Use `실패` or `전달 취소` if the Ghost article should not be recorded as published.

## Country news live-publish quality checklist

Use this checklist before scheduling an X draft or recording a manual LinkedIn/Threads handoff for the Korea/Japan country-news accounts.

1. Check the article URL.
   - Open the source URL from the review detail page and confirm it reaches the specific article, not a homepage, tag page, or unrelated landing page.
   - Confirm the visible article topic still matches the draft title and summary.
   - Stop if the URL is broken, paywall-only without enough review context, redirected to unrelated content, or no longer supports the draft.

2. Check source attribution.
   - For X, confirm a compact `Source: ...` cue appears before the URL when attribution is required.
   - For LinkedIn and Threads, confirm the source name or hostname is visible in the body or review context before manual upload.
   - Edit before approval if the source is ambiguous, missing, or names the wrong outlet.

3. Check summary accuracy.
   - Verify the draft states only what the article or regenerated summary supports.
   - Keep dates, numbers, names, places, legal status, casualty or damage figures, and official statements aligned with the source.
   - Reject or edit drafts that speculate about motives, outcomes, market impact, diplomatic intent, health risk, or legal guilt beyond the source.

4. Check category and coverage fit.
   - Korea drafts should be meaningfully about Korea, South Korea, North Korea, Seoul, Korean politics, economy, society, science, culture, diplomacy, or inter-Korean affairs.
   - Japan drafts should be meaningfully about Japan, Tokyo, Osaka, Kyoto, Japanese politics, economy, society, culture, public safety, or national institutions.
   - Reject broad world, sports, entertainment, market, or wire-repeat stories when the country relevance is weak.

5. Check sensitive-topic cues.
   - Treat politics, security, legal, disaster, health, finance, and diplomacy notes as stop-and-check prompts, not as automatic rejection.
   - Confirm sensitive drafts use sober wording, avoid blame or certainty not present in the source, and leave the reviewable facts easy to trace.
   - Prefer rejection over scheduling when a sensitive draft cannot be verified quickly from the source.

6. Decide the action.
   - `Reject` low-value duplicates, weak country matches, stale wire repeats, broken URLs, unverifiable sensitive claims, or drafts that would need a full rewrite.
   - `Edit` drafts that are basically sound but need attribution, shorter X wording, clearer dates, or less speculative phrasing.
   - `Approve` only after the URL, attribution, accuracy, category fit, and sensitivity checks pass.
   - `Schedule` X only after approval and with dry-run-first expectations. For LinkedIn and Threads manual handoff, use the rendered approved body and then record the final external result in the publish job.

7. Stop the live run when needed.
   - Stop if multiple drafts repeat the same source story inside the 7-day duplicate window.
   - Stop if the current account already has a future X job and the new draft is not clearly better.
   - Stop if a publisher credential, account identity, or external platform state is uncertain.
   - Stop if a real-world emergency or fast-moving legal, disaster, security, or health story needs fuller context than a short social draft can provide.

## Manual handoff flow for Ghost, LinkedIn, and manual-fallback Threads

1. Approval creates an explicit publish-job record automatically for Ghost and LinkedIn, and for Threads only when that account does not currently resolve a live publisher from `publisher.credential_ref`.
2. The review detail page keeps the approved body available as operator copy for the external platform.
3. The publish-job detail page shows manual action forms only while the handoff is still open.
4. `발행 완료 기록` stores the final state as `published` and can include an external post ID or link.
5. `발행 실패 기록` stores the handoff as `failed` with the readable error message you provide.
6. `전달 취소` closes the handoff as `cancelled` without sending it to the scheduler queue.

## Enabling Threads live publishing later

This section is intentionally not part of the first protected live rollout. Use it only when you are preparing a separate Threads live enablement.

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
- Treat the sensitivity note on review detail pages as a stop-and-check cue: verify attribution, legal status, official statements, casualty or health claims, and dates before approving.
- Browser scheduling still uses the same validation, attribution, and provenance checks as the CLI and API.
- `publish-due` stays dry-run by default in the browser. Live publish only runs when you explicitly select the one-run live option.
- Live publish still depends on configured channel credentials from environment variables, not YAML secrets.
- Ghost and LinkedIn handoffs are never auto-published by the browser. Threads handoffs are also manual-only whenever live credentials are missing, invalid, or not configured for that account.
- Scheduler backfill and review-page scheduling only treat Threads as live-publish-capable when the configured account can resolve a live Threads publisher. Otherwise the console keeps Threads on the manual handoff path.
- Manual handoff forms disappear after a job reaches `published`, `failed`, or `cancelled`; if a fresh post is needed later, start from a new approved draft or new handoff instead of reopening the terminal job.
- Edge Basic Auth is an access-control wrapper only. It does not replace the repository's own review-first workflow or justify public unauthenticated exposure.

## Related guides

- [Operator control-plane API guide](./operator-control-plane-api.md)
- [Finance Local MVP guide](./finance-local-operator-guide.md)
- [All-domain news guide](./all-domain-news-operator-guide.md)
