"""Tests for the bootstrap CLI commands."""

from pathlib import Path

import app.cli as cli_module
from sqlalchemy import inspect
from sqlalchemy.engine import create_engine
from typer.testing import CliRunner

from app import __version__
from app.cli import app

runner = CliRunner()


def test_version_command_outputs_application_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"sns-content-engine {__version__}"


def test_healthcheck_command_reports_ok_status() -> None:
    result = runner.invoke(app, ["healthcheck"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "status=ok"


def test_db_init_command_bootstraps_the_database(tmp_path: Path) -> None:
    database_path = tmp_path / "cli.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    result = runner.invoke(app, ["db", "init", "--database-url", database_url])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"database initialized: {database_url}"

    engine = create_engine(database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "content_briefs",
            "draft_variants",
            "publish_jobs",
            "publish_logs",
            "source_items",
        }
    finally:
        engine.dispose()


def test_help_command_is_available() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "db" in result.stdout


def test_main_runs_the_typer_app(monkeypatch) -> None:
    called = False

    def fake_app() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli_module, "app", fake_app)

    cli_module.main()

    assert called is True
