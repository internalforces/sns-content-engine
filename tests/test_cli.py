"""Tests for the bootstrap CLI commands."""

from pathlib import Path

import app.cli as cli_module
from sqlalchemy import inspect
from sqlalchemy.engine import create_engine
from typer.testing import CliRunner

from app import __version__
from app.cli import app
from app.domain import SourceDiscoveryFailure, SourceItemCandidate
from app.workflows import DiscoverSourcesResult

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


def test_discover_command_reports_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "discover_sources",
        lambda _config_dir: DiscoverSourcesResult(
            items=(
                SourceItemCandidate(
                    source_id="ai_tools_rss",
                    external_id="entry-1",
                    source_url="https://example.com/posts/1",
                    title="First AI Tool",
                ),
                SourceItemCandidate(
                    source_id="ai_tools_manual",
                    external_id="csv-1",
                    source_url="https://example.com/manual/1",
                    title="Manual Discovery",
                ),
            ),
            failures=(),
            processed_sources=("ai_tools_manual", "ai_tools_rss"),
        ),
    )

    result = runner.invoke(app, ["discover"])

    assert result.exit_code == 0
    assert "discovered 2 source item candidates from 2 sources" in result.stdout
    assert "ai_tools_manual: 1" in result.stdout
    assert "ai_tools_rss: 1" in result.stdout


def test_discover_command_exits_nonzero_when_failures_are_present(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "discover_sources",
        lambda _config_dir: DiscoverSourcesResult(
            items=(),
            failures=(
                SourceDiscoveryFailure(
                    source_id="ai_tools_sitemap",
                    stage="fetch",
                    message="timeout",
                ),
            ),
            processed_sources=("ai_tools_sitemap",),
        ),
    )

    result = runner.invoke(app, ["discover"])

    assert result.exit_code == 1
    assert "failures:" in result.output
    assert "ai_tools_sitemap [fetch] timeout" in result.output


def test_help_command_is_available() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "db" in result.stdout
    assert "discover" in result.stdout


def test_main_runs_the_typer_app(monkeypatch) -> None:
    called = False

    def fake_app() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli_module, "app", fake_app)

    cli_module.main()

    assert called is True
