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
    SourcePolicyMode,
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
    assert result.runs[0].trigger_mode == "manual_local"
    assert result.runs[0].failure_count == 1


def test_list_pipeline_runs_surfaces_policy_aware_summary_fields(tmp_path) -> None:
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
                draft_count=6,
                failure_count=0,
                latest_error_code=None,
                summary_json={
                    "policy_mode_counts": {
                        "discovery_only": 1,
                        "reusable": 2,
                    },
                    "policy_skipped_count": 1,
                    "attribution_required_count": 2,
                    "rewrite_providers": ["codex_wrapper", "fake"],
                },
            )
        )

    result = list_pipeline_runs(session_factory=session_factory)

    assert result.runs[0].policy_mode_counts == {
        "discovery_only": 1,
        "reusable": 2,
    }
    assert result.runs[0].policy_skipped_count == 1
    assert result.runs[0].attribution_required_count == 2
    assert result.runs[0].rewrite_providers == ("codex_wrapper", "fake")



def test_list_pipeline_failures_returns_readable_rows(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
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
        policy_skip_source_item = SourceItemRepository(session).add(
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
                source_item_id=policy_skip_source_item.id,
                source_name="Wikinews",
                article_url="https://example.com/articles/2",
                policy_decision_reason="Source policy blocks full-text fetch for this item (mode=discovery_only).",
                html_fetch_status=StageExecutionStatus.SKIPPED,
                article_extract_status=StageExecutionStatus.SKIPPED,
                summary_regenerate_status=StageExecutionStatus.SKIPPED,
                last_stage=PipelineStage.HTML_FETCH,
            )
        )

    result = list_pipeline_failures(session_factory=session_factory)

    assert len(result.failures) == 1
    assert result.failures[0].title == "Central bank update"
    assert result.failures[0].source_policy_mode == "restricted"
    assert result.failures[0].require_attribution is True
    assert result.failures[0].failure_code == "fetch_blocked"
    assert result.failures[0].failure_message == "사이트 접근이 차단되었어요"
    assert result.failures[0].failure_stage == "html_fetch"
    assert len(result.policy_skips) == 1
    assert result.policy_skips[0].title == "Election watchdog report"
    assert result.policy_skips[0].source_policy_mode == "discovery_only"
    assert result.policy_skips[0].require_attribution is True
    assert result.policy_skips[0].skipped_stage == "html_fetch"
    assert (
        result.policy_skips[0].policy_decision_reason
        == "Source policy blocks full-text fetch for this item (mode=discovery_only)."
    )



def _build_session_factory(tmp_path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'history.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)
