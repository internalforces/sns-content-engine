# sns-content-engine

Config-driven multi-account SNS content automation engine.

## Overview

This repository bootstraps the MVP foundation for a shared content engine that can support multiple topic-based social accounts from one system.

The initial MVP is intentionally limited to:

- X live publishing plus operator-recorded manual LinkedIn/Threads handoff tracking
- English-language operation
- Manual review before publishing
- SQLite as an acceptable local persistence option

The current milestone includes configuration loading, source ingestion, brief generation, multichannel draft generation, a CLI-first manual review queue, scheduled publish jobs for X, manual publish handoff tracking for LinkedIn and Threads, a live X publisher adapter, and the minimum operations layer needed to run the MVP safely on a single server. The long-running scheduler still keeps `publish-due` in dry-run mode unless you explicitly run the one-off live command.

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

3. Optional: enable live draft generation. If `<config-dir>/providers.yaml` is present, `generate-drafts` and `run-local` use its `draft_generate` route chain at runtime. If the file is absent, draft generation falls back to environment-based auto-detection in this order: OpenAI, Anthropic, then Codex-Wrapper. If no supported provider credentials are present, local workflows use the built-in fake provider for safety.

```bash
export OPENAI_API_KEY="your_api_key_here"
export OPENAI_MODEL="gpt-5.4-mini"
export OPENAI_REASONING_EFFORT="none"
export OPENAI_TIMEOUT_SECONDS="30"
```

For Codex-Wrapper routes, set `CODEX_WRAPPER_API_KEY`, `CODEX_WRAPPER_BASE_URL`, and optionally `CODEX_WRAPPER_MODEL` instead of the OpenAI variables above.

## Example Config Sets

- `config/` remains the active default configuration used by the CLI unless you pass a different `--config-dir`. It now defines the built-in AI/SEO operator accounts across `x`, `linkedin`, and `threads`, with live publishing configured only for `x` and source-linked sharing as the default link strategy instead of routing to a house destination site.
- `config/examples/finance_local/` is a finance-local sample for the current review-first MVP flow.
- `config/examples/all_domain_news/` is a sample-only all-domain setup showing reusable public sources, reusable newsroom or IR sources, attribution-friendly Wikinews-style settings, and a discovery-only GDELT sample kept in its own source set.

These example directories are not production defaults. Copy them into a separate working config directory and replace the sample URLs with your own operator-approved sources before real runs.
`sns-engine healthcheck` now treats bundled `config/examples/...` directories and unresolved `example.com` / `example.org` / `example.net` URLs as not operator-ready, so copy and edit the sample files before using them for live workflows.
Keep the bundled GDELT example in a dedicated discovery-only source set. Policy-aware enrichment skips are now recorded when later steps block full-text fetch or rewrite, so the sample is intended for recent-news discovery rather than direct full-text reuse.

## Operator Guides

- [Single-server deployment guide](docs/single-server-deployment-guide.md) for the recommended `/opt/sns-content-engine` layout, env handling, SQLite-first database choice, and the split between the loopback-only web process and the scheduler service before a protected `sns.gilgop.cloud` rollout.
- [Operator console guide](docs/operator-console-guide.md) for starting the FastAPI-served browser console and using dashboard, review, publish-job, and scheduler pages safely.
- [Finance Local MVP guide](docs/finance-local-operator-guide.md) for the original review-first finance workflow.
- [All-domain news guide](docs/all-domain-news-operator-guide.md) for source-policy categories, intentional enrichment skips, Codex-Wrapper usage, and manual-review expectations.
- [Operator control-plane API guide](docs/operator-control-plane-api.md) for review detail, manual publish handoff actions, publish-job visibility, and scheduler-safe HTTP actions.

The console follows the same safety model as the CLI and API: drafts still require manual review, browser `publish-due` stays dry-run unless you explicitly opt into one live run, and LinkedIn or Threads publishing remains an operator-driven manual upload flow with explicit outcome recording.

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

The `discover` command loads configured sources, runs the RSS / sitemap / manual CSV / GDELT connectors, and reports normalized source item candidates plus captured failures.

The `ingest` command runs discovery, applies canonical URL / title / fingerprint deduplication, and stores only new source items in the configured database.

