# sns-content-engine

Config-driven multi-account SNS content automation engine.

## Overview

This repository bootstraps the MVP foundation for a shared content engine that can support multiple topic-based social accounts from one system.

The initial MVP is intentionally limited to:

- X (Twitter) publishing only
- English-language operation
- Manual review before publishing
- SQLite as an acceptable local persistence option

The current milestone includes configuration loading, local developer entrypoints, and the MVP database layer. It does not include real publisher integrations, scheduler workflows, or review UI yet.

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
sns-engine db init
```

Run the same commands through the module entrypoint:

```bash
python -m app.cli version
python -m app.cli healthcheck
python -m app.cli discover
python -m app.cli ingest
python -m app.cli db init
```

The `discover` command loads configured sources, runs the RSS / sitemap / manual CSV connectors, and reports normalized source item candidates plus captured failures.

The `ingest` command runs discovery, applies canonical URL / title / fingerprint deduplication, and stores only new source items in the configured database.

If you already have an older SQLite file from a previous milestone, recreate it with `sns-engine db init` before running `ingest`. The MVP does not apply automatic schema migrations yet.

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
