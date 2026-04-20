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
