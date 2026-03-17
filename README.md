# sns-content-engine

Config-driven multi-account SNS content automation engine.

## Overview

This repository bootstraps the MVP foundation for a shared content engine that can support multiple topic-based social accounts from one system.

The initial MVP is intentionally limited to:

- X (Twitter) publishing only
- English-language operation
- Manual review before publishing
- SQLite as an acceptable local persistence option

The current milestone includes configuration loading, source ingestion, brief generation, draft generation, and a CLI-first manual review queue. It does not include real publisher integrations, scheduler execution, or review UI yet.

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

## CLI Usage

Run the CLI through the console script:

```bash
sns-engine version
sns-engine healthcheck
sns-engine discover
sns-engine ingest
sns-engine build-briefs
sns-engine generate-drafts
sns-engine review list
sns-engine review approve 42 --reviewer editor
sns-engine review reject 42 --reason "Off topic"
sns-engine review edit 42 --body "Revised draft text"
sns-engine review schedule 42 --scheduled-for 2026-03-18T09:00:00+00:00
sns-engine db init
```

Run the same commands through the module entrypoint:

```bash
python -m app.cli version
python -m app.cli healthcheck
python -m app.cli discover
python -m app.cli ingest
python -m app.cli build-briefs
python -m app.cli generate-drafts
python -m app.cli review list
python -m app.cli db init
```

The `discover` command loads configured sources, runs the RSS / sitemap / manual CSV connectors, and reports normalized source item candidates plus captured failures.

The `ingest` command runs discovery, applies canonical URL / title / fingerprint deduplication, and stores only new source items in the configured database.

The `build-briefs` command reads ingested source items, matches them to eligible accounts, resolves landing URLs, and stores channel-neutral content briefs for later draft generation.

The `generate-drafts` command reads stored content briefs, renders the configured prompt profile, and stores X-ready draft variants for manual review.

The `review` command group lists `pending_review` drafts and supports approve, reject, edit, and one-off schedule actions while recording reviewer audit history.

If you already have an older SQLite file from a previous milestone, delete it and recreate it with `sns-engine db init` before running `ingest`. The MVP does not apply automatic schema migrations yet.

Initialize the schema through the thin script wrapper:

```bash
python scripts/create_db.py
```

## Testing

Run the test suite with:

```bash
./.venv/bin/pytest
```

## Next Steps

Future milestones can add configuration loading, domain models, workflows, storage, scheduling, and publisher adapters without changing the basic package layout introduced here.
