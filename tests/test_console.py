"""Focused tests for the server-rendered operator console shell."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import create_app
from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    PipelineRun,
    PipelineRunRepository,
    PipelineRunStatus,
    PipelineStage,
    SourceItem,
    SourceItemRepository,
    SourcePolicyMode,
    StageExecutionStatus,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)


def test_console_shell_root_redirects_to_canonical_landing() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/console",
        params={
            "config_dir": "/tmp/operator-config",
            "database_url": "sqlite:///tmp/operator.db",
        },
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert (
        response.headers["location"]
        == "http://testserver/console/?config_dir=%2Ftmp%2Foperator-config&database_url=sqlite%3A%2F%2F%2Ftmp%2Foperator.db"
    )


def test_console_shell_landing_page_renders_navigation_and_context() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/console/",
        params={
            "config_dir": "/tmp/operator-config",
            "database_url": "sqlite:///tmp/operator.db",
        },
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Operator Console" in response.text
    assert "Console Home" in response.text
    assert "Runs &amp; Failures" in response.text
    assert "Pending Review" in response.text
    assert "/tmp/operator-config" in response.text
    assert "sqlite:///tmp/operator.db" in response.text
    assert "Manual review required" in response.text
    assert "Dry-run publish is the browser default" in response.text


def test_console_shell_static_asset_is_served() -> None:
    client = TestClient(create_app())

    response = client.get("/console/static/console.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert "--console-bg" in response.text
    assert ".console-shell" in response.text


def test_dashboard_page_renders_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/dashboard",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "Run Dashboard" in response.text
    assert "Run dashboard is waiting for data. No pipeline runs have been recorded yet." in response.text
    assert "No recent runs are available for this operator context yet." in response.text
    assert "No technical failures are currently visible." in response.text
    assert "No policy skips are currently visible." in response.text


def test_dashboard_page_renders_recent_runs_and_failures(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        PipelineRunRepository(session).add(
            PipelineRun(
                workflow_name="run_local_finance",
                trigger_mode="manual_local",
                status=PipelineRunStatus.PARTIAL,
                started_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 3, 18, 9, 5, tzinfo=timezone.utc),
                discovered_count=4,
                saved_count=3,
                enriched_count=2,
                brief_count=2,
                draft_count=5,
                failure_count=1,
                latest_error_code="fetch_blocked",
                summary_json={
                    "policy_mode_counts": {"reusable": 3, "restricted": 1},
                    "policy_skipped_count": 1,
                    "attribution_required_count": 2,
                    "rewrite_providers": ["codex_wrapper", "fake"],
                },
            )
        )
        failed_source = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="entry-1",
                source_url="https://example.com/articles/1",
                title="Central bank update",
                policy_mode=SourcePolicyMode.RESTRICTED,
                require_attribution=True,
            )
        )
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=failed_source.id,
                source_name="Finance Feed",
                article_url="https://example.com/articles/1",
                failure_stage=PipelineStage.HTML_FETCH,
                failure_code="fetch_blocked",
                failure_message="site blocked",
                html_fetch_status=StageExecutionStatus.FAILED,
                last_stage=PipelineStage.HTML_FETCH,
                updated_at=datetime(2026, 3, 18, 9, 8, tzinfo=timezone.utc),
            )
        )
        skipped_source = SourceItemRepository(session).add(
            SourceItem(
                source_key="wikinews_feed",
                external_id="entry-2",
                source_url="https://example.com/articles/2",
                title="Election watchdog report",
                policy_mode=SourcePolicyMode.DISCOVERY_ONLY,
                require_attribution=True,
            )
        )
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=skipped_source.id,
                source_name="Wikinews",
                article_url="https://example.com/articles/2",
                policy_decision_reason="Source policy blocks full-text fetch for this item.",
                html_fetch_status=StageExecutionStatus.SKIPPED,
                article_extract_status=StageExecutionStatus.SKIPPED,
                summary_regenerate_status=StageExecutionStatus.SKIPPED,
                last_stage=PipelineStage.HTML_FETCH,
                updated_at=datetime(2026, 3, 18, 9, 9, tzinfo=timezone.utc),
            )
        )

    client = TestClient(create_app())
    response = client.get(
        "/console/dashboard",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "Run Dashboard" in response.text
    assert "run_local_finance" in response.text
    assert "Partial" in response.text
    assert "Discovered 4 / Saved 3 / Enriched 2 / Briefs 2 / Drafts 5 / Failures 1" in response.text
    assert "Restricted 1 / Reusable 3" in response.text
    assert "Policy skips 1 / Attribution required 2" in response.text
    assert "codex_wrapper, fake" in response.text
    assert "Central bank update" in response.text
    assert "site blocked" in response.text
    assert "Election watchdog report" in response.text
    assert "Source policy blocks full-text fetch for this item." in response.text


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'console.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)