The `build-briefs` command reads ingested source items, matches them to eligible accounts, resolves landing URLs, and stores channel-neutral content briefs for later draft generation.

The `generate-drafts` command reads stored content briefs, renders the configured prompt profile, and stores channel-specific draft variants for the configured `x`, `linkedin`, and `threads` accounts. When `<config-dir>/providers.yaml` is present, it uses the configured `draft_generate` route chain and model overrides at runtime. When the file is absent, it falls back to environment-based auto-detection and only uses the deterministic fake provider when no supported live-provider credentials are configured.

The `review` command group lists `pending_review` drafts and supports approve, reject, edit, and one-off schedule actions while recording reviewer audit history. Approving LinkedIn or Threads drafts creates an explicit manual publish handoff job automatically; X keeps the existing schedule-driven publish flow.

The `run-local` command is the new finance-local MVP entrypoint. It runs `ingest -> enrich -> build-briefs -> generate-drafts`, stores pipeline run history, uses the same draft-provider resolution path as `generate-drafts`, and stops with drafts in `pending_review`. It never auto-approves or auto-publishes.

The `history runs` and `history failures` commands expose operator-readable summaries from persisted `pipeline_runs` and article-enrichment history while still matching the future UI/API data model. Run history includes policy-aware counts and rewrite-provider names when available, and failure history prints both ordinary `type=failure` rows and intentional `type=policy_skip` rows with source-policy metadata.

The `healthcheck` command is a strict readiness check. It validates config loading, operator-readiness signals for bundled sample configs and placeholder URLs, and database schema readiness; it prints key=value status lines and exits non-zero if any required check fails.

The `scheduler publish-due` command stays in safe dry-run mode by default. Pass `--live` only after configuring a channel publisher and its referenced environment variable. Only scheduled jobs enter the due queue, so manual LinkedIn and Threads handoffs are intentionally excluded until an operator records their outcome through the console or API.

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

If you already have an older SQLite file from a previous milestone, run `sns-engine db upgrade --database-url ...` before `ingest` or `run-local`. Fresh databases should still start with `sns-engine db init`.

Initialize the schema through the thin script wrapper:

```bash
python scripts/create_db.py
python scripts/create_db.py --database-url sqlite:///data/sns_content_engine.db --upgrade
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

- `healthcheck` is readiness only. If it reports an outdated SQLite schema, run `sns-engine db upgrade`. Use `sns-engine db init` only for fresh databases.
- `healthcheck` also fails when `--config-dir` points at bundled `config/examples/...` content or when placeholder `example.com` / `example.org` / `example.net` URLs are still present. Copy the sample config to a separate directory and replace those URLs before real runs.
- Scheduler and publish operations now emit one-line `key=value` logs such as `event=workflow component=scheduler status=ok workflow=publish_due ...`, which are intended for terminal, journald, or basic log shipping.
- Dry-run is the default safety mode for `scheduler publish-due`. Use it first to confirm the due-job queue and logging behavior before a live publish.
- Live publish requires configured publisher credentials through environment variables only. Do not store credentials in YAML.
- Draft generation checks `<config-dir>/providers.yaml` first when present. Without it, environment-based auto-detection tries OpenAI, Anthropic, then Codex-Wrapper; if no supported credentials are configured, local workflows fall back to the deterministic fake provider.
- Provider credentials still come from environment variables only. `providers.yaml` selects route order and optional model overrides; it does not store secrets.
- If a live draft provider is selected and fails, `generate-drafts` exits with an error instead of silently falling back to fake output.
- In server environments, prefer `DATABASE_URL` via `Environment` or `EnvironmentFile` instead of passing the DB URL on the command line.
- Retry policy is `manual_reschedule`. Failed publish jobs remain failed with `attempt_count` and `last_error` recorded. After fixing the cause, reschedule the already approved draft with `sns-engine review schedule ...` to create a new publish job.
- Approving a LinkedIn or Threads draft creates a `scheduled_for = null` publish job that represents a manual upload handoff. Complete, fail, or cancel that handoff from the publish-job detail page in the console or through the `/publish-jobs/{id}/manual/*` API routes.
- `sns-engine review schedule ...` remains the scheduled-publish path for channels with a live publisher. It is intentionally rejected for manual-only channels so the scheduler queue stays limited to due X jobs.

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
