"""Tests for the FastAPI read-only operator routes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from fastapi.testclient import TestClient

from app.api import create_app
from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    PipelineRun,
    PipelineRunRepository,
    PipelineRunStatus,
    SourceItem,
    SourceItemRepository,
    SourcePolicyMode,
    StageExecutionStatus,
    PipelineStage,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)


def test_health_endpoint_returns_readiness_json(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    database_url = f"sqlite+pysqlite:///{tmp_path / 'api-health.db'}"
    engine = create_database_engine(database_url)
    create_all_tables(engine)
    engine.dispose()
    client = TestClient(create_app())

    response = client.get(
        "/health",
        params={
            "config_dir": str(tmp_path),
            "database_url": database_url,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["failed_check_count"] == 0
    assert [check["name"] for check in payload["checks"]] == ["config", "database"]


def test_runs_endpoint_returns_readable_history_rows(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        PipelineRunRepository(session).add(
            PipelineRun(
                workflow_name="run_local_finance",
                trigger_mode="manual_local",
                status=PipelineRunStatus.SUCCEEDED,
                started_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 3, 18, 9, 5, tzinfo=timezone.utc),
                discovered_count=4,
                saved_count=3,
                enriched_count=2,
                brief_count=2,
                draft_count=5,
                failure_count=0,
                summary_json={
                    "policy_mode_counts": {"reusable": 3, "restricted": 1},
                    "policy_skipped_count": 1,
                    "attribution_required_count": 2,
                    "rewrite_providers": ["codex_wrapper", "fake"],
                },
            )
        )

    client = TestClient(create_app())
    response = client.get(
        "/runs",
        params={
            "database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["workflow_name"] == "run_local_finance"
    assert payload["runs"][0]["policy_mode_counts"] == {"restricted": 1, "reusable": 3}
    assert payload["runs"][0]["rewrite_providers"] == ["codex_wrapper", "fake"]


def test_failures_endpoint_returns_failures_and_policy_skips(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
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
            )
        )

    client = TestClient(create_app())
    response = client.get(
        "/failures",
        params={
            "database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["failures"]) == 1
    assert payload["failures"][0]["failure_code"] == "fetch_blocked"
    assert payload["failures"][0]["failure_stage"] == "html_fetch"
    assert len(payload["policy_skips"]) == 1
    assert payload["policy_skips"][0]["skipped_stage"] == "html_fetch"
    assert payload["policy_skips"][0]["source_policy_mode"] == "discovery_only"


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'api.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _write_minimal_project_config(path: Path) -> None:
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


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
