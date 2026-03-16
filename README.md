# sns-content-engine

Config-driven multi-account SNS content automation engine.

## Overview

This repository bootstraps the MVP foundation for a shared content engine that can support multiple topic-based social accounts from one system.

The initial MVP is intentionally limited to:

- X (Twitter) publishing only
- English-language operation
- Manual review before publishing
- SQLite as an acceptable local persistence option

This milestone only establishes the project structure and local developer entrypoints. It does not include real integrations, business workflows, or database models yet.

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
```

Run the same commands through the module entrypoint:

```bash
python -m app.cli version
python -m app.cli healthcheck
```

## Testing

Run the test suite with:

```bash
pytest
```

## Next Steps

Future milestones can add configuration loading, domain models, workflows, storage, scheduling, and publisher adapters without changing the basic package layout introduced here.
