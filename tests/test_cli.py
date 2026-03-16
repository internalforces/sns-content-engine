"""Tests for the bootstrap CLI commands."""

import app.cli as cli_module
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


def test_help_command_is_available() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_main_runs_the_typer_app(monkeypatch) -> None:
    called = False

    def fake_app() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli_module, "app", fake_app)

    cli_module.main()

    assert called is True
