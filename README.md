# sns-content-engine

Config-driven multi-account SNS content automation engine.

## Overview

This repository bootstraps the MVP foundation for a shared content engine that can support multiple topic-based social accounts from one system.

The initial MVP is intentionally limited to:

- X (Twitter) publishing only
- English-language operation
- Manual review before publishing
- SQLite as an acceptable local persistence option

The current milestone includes configuration loading, source ingestion, brief generation, draft generation, a CLI-first manual review queue, scheduled publish jobs, an X publisher adapter, and the minimum operations layer needed to run the MVP safely on a single server. The long-running scheduler still keeps `publish-due` in dry-run mode unless you explicitly run the one-off live command.

## Repository Structure

```text
sns-content-engine/
  app/
    api/
    config/
    connectors/
      publishers/
      sources/
    domain/
    scheduler/
    services/
    storage/
    workflows/
    cli.py
  config/
  data/
  tests/
  .env.example
  pyproject.toml
  README.md
```

## Local Setup

1. Create a virtual environment with Python 3.12 or 3.13.
2. Install the package and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

3. Optional: enable real OpenAI draft generation. If `OPENAI_API_KEY` is not set, `generate-drafts` uses the built-in fake provider for safe local workflows.

```bash
export OPENAI_API_KEY="your_api_key_here"
export OPENAI_MODEL="gpt-5.4-mini"
export OPENAI_REASONING_EFFORT="none"
export OPENAI_TIMEOUT_SECONDS="30"
```

## CLI Usage

Run the CLI through the console script:

```bash
sns-engine version
sns-engine healthcheck --config-dir config
sns-engine discover
sns-engine ingest
sns-engine build-briefs
sns-engine generate-drafts
sns-engine run-local
sns-engine history runs
sns-engine history failures
sns-engine review list
sns-engine review approve 42 --reviewer editor
sns-engine review reject 42 --reason "Off topic"
sns-engine review edit 42 --body "Revised draft text"
sns-engine review schedule 42 --scheduled-for 2026-03-18T09:00:00+00:00
sns-engine scheduler discover
sns-engine scheduler backfill
sns-engine scheduler publish-due
sns-engine scheduler publish-due --live
sns-engine scheduler run
sns-engine db init
```

Run the same commands through the module entrypoint:

```bash
python -m app.cli version
python -m app.cli healthcheck --config-dir config
python -m app.cli discover
python -m app.cli ingest
python -m app.cli build-briefs
python -m app.cli generate-drafts
python -m app.cli run-local
python -m app.cli history runs
python -m app.cli history failures
python -m app.cli review list
python -m app.cli scheduler backfill
python -m app.cli scheduler publish-due
python -m app.cli scheduler run
python -m app.cli db init
```

The `discover` command loads configured sources, runs the RSS / sitemap / manual CSV connectors, and reports normalized source item candidates plus captured failures.

The `ingest` command runs discovery, applies canonical URL / title / fingerprint deduplication, and stores only new source items in the configured database.

The `build-briefs` command reads ingested source items, matches them to eligible accounts, resolves landing URLs, and stores channel-neutral content briefs for later draft generation.

The `generate-drafts` command reads stored content briefs, renders the configured prompt profile, and stores X-ready draft variants for manual review. It automatically uses OpenAI when `OPENAI_API_KEY` is present; otherwise it falls back to the deterministic fake provider.

The `review` command group lists `pending_review` drafts and supports approve, reject, edit, and one-off schedule actions while recording reviewer audit history.

The `run-local` command is the new finance-local MVP entrypoint. It runs `ingest -> enrich -> build-briefs -> generate-drafts`, stores pipeline run history, and stops with drafts in `pending_review`. It never auto-approves or auto-publishes.

The `history runs` and `history failures` commands expose UI-friendly summaries from persisted `pipeline_runs` and article-enrichment failures so a future local homepage can read the same data model.

The `healthcheck` command is a strict readiness check. It validates both config loading and database schema readiness, prints key=value status lines, and exits non-zero if either check fails.

The `scheduler publish-due` command stays in safe dry-run mode by default. Pass `--live` only after configuring a channel publisher and its referenced environment variable.

Example channel config:

