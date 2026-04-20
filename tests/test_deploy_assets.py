"""Tests for checked-in single-server deployment assets."""

from __future__ import annotations

from pathlib import Path
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_dependencies_include_uvicorn() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.startswith("uvicorn") for dependency in dependencies)


def test_systemd_units_use_shared_env_and_expected_commands() -> None:
    web_unit = (PROJECT_ROOT / "deploy/systemd/sns-web.service").read_text(encoding="utf-8")
    scheduler_unit = (PROJECT_ROOT / "deploy/systemd/sns-scheduler.service").read_text(encoding="utf-8")

    assert "User=sns-engine" in web_unit
    assert "Group=sns-engine" in web_unit
    assert "EnvironmentFile=/opt/sns-content-engine/.env" in web_unit
    assert (
        "ExecStart=/opt/sns-content-engine/.venv/bin/uvicorn "
        "app.api.app:app --host 127.0.0.1 --port 8000"
    ) in web_unit

    assert "User=sns-engine" in scheduler_unit
    assert "Group=sns-engine" in scheduler_unit
    assert "EnvironmentFile=/opt/sns-content-engine/.env" in scheduler_unit
    assert (
        "ExecStart=/opt/sns-content-engine/.venv/bin/sns-engine "
        "scheduler run --config-dir /opt/sns-content-engine/config"
    ) in scheduler_unit


def test_production_env_template_matches_single_server_defaults() -> None:
    env_template = (PROJECT_ROOT / ".env.production.example").read_text(encoding="utf-8")

    assert "APP_ENV=production" in env_template
    assert "LOG_LEVEL=INFO" in env_template
    assert "DATABASE_URL=sqlite:////opt/sns-content-engine/data/sns_content_engine.db" in env_template
    assert "DEFAULT_TIMEZONE=Asia/Seoul" in env_template


def test_caddy_reverse_proxy_assets_pin_the_edge_protection_baseline() -> None:
    caddyfile = (PROJECT_ROOT / "deploy/caddy/sns.gilgop.cloud.Caddyfile").read_text(encoding="utf-8")
    env_template = (PROJECT_ROOT / "deploy/caddy/sns.gilgop.cloud.env.example").read_text(
        encoding="utf-8"
    )

    assert "sns.gilgop.cloud" in caddyfile
    assert "@health path /health" in caddyfile
    assert "basic_auth" in caddyfile
    assert "{$SNS_EDGE_BASIC_AUTH_USER}" in caddyfile
    assert "{$SNS_EDGE_BASIC_AUTH_HASH}" in caddyfile
    assert "reverse_proxy 127.0.0.1:8000" in caddyfile

    assert "SNS_EDGE_BASIC_AUTH_USER=replace-with-console-user" in env_template  # pragma: allowlist secret
    assert "SNS_EDGE_BASIC_AUTH_HASH=" in env_template


def test_operator_docs_keep_remote_access_on_the_edge_baseline() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    console_guide = (PROJECT_ROOT / "docs/operator-console-guide.md").read_text(encoding="utf-8")
    control_plane_guide = (PROJECT_ROOT / "docs/operator-control-plane-api.md").read_text(
        encoding="utf-8"
    )

    assert "keep the shared FastAPI app on `127.0.0.1:8000`" in readme
    assert "Caddy plus Basic Auth edge layer" in readme
    assert "do not expose the app directly on a public `0.0.0.0` bind" in readme

    assert "https://sns.gilgop.cloud/console/" in console_guide
    assert "Do not rebind `uvicorn` to `0.0.0.0`" in console_guide
    assert "protects every other route, including `/console`, `/reviews/...`, `/scheduler/...`" in (
        console_guide
    )

    assert "keep that app bound to `127.0.0.1:8000`" in control_plane_guide
    assert "protects every other route with Basic Auth" in control_plane_guide
    assert '"https://sns.gilgop.cloud/reviews/pending?' in control_plane_guide


def test_single_server_runbook_assets_cover_smoke_checks_and_recovery() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    deployment_guide = (PROJECT_ROOT / "docs/single-server-deployment-guide.md").read_text(
        encoding="utf-8"
    )
    smoke_script = (PROJECT_ROOT / "scripts/single_server_smoke_check.sh").read_text(
        encoding="utf-8"
    )

    assert "scripts/single_server_smoke_check.sh" in readme
    assert "SNS_SMOKE_EDGE_USER=operator" in readme
    assert "backup and rollback order lives in the single-server deployment guide" in readme

    assert "scripts/single_server_smoke_check.sh" in deployment_guide
    assert "Backup baseline for SQLite-first rollout" in deployment_guide
    assert "Non-destructive rollout order" in deployment_guide
    assert "Rollback order" in deployment_guide

    assert "sns-web.service" in smoke_script
    assert "sns-scheduler.service" in smoke_script
    assert "caddy.service" in smoke_script
    assert "executor mode: fake dry-run (no state changes)" in smoke_script
    assert "SNS_SMOKE_EDGE_USER" in smoke_script
    assert "SNS_SMOKE_EDGE_PASSWORD" in smoke_script
