"""Tests for readable run/failure history queries."""

from __future__ import annotations

from datetime import datetime, timezone

from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    PipelineRun,
    PipelineRunRepository,
    PipelineRunStage,
    PipelineRunStageRepository,
    PipelineRunStatus,
    PipelineStage,
    SourceItem,
    SourceItemRepository,
    StageExecutionStatus,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.workflows import list_pipeline_failures, list_pipeline_runs


def test_list_pipeline_runs_returns_recent_rows(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        run = PipelineRunRepository(session).add(
            PipelineRun(
                workflow_name="run_local_finance",
                status=PipelineRunStatus.PARTIAL,
                started_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 3, 18, 9, 5, tzinfo=timezone.utc),
                discovered_count=4,
                saved_count=2,
                enriched_count=1,
                brief_count=1,
                draft_count=3,
                failure_count=1,
            )
        )
        PipelineRunStageRepository(session).add(
            PipelineRunStage(
                pipeline_run_id=run.id,
                stage=PipelineStage.HTML_FETCH,
                status=StageExecutionStatus.FAILED,
                item_count=2,
                success_count=1,
                failure_count=1,
            )
        )

    result = list_pipeline_runs(session_factory=session_factory)

    assert len(result.runs) == 1
    assert result.runs[0].run_id >= 1
    assert result.runs[0].status == "partial"
    assert result.runs[0].failure_count == 1



def test_list_pipeline_failures_returns_readable_rows(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="entry-1",
                source_url="https://example.com/articles/1",
                title="Central bank update",
            )
        )
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=source_item.id,
                source_name="Finance Feed",
                article_url="https://example.com/articles/1",
                failure_stage=PipelineStage.HTML_FETCH,
                failure_code="fetch_blocked",
                failure_message="사이트 접근이 차단되었어요",
                html_fetch_status=StageExecutionStatus.FAILED,
                last_stage=PipelineStage.HTML_FETCH,
            )
        )

    result = list_pipeline_failures(session_factory=session_factory)

    assert len(result.failures) == 1
    assert result.failures[0].title == "Central bank update"
    assert result.failures[0].failure_code == "fetch_blocked"
    assert result.failures[0].failure_message == "사이트 접근이 차단되었어요"
    assert result.failures[0].failure_stage == "html_fetch"



def _build_session_factory(tmp_path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'history.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)
