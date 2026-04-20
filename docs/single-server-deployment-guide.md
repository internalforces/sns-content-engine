# Single-Server Deployment Guide

## Goal

Run the current review-first SNS content engine on one protected personal server at `sns.gilgop.cloud` without changing its workflow semantics.

This guide standardizes the current deployment shape for:
- one FastAPI web process serving `/health` and `/console/...`
- one separate scheduler process running `sns-engine scheduler run`
- one shared environment file and one shared config directory
- one local database, with SQLite as the default first-rollout choice

It now provides checked-in `systemd` units plus a production-oriented env template, but reverse-proxy config files and a backup and rollback runbook still remain follow-up tasks in the deployment-readiness roadmap.

## Safety model

Keep the existing operator guardrails intact:
- Manual review still gates publishing.
- `sns-engine scheduler publish-due` stays dry-run by default. Use `--live` only for an intentional one-off live publish run.
- Publisher credentials, API keys, and database URLs stay in environment variables or an `EnvironmentFile`, never in checked-in YAML.
- The current browser console does not add in-app authentication. Do not expose it directly to the public internet.

## Recommended server layout

Use one stable application root such as `/opt/sns-content-engine`:

```text
/opt/sns-content-engine/
  app/
  config/
  data/
    sns_content_engine.db
  docs/
  scripts/
  .env
  .venv/
  README.md
```

Conventions:
- Keep the Git checkout, virtualenv, config, and SQLite file under the same operator-owned root.
- Keep `config/` as the active runtime config only after replacing placeholder URLs and sample values with operator-approved ones.
- Keep the database path stable so both the web process and the scheduler point at the same state.
- Prefer journald or another process-level log collector instead of ad hoc log files in the repo.

## Environment conventions

The CLI and FastAPI app both call the lightweight project `.env` loader on startup, so a repo-local `.env` file works for local and single-server operation. On the server, prefer the same values through `EnvironmentFile=/opt/sns-content-engine/.env` so the web service and scheduler share one source of truth.

Recommended baseline variables:

```dotenv
APP_ENV=production
LOG_LEVEL=INFO
DATABASE_URL=sqlite:////opt/sns-content-engine/data/sns_content_engine.db
DEFAULT_TIMEZONE=Asia/Seoul
OPENAI_API_KEY=replace-me
OPENAI_MODEL=gpt-5.4-mini
OPENAI_REASONING_EFFORT=none
OPENAI_TIMEOUT_SECONDS=30
```

Additional rules:
- Keep provider credentials and publisher credential bundles in the environment only.
- Keep `publisher.credential_ref` values in `accounts.yaml`, but store the referenced JSON payload in the environment variable named by that ref.
- Use one explicit config directory for both processes, for example `/opt/sns-content-engine/config`.
- Do not run the server from bundled `config/examples/...` directories. `sns-engine healthcheck` intentionally fails when sample configs or placeholder `example.*` URLs are still present.

## Database choice

For the first protected personal-server rollout, stay on SQLite unless you have a clear operational reason to switch.

Why SQLite is the default here:
- it is already the repository default via `DATABASE_URL=sqlite:///data/sns_content_engine.db`
- the current workflow is single-operator and review-first
- it keeps initial deployment simpler while the web console and scheduler remain on one machine

Stay with SQLite when:
- one operator is running the system
- traffic is low
- you want the smallest operational footprint

Plan a Postgres move later when:
- SQLite file locking becomes a real operational problem
- you want managed backups or existing Postgres operations
- you intentionally expand beyond the current one-server shape

Whichever backend you choose, keep one shared `DATABASE_URL` for both the web process and the scheduler.

## Bring-up checklist

1. Clone the repository onto the server and create a Python 3.12 or 3.13 virtual environment.
2. Install the package into the server virtual environment. Use development extras only when you also want the local test tooling on the server:

```bash
python -m pip install -e .
```

3. Prepare an operator-owned config directory under `/opt/sns-content-engine/config`.
   Copy from `config/` or a sample directory only as a starting point, then replace placeholder URLs and sample account details.
4. Create `/opt/sns-content-engine/.env` from `.env.production.example` and fill only the values you actually use.
5. Initialize a fresh database or upgrade an older one:

```bash
./.venv/bin/sns-engine db init
./.venv/bin/sns-engine db upgrade
```

Use `db init` only for a brand-new database. Use `db upgrade` when reusing an older SQLite file.
6. Run a readiness check before starting long-running processes:

```bash
./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config
```

## Runtime split

Keep the web console and scheduler as separate long-running processes.

Recommended web command:

```bash
./.venv/bin/uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

Recommended scheduler command:

```bash
./.venv/bin/sns-engine scheduler run --config-dir /opt/sns-content-engine/config
```

Why this shape matters:
- the web process serves `/health` and the operator console
- the scheduler keeps background discover, backfill, and publish-due execution separate
- both processes can share one `.env`, one config directory, and one database URL without merging responsibilities

## Checked-in service units

The repository now includes one-server `systemd` units under `deploy/systemd/`:

- `deploy/systemd/sns-web.service`
- `deploy/systemd/sns-scheduler.service`

They assume:
- a working tree rooted at `/opt/sns-content-engine`
- one shared environment file at `/opt/sns-content-engine/.env`
- one shared runtime config at `/opt/sns-content-engine/config`
- a dedicated service account named `sns-engine`

If you use a different service account, update `User=` and `Group=` before enabling the units.

Suggested install sequence:

```bash
sudo cp deploy/systemd/sns-web.service /etc/systemd/system/
sudo cp deploy/systemd/sns-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sns-web.service sns-scheduler.service
```

## Remote access requirements for `sns.gilgop.cloud`

Treat the current app as private-by-default.

Required deployment posture:
- terminate HTTPS at an edge proxy in front of the FastAPI app
- keep the app itself bound to loopback only, such as `127.0.0.1:8000`
- require an access-control layer before requests reach `/console`

Acceptable edge protection examples:
- HTTP basic auth at the reverse proxy
- an IP allowlist
- a VPN-only route
- a zero-trust access gateway

Do not:
- bind the app directly to `0.0.0.0` and expose it without protection
- treat the current console as safe for public unauthenticated access
- move credentials into checked-in config files just to simplify remote startup

Concrete reverse-proxy assets for `sns.gilgop.cloud` are a later deployment-readiness task. Until those land, keep remote exposure private and operator-controlled.

## First smoke checks

After the web process and scheduler are running, verify the minimum safe surface:

```bash
./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config
curl -fsS "http://127.0.0.1:8000/health?config_dir=/opt/sns-content-engine/config"
./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config
```

What to confirm:
- `healthcheck` passes config, config-readiness, and database checks
- `/health` returns successfully on the loopback-only app port
- `scheduler publish-due` stays in dry-run mode unless you deliberately add `--live`
- the console opens with an explicit operator context such as `/console/?config_dir=/opt/sns-content-engine/config`

## What is intentionally deferred

This guide defines the runtime conventions for a single protected server, but these assets still belong to later tasks:
- checked-in reverse-proxy config for `sns.gilgop.cloud`
- backup, restore, and rollback procedures
- a final production smoke checklist that includes service-manager status checks
