"""Tests for checked-in single-server deployment assets."""

from __future__ import annotations

import tomllib
from pathlib import Path

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
        "app.api.app:app --host 127.0.0.1 --port 8001"
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


def test_caddy_reverse_proxy_assets_allow_public_console() -> None:
    caddyfile = (PROJECT_ROOT / "deploy/caddy/sns.gilgop.cloud.Caddyfile").read_text(encoding="utf-8")

    assert "sns.gilgop.cloud" in caddyfile
    assert "basic_auth" not in caddyfile
    assert "@root path /" in caddyfile
    assert "rewrite @root /console/" in caddyfile
    assert "reverse_proxy 127.0.0.1:8001" in caddyfile


def test_operator_docs_keep_remote_access_on_the_edge_baseline() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    deployment_guide = (PROJECT_ROOT / "docs/single-server-deployment-guide.md").read_text(
        encoding="utf-8"
    )

    assert "FastAPI 앱을 `127.0.0.1:8001`에 유지" in readme
    assert "Caddy HTTPS 프록시를 통해 로그인 없이 제공합니다" in readme
    assert "공개 `0.0.0.0` 주소로 직접 노출하지 않습니다" in readme

    assert "https://sns.gilgop.cloud/console/" in deployment_guide
    assert "proxies only to `127.0.0.1:8001`" in deployment_guide
    assert "serves `/health`, `/console`, and the JSON review or scheduler APIs without authentication" in deployment_guide


def test_single_server_runbook_assets_cover_smoke_checks_and_recovery() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    deployment_guide = (PROJECT_ROOT / "docs/single-server-deployment-guide.md").read_text(
        encoding="utf-8"
    )
    smoke_script = (PROJECT_ROOT / "scripts/single_server_smoke_check.sh").read_text(
        encoding="utf-8"
    )

    assert "scripts/single_server_smoke_check.sh" in readme
    assert "SNS_SMOKE_EDGE_USER" not in readme
    assert "백업과 롤백 순서" in readme

    assert "scripts/single_server_smoke_check.sh" in deployment_guide
    assert "Backup baseline for SQLite-first rollout" in deployment_guide
    assert "Non-destructive rollout order" in deployment_guide
    assert "Rollback order" in deployment_guide

    assert "sns-web.service" in smoke_script
    assert "sns-scheduler.service" in smoke_script
    assert "caddy.service" in smoke_script
    assert "executor mode: fake dry-run (no state changes)" in smoke_script
    assert "smoke_check=console_public" in smoke_script
    assert "SNS_SMOKE_EDGE_USER" not in smoke_script
