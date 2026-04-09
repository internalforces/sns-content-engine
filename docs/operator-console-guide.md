# Operator Console Guide

## What the console is

The operator console is the browser surface for the same FastAPI app, database, and review workflow that back the CLI and operator API.

- Manual review still gates publishing.
- Browser `publish-due` stays in dry-run mode unless you explicitly opt into one live run.
- The console does not add authentication, auto-approval, or hidden publish behavior.

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
- `Review Detail`: approve, reject, edit, or schedule one draft while keeping current validation and audit behavior.
- `Publish Jobs`: queued, published, and failed jobs plus linked draft context.
- `Scheduler`: discover, backfill, and publish-due actions with dry-run-first messaging.

## Recommended local flow

1. Run `sns-engine run-local` to discover, enrich, build briefs, and generate drafts.
2. Open `Pending Review` and inspect one draft workspace.
3. Approve, reject, or edit the draft. Schedule only after approval succeeds.
4. Check `Publish Jobs` to confirm scheduled, published, or failed delivery state.
5. Use `Scheduler` for discover, backfill, and `publish-due` after confirming the current queue.

## Safety reminders

- Drafts stay in `pending_review` until an operator acts.
- Browser scheduling still uses the same validation, attribution, and provenance checks as the CLI and API.
- `publish-due` stays dry-run by default in the browser. Live publish only runs when you explicitly select the one-run live option.
- Live publish still depends on configured channel credentials from environment variables, not YAML secrets.

## Related guides

- [Operator control-plane API guide](./operator-control-plane-api.md)
- [Finance Local MVP guide](./finance-local-operator-guide.md)
- [All-domain news guide](./all-domain-news-operator-guide.md)
