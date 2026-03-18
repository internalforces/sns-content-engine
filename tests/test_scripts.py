"""Tests for standalone project scripts."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from sqlalchemy import inspect
from sqlalchemy.engine import create_engine

from app.storage import (
    ContentBrief,
    ContentBriefRepository,
    DraftVariant,
    DraftVariantRepository,
    DraftVariantState,
    PublishJob,
    PublishJobRepository,
    SourceItem,
    SourceItemRepository,
    create_database_engine,
    create_session_factory,
    session_scope,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_create_db_script_bootstraps_the_database(tmp_path: Path) -> None:
    database_path = tmp_path / "script.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts/create_db.py"), "--database-url", database_url],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == f"database initialized: {database_url}"

    engine = create_engine(database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "article_enrichments",
            "content_briefs",
            "draft_variants",
            "pipeline_runs",
            "pipeline_run_stages",
            "publish_jobs",
            "publish_logs",
            "review_actions",
            "source_item_recent_fingerprint_claims",
            "source_items",
        }
    finally:
        engine.dispose()


def test_operations_smoke_cli_flow(tmp_path: Path) -> None:
    config_dir = _write_smoke_project_config(tmp_path)
    database_url = f"sqlite+pysqlite:///{tmp_path / 'operations-smoke.db'}"

    init_result = subprocess.run(
        [sys.executable, "-m", "app.cli", "db", "init", "--database-url", database_url],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert init_result.returncode == 0
    assert init_result.stdout.strip() == f"database initialized: {database_url}"

    healthcheck_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "healthcheck",
            "--config-dir",
            str(config_dir),
            "--database-url",
            database_url,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert healthcheck_result.returncode == 0
    assert "event=healthcheck component=cli status=ok check_count=2 failed_check_count=0" in (
        healthcheck_result.stdout
    )

    _seed_due_publish_job(database_url)

    publish_due_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "scheduler",
            "publish-due",
            "--config-dir",
            str(config_dir),
            "--database-url",
            database_url,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert publish_due_result.returncode == 0
    assert "processed due jobs: 1 (dry_run=1, failed=0, skipped=0)" in publish_due_result.stdout
    assert "executor mode: fake dry-run (no state changes)" in publish_due_result.stdout
    assert "event=publish_job component=publisher status=dry_run workflow=publish_due" in (
        publish_due_result.stderr
    )


def _seed_due_publish_job(database_url: str) -> None:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_scope(session_factory) as session:
            source_item = SourceItemRepository(session).add(
                SourceItem(
                    source_key="ai_tools_rss",
                    external_id="operations-smoke-entry",
                    source_url="https://example.com/operations-smoke",
                    title="Operations smoke test item",
                    summary="Smoke summary",
                )
            )
            brief = ContentBriefRepository(session).add(
                ContentBrief(
                    source_item_id=source_item.id,
                    account_key="ai_tools_daily",
                    title="Operations smoke brief",
                    summary="Smoke summary",
                    key_points=["Smoke point"],
                    landing_url="https://gilgop.cloud/ai-tools",
                    tags=["ai"],
                    angle="practical_how_to",
                    language="en",
                )
            )
            draft = DraftVariantRepository(session).add(
                DraftVariant(
                    content_brief=brief,
                    channel="x",
                    variant_index=0,
                    body="Smoke dry-run post https://gilgop.cloud/ai-tools",
                )
            )
            DraftVariantRepository(session).transition_state(
                draft,
                DraftVariantState.APPROVED,
                reviewed_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            )
            PublishJobRepository(session).add(
                PublishJob(
                    draft_variant=draft,
                    channel="x",
                    scheduled_for=datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc),
                )
            )
    finally:
        engine.dispose()


def _write_smoke_project_config(path: Path) -> Path:
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
            url: https://example.com/feed.xml

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """,
    )
    return path


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
