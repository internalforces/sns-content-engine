"""Tests for the FastAPI operator routes."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from textwrap import dedent

from fastapi.testclient import TestClient

from app.api import create_app
from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    ContentBrief,
    ContentBriefRepository,
    DraftVariant,
    DraftVariantRepository,
    DraftVariantState,
    PublishJobRepository,
    PipelineRun,
    PipelineRunRepository,
    PipelineRunStatus,
    StageExecutionStatus,
    PipelineStage,
    SourceItem,
    SourceItemRepository,
    SourcePolicyMode,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)

_DRAFT_SOURCE_COUNTER = count()
_VALID_REVIEW_DRAFT_BODY = "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools"


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
    assert [check["name"] for check in payload["checks"]] == ["config", "config_readiness", "database"]


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


def test_articles_endpoint_returns_article_status_rows(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        pending_source = SourceItemRepository(session).add(
            SourceItem(
                source_key="ops_manual",
                external_id="entry-1",
                source_url="https://example.com/articles/1",
                title="Operator checklist update",
                created_at=datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
            )
        )
        failed_source = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="entry-2",
                source_url="https://example.com/articles/2",
                title="Central bank update",
                published_at=datetime(2026, 3, 17, 21, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            )
        )
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=failed_source.id,
                source_name="Finance Feed",
                article_url="https://example.com/final/2",
                published_at=datetime(2026, 3, 17, 21, 0, tzinfo=timezone.utc),
                discovered_at=datetime(2026, 3, 18, 9, 1, tzinfo=timezone.utc),
                failure_stage=PipelineStage.HTML_FETCH,
                failure_code="fetch_blocked",
                failure_message="site blocked",
                html_fetch_status=StageExecutionStatus.FAILED,
                last_stage=PipelineStage.HTML_FETCH,
            )
        )

    client = TestClient(create_app())
    response = client.get(
        "/articles",
        params={
            "database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["articles"]) == 2
    assert payload["articles"][0]["source_item_id"] == failed_source.id
    assert payload["articles"][0]["source_name"] == "Finance Feed"
    assert payload["articles"][0]["article_url"] == "https://example.com/final/2"
    assert payload["articles"][0]["enrichment_state"] == "failed"
    assert payload["articles"][0]["fetch_status"] == "failed"
    assert payload["articles"][0]["last_failure_message"] == "site blocked"
    assert payload["articles"][1]["source_item_id"] == pending_source.id
    assert payload["articles"][1]["article_enrichment_id"] is None
    assert payload["articles"][1]["source_name"] == "ops_manual"
    assert payload["articles"][1]["enrichment_state"] == "pending"
    assert payload["articles"][1]["fetch_status"] == "pending"
    assert payload["articles"][1]["extract_status"] == "pending"
    assert payload["articles"][1]["summarize_status"] == "pending"


def test_articles_endpoint_returns_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/articles",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    assert response.json() == {"articles": []}


def test_pending_review_endpoint_returns_pending_drafts(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        pending_draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )
        _create_draft_variant(
            session,
            variant_index=1,
            draft_state=DraftVariantState.APPROVED,
            created_at=datetime(2026, 3, 18, 9, 5, tzinfo=timezone.utc),
        )

    client = TestClient(create_app())
    response = client.get(
        "/reviews/pending",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pending_count"] == 1
    assert len(payload["drafts"]) == 1
    assert payload["drafts"][0]["draft_id"] == pending_draft.id
    assert payload["drafts"][0]["account_key"] == "ai_tools_daily"
    assert payload["drafts"][0]["channel"] == "x"
    assert payload["drafts"][0]["title"] == "Brief for draft"
    assert payload["drafts"][0]["body"] == "Useful AI automation workflows for operators"


def test_pending_review_endpoint_returns_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/reviews/pending",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    assert response.json() == {"pending_count": 0, "drafts": []}


def test_review_approve_endpoint_returns_action_result(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    client = TestClient(create_app())
    response = client.post(
        f"/reviews/{draft.id}/approve",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"reviewer": "editor-a", "config_dir": str(tmp_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_id"] == draft.id
    assert payload["reviewer"] == "editor-a"
    assert payload["action_type"] == "approve"
    assert payload["draft_state"] == "approved"
    assert payload["publish_job_id"] is None
    assert payload["scheduled_for"] is None


def test_review_reject_endpoint_returns_action_result(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )

    client = TestClient(create_app())
    response = client.post(
        f"/reviews/{draft.id}/reject",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"reviewer": "editor-b", "reason": "Off topic for this account"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_id"] == draft.id
    assert payload["reviewer"] == "editor-b"
    assert payload["action_type"] == "reject"
    assert payload["draft_state"] == "rejected"


def test_review_edit_endpoint_returns_action_result(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )

    client = TestClient(create_app())
    response = client.post(
        f"/reviews/{draft.id}/edit",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={
            "reviewer": "editor-c",
            "body": "Updated draft body https://gilgop.cloud/ai-tools",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_id"] == draft.id
    assert payload["reviewer"] == "editor-c"
    assert payload["action_type"] == "edit"
    assert payload["draft_state"] == "pending_review"


def test_review_schedule_endpoint_returns_action_result(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            draft_state=DraftVariantState.APPROVED,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    client = TestClient(create_app())
    response = client.post(
        f"/reviews/{draft.id}/schedule",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={
            "reviewer": "scheduler-a",
            "config_dir": str(tmp_path),
            "scheduled_for": "2026-03-18T09:00:00+09:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_id"] == draft.id
    assert payload["reviewer"] == "scheduler-a"
    assert payload["action_type"] == "schedule"
    assert payload["draft_state"] == "approved"
    assert payload["publish_job_id"] is not None
    assert payload["scheduled_for"] == "2026-03-18T00:00:00+00:00"

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session).list()

    assert len(jobs) == 1
    assert jobs[0].draft_variant_id == draft.id


def test_review_action_endpoint_returns_not_found_error(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.post(
        "/reviews/999/approve",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"reviewer": "editor-a", "config_dir": str(tmp_path)},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "draft_not_found",
        "message": "draft 999 was not found",
    }


def test_review_approve_endpoint_returns_validation_error(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body="Operator update for general readers https://gilgop.cloud/ai-tools",
        )

    client = TestClient(create_app())
    response = client.post(
        f"/reviews/{draft.id}/approve",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"reviewer": "editor-a", "config_dir": str(tmp_path)},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "draft_validation_failed"
    assert "topic_guard_failed" in payload["message"]


def test_review_schedule_endpoint_returns_conflict_for_duplicate_job(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            draft_state=DraftVariantState.APPROVED,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    client = TestClient(create_app())
    first_response = client.post(
        f"/reviews/{draft.id}/schedule",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={
            "reviewer": "scheduler-a",
            "config_dir": str(tmp_path),
            "scheduled_for": "2026-03-18T09:00:00+09:00",
        },
    )
    second_response = client.post(
        f"/reviews/{draft.id}/schedule",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={
            "reviewer": "scheduler-a",
            "config_dir": str(tmp_path),
            "scheduled_for": "2026-03-18T10:00:00+09:00",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["error_code"] == "draft_schedule_conflict"


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'api.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


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
            matching:
              include_keywords:
                - ai
                - automation
              source_tags:
                - ai
                - automation
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
                validation:
                  max_links: 1
                  banned_phrases: []
                  recent_duplicate_window_days: 7
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


def _create_draft_variant(
    session,
    *,
    variant_index: int,
    draft_state: DraftVariantState = DraftVariantState.PENDING_REVIEW,
    created_at: datetime,
    body: str = "Useful AI automation workflows for operators",
    include_provenance: bool = False,
) -> DraftVariant:
    source_number = next(_DRAFT_SOURCE_COUNTER)
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"draft-entry-{source_number}",
            source_url=f"https://example.com/drafts/{source_number}",
            title=f"Draft source {source_number}",
        )
    )
    brief = ContentBriefRepository(session).add(
        ContentBrief(
            source_item_id=source_item.id,
            account_key="ai_tools_daily",
            title="Brief for draft",
            summary="Summary for review",
            key_points=["Point one"],
            landing_url="https://gilgop.cloud/ai-tools",
            tags=["ai"],
            angle="topic_takeaway",
            language="en",
        )
    )
    repository = DraftVariantRepository(session)
    draft = repository.add(
        DraftVariant(
            content_brief_id=brief.id,
            channel="x",
            variant_index=variant_index,
            body=body,
            created_at=created_at,
            source_name="AI Tools Daily" if include_provenance else None,
            source_url=f"https://example.com/drafts/{source_number}" if include_provenance else None,
            article_url=f"https://example.com/drafts/{source_number}" if include_provenance else None,
            source_published_at=datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)
            if include_provenance
            else None,
            source_policy_mode=SourcePolicyMode.REUSABLE if include_provenance else None,
        )
    )
    if draft_state is DraftVariantState.APPROVED:
        repository.transition_state(draft, DraftVariantState.APPROVED)
    elif draft_state is DraftVariantState.REJECTED:
        repository.transition_state(
            draft,
            DraftVariantState.REJECTED,
            rejection_reason="Rejected during test setup",
        )
    return draft