```yaml
channels:
  x:
    schedule:
      cron: "0 9 * * *"
    render:
      max_chars: 280
    publisher:
      credential_ref: X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS
```

Example credential bundle:

```bash
export X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS='{"access_token":"replace-with-user-access-token"}'
sns-engine scheduler publish-due --live
```

If you already have an older SQLite file from a previous milestone, delete it and recreate it with `sns-engine db init` before running `ingest`. The MVP does not apply automatic schema migrations yet.

Initialize the schema through the thin script wrapper:

```bash
python scripts/create_db.py
```

## Operations

Use the following operating sequence for local or single-server runs:

```bash
sns-engine db init --database-url sqlite:///data/sns_content_engine.db
sns-engine healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine discover --config-dir config
sns-engine ingest --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine build-briefs --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine generate-drafts --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine run-local --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine history runs --database-url sqlite:///data/sns_content_engine.db
sns-engine history failures --database-url sqlite:///data/sns_content_engine.db
sns-engine review list --database-url sqlite:///data/sns_content_engine.db
sns-engine review approve 42 --reviewer editor --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine review schedule 42 --scheduled-for 2026-03-18T09:00:00+00:00 --reviewer editor --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine scheduler publish-due --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine scheduler publish-due --config-dir config --database-url sqlite:///data/sns_content_engine.db --live
sns-engine scheduler run --config-dir config --database-url sqlite:///data/sns_content_engine.db
```

Operational notes:

- `healthcheck` is readiness only. If it reports a database failure, recreate the SQLite file or run `sns-engine db init` against a fresh database.
- Scheduler and publish operations now emit one-line `key=value` logs such as `event=workflow component=scheduler status=ok workflow=publish_due ...`, which are intended for terminal, journald, or basic log shipping.
- Dry-run is the default safety mode for `scheduler publish-due`. Use it first to confirm the due-job queue and logging behavior before a live publish.
- Live publish requires configured publisher credentials through environment variables only. Do not store credentials in YAML.
- Draft generation uses OpenAI automatically when `OPENAI_API_KEY` is set. Runtime controls are `OPENAI_MODEL` (default `gpt-5.4-mini`), `OPENAI_REASONING_EFFORT` (default `none`), and `OPENAI_TIMEOUT_SECONDS` (default `30`).
- If OpenAI draft generation is selected and fails, `generate-drafts` exits with an error instead of silently falling back to fake output.
- In server environments, prefer `DATABASE_URL` via `Environment` or `EnvironmentFile` instead of passing the DB URL on the command line.
- Retry policy is `manual_reschedule`. Failed publish jobs remain failed with `attempt_count` and `last_error` recorded. After fixing the cause, reschedule the already approved draft with `sns-engine review schedule ...` to create a new publish job.

Suggested dry-run and smoke checks:

```bash
sns-engine healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine scheduler publish-due --config-dir config --database-url sqlite:///data/sns_content_engine.db
./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_scripts.py
```

Example `systemd` unit for the long-running scheduler:

```ini
[Unit]
Description=sns-content-engine scheduler
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/sns-content-engine
Environment=DATABASE_URL=sqlite:////opt/sns-content-engine/data/sns_content_engine.db
EnvironmentFile=/opt/sns-content-engine/.env
ExecStart=/opt/sns-content-engine/.venv/bin/sns-engine scheduler run --config-dir /opt/sns-content-engine/config
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Testing

Run the test suite with:

```bash
./.venv/bin/pytest
```

## Next Steps

Future milestones can add configuration loading, domain models, workflows, storage, scheduling, and publisher adapters without changing the basic package layout introduced here.

## Finance Local MVP Notes

Use the finance-local example config under `config/examples/finance_local/` as a starting point when you want to run the new RSS -> HTML -> summary -> brief -> draft flow without hard-coding production feeds. Copy those files into a temporary config directory and edit the feed/account values locally.

Finance-local guardrails:
- RSS is used for discovery only. The pipeline fetches article HTML and regenerates summaries from extracted body text when possible.
- Readable failure reasons are stored for blocked fetches, extraction failures, and content that is too short to summarize.
- Draft generation now includes source context and explicit anti-investment-advice guidance.
- The local MVP always stops at `pending_review`; publish automation remains separate and unchanged.
