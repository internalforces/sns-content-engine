"""Tests for operational helper utilities."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from sqlalchemy.engine import make_url

from app.operations import _describe_database_target, run_healthcheck
from app.storage import create_all_tables, create_database_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_describe_database_target_redacts_credentials_for_non_sqlite_urls() -> None:
    backend, target = _describe_database_target(
        make_url("postgresql://ops-user:super-secret@db.example.com:5432/appdb")
    )

    assert backend == "postgresql"
    assert target == "db.example.com:5432/appdb"
    assert "super-secret" not in target
    assert "ops-user" not in target


def test_run_healthcheck_flags_bundled_sample_config_directory(tmp_path: Path) -> None:
    database_url = _initialize_database(tmp_path / "sample-config.db")

    result = run_healthcheck(
        config_dir=PROJECT_ROOT / "config" / "examples" / "all_domain_news",
        database_url=database_url,
    )

    assert result.status == "failed"
    readiness_check = next(check for check in result.checks if check.name == "config_readiness")
    assert readiness_check.status == "failed"
    assert "bundled sample config directory" in readiness_check.message
    assert "config/examples/all_domain_news" in readiness_check.message
    assert "placeholder URLs detected" in readiness_check.message


def test_run_healthcheck_flags_placeholder_urls_in_working_config(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path, source_url="https://example.com/feed.xml")
    database_url = _initialize_database(tmp_path / "placeholder-config.db")

    result = run_healthcheck(config_dir=tmp_path, database_url=database_url)

    assert result.status == "failed"
    readiness_check = next(check for check in result.checks if check.name == "config_readiness")
    assert readiness_check.status == "failed"
    assert "placeholder URLs detected" in readiness_check.message
    assert "sources.ai_tools_rss.url (example.com)" in readiness_check.message


def _initialize_database(path: Path) -> str:
    database_url = f"sqlite+pysqlite:///{path}"
    engine = create_database_engine(database_url)
    try:
        create_all_tables(engine)
    finally:
        engine.dispose()
    return database_url


def _write_minimal_project_config(
    path: Path,
    *,
    source_url: str = "https://gilgop.cloud/feed.xml",
) -> None:
    _write_file(
        path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: "system"
            user_template: "user"
        """,
    )
    _write_file(
        path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: {source_url}

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """.format(source_url=source_url),
    )


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
