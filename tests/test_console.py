"""Focused tests for the server-rendered operator console shell."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from textwrap import dedent

from fastapi.testclient import TestClient

from app.api import create_app
from app.domain import DuplicateReason, SourceDiscoveryFailure, SourceItemCandidate
from app.scheduler import (
    BackfillChannelResult,
    BackfillResult,
    PublishDueOutcome,
    PublishDueResult,
    SchedulerDiscoverResult,
)
from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    ContentBrief,
    ContentBriefRepository,
    DraftVariant,
    DraftVariantRepository,
    DraftVariantState,
    PipelineRun,
    PipelineRunRepository,
    PipelineRunStatus,
    PipelineStage,
    PublishJob,
    PublishJobState,
    PublishLogRepository,
    PublishJobRepository,
    SourceItem,
    SourceItemRepository,
    SourcePolicyMode,
    StageExecutionStatus,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.workflows import (
    EnrichArticleOutcome,
    EnrichArticlesResult,
    IngestSourcesResult,
    RunLocalPipelineResult,
    SourceIngestOutcome,
)
from app.workflows.review_queue import (
    PendingReviewDraft,
    PendingReviewDraftsResult,
    approve_draft,
    edit_draft,
    schedule_draft,
)

_DRAFT_SOURCE_COUNTER = count()


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
    assert "운영 콘솔" in response.text
    assert "콘솔 홈" in response.text
    assert "실행 및 실패" in response.text
    assert "검토 대기" in response.text
    assert "/tmp/operator-config" in response.text
    assert "sqlite:///tmp/operator.db" in response.text
    assert "수동 검토 필수" in response.text
    assert "브라우저 기본 발행 경로는 드라이런입니다" in response.text


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
    assert "실행 대시보드" in response.text
    assert "실행 대시보드가 데이터를 기다리고 있습니다. 아직 기록된 파이프라인 실행이 없습니다." in response.text
    assert "현재 운영 콘텍스트에 표시할 최근 실행 이력이 아직 없습니다." in response.text
    assert "현재 표시할 기술 실패가 없습니다." in response.text
    assert "현재 표시할 정책상 건너뜀이 없습니다." in response.text


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
    assert "실행 대시보드" in response.text
    assert "run_local_finance" in response.text
    assert "부분 완료" in response.text
    assert "발견 4 / 저장 3 / 보강 2 / 브리프 2 / 초안 5 / 실패 1" in response.text
    assert "제한됨 1 / 재사용 가능 3" in response.text
    assert "정책상 건너뜀 1 / 출처 표기 필수 2" in response.text
    assert "codex_wrapper, fake" in response.text
    assert "Central bank update" in response.text
    assert "site blocked" in response.text
    assert "Election watchdog report" in response.text
    assert "Source policy blocks full-text fetch for this item." in response.text


def test_articles_page_renders_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/articles",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "아티클 상태" in response.text
    assert "현재 운영 콘텍스트에서 최근 소스 항목을 저장된 발견 순서 기준 최대 25개까지 보여줍니다." in response.text
    assert "현재 운영 콘텍스트에 표시할 저장된 아티클 행이 아직 없습니다." in response.text


def test_articles_page_renders_recent_article_rows(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        SourceItemRepository(session).add(
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
        "/console/articles",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "아티클 상태" in response.text
    assert "Central bank update" in response.text
    assert "Finance Feed" in response.text
    assert "https://example.com/final/2" in response.text
    assert "실패" in response.text
    assert "수집 실패 / 추출 대기 / 요약 대기" in response.text
    assert "site blocked" in response.text
    assert "Operator checklist update" in response.text
    assert "해결된 아티클 URL이 아직 기록되지 않았습니다." in response.text


def test_pending_review_page_renders_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/reviews/pending",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "검토 대기" in response.text
    assert "각 대기열 행은 하나의 초안 작업공간으로 연결되어" in response.text
    assert "현재 수동 검토를 기다리는 초안이 없습니다." in response.text


def test_pending_review_page_renders_current_queue_only(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        pending_draft = _create_pending_review_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            brief_title="Brief for draft",
            body="Useful AI automation workflows for operators",
        )
        _create_pending_review_draft(
            session,
            variant_index=1,
            created_at=datetime(2026, 3, 18, 9, 5, tzinfo=timezone.utc),
            brief_title="Hidden approved draft",
            body="This approved draft should not appear in the pending queue",
            draft_state=DraftVariantState.APPROVED,
        )

    client = TestClient(create_app())
    response = client.get(
        "/console/reviews/pending",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "검토 대기" in response.text
    assert f"초안 {pending_draft.id}" in response.text
    assert "버전 0" in response.text
    assert "ai_tools_daily" in response.text
    assert "Useful AI automation workflows for operators" in response.text
    assert f'/console/reviews/{pending_draft.id}' in response.text
    assert "Hidden approved draft" not in response.text
    assert "This approved draft should not appear in the pending queue" not in response.text


def test_review_detail_page_renders_full_draft_context(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    attributed_body_template = (
        "AI Tools Daily via example.com: Useful AI automation workflows for operators {article_url}"
    )
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=attributed_body_template,
            include_provenance=True,
            include_article_enrichment=True,
        )
    attributed_body = attributed_body_template.format(article_url=draft.article_url)

    edited_body = (
        "AI Tools Daily via example.com: Edited AI automation workflow summary for operators "
        f"{draft.article_url}"
    )
    edit_draft(
        draft.id,
        body=edited_body,
        reviewer="editor-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )
    approve_draft(
        draft.id,
        reviewer="editor-b",
        config_dir=tmp_path,
        session_factory=session_factory,
    )
    schedule_result = schedule_draft(
        draft.id,
        scheduled_for="2026-03-18T09:00:00+09:00",
        reviewer="scheduler-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )

    with session_scope(session_factory) as session:
        repository = DraftVariantRepository(session)
        stored_draft = repository.get(draft.id)
        assert stored_draft is not None
        repository.add(
            DraftVariant(
                content_brief_id=stored_draft.content_brief_id,
                channel="x",
                variant_index=2,
                body="Variant two for deeper operator analysis",
                created_at=datetime(2026, 3, 18, 9, 20, tzinfo=timezone.utc),
            )
        )
        sibling = repository.add(
            DraftVariant(
                content_brief_id=stored_draft.content_brief_id,
                channel="x",
                variant_index=1,
                body="Variant one with a shorter operator hook",
                created_at=datetime(2026, 3, 18, 9, 10, tzinfo=timezone.utc),
            )
        )
        repository.add(
            DraftVariant(
                content_brief_id=stored_draft.content_brief_id,
                channel="linkedin",
                variant_index=0,
                body="Different channel variant should stay hidden",
                created_at=datetime(2026, 3, 18, 9, 30, tzinfo=timezone.utc),
            )
        )

    client = TestClient(create_app())
    response = client.get(
        f"/console/reviews/{draft.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert f"검토 초안 {draft.id}" in response.text
    assert f"초안 {draft.id}" in response.text
    assert "Brief for draft" in response.text
    assert "AI Tools Daily" in response.text
    assert "Regenerated article summary for operators" in response.text
    assert "Detail point one" in response.text
    assert "editor-a" in response.text
    assert "editor-b" in response.text
    assert "scheduler-a" in response.text
    assert attributed_body in response.text
    assert edited_body in response.text
    assert f"발행 작업 {schedule_result.publish_job_id}" in response.text
    assert "Variant one with a shorter operator hook" in response.text
    assert "Variant two for deeper operator analysis" in response.text
    assert f'/console/reviews/{sibling.id}' in response.text
    assert "Different channel variant should stay hidden" not in response.text


def test_review_detail_page_returns_browser_friendly_not_found(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/reviews/999",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 404
    assert "검토 초안을 찾을 수 없음" in response.text
    assert "draft 999 was not found" in response.text
    assert "/console/reviews/pending" in response.text


def test_review_actions_approve_success_updates_detail_state(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    body = "AI Tools Daily via example.com: Useful AI automation workflows for operators https://gilgop.cloud/ai-tools"
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=body,
            include_provenance=True,
        )

    client = TestClient(create_app())
    response = _post_console_review_action(
        client,
        draft_id=draft.id,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'console.db'}",
        config_dir=tmp_path,
        action="approve",
        reviewer="editor-a",
    )

    assert response.status_code == 200
    assert "승인 완료" in response.text
    assert "초안이 승인되었습니다. 이제 이 작업공간에서 예약을 진행할 수 있습니다." in response.text
    assert "승인됨" in response.text
    assert "발행 작업 만들기" in response.text

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft.id)

    assert stored_draft is not None
    assert stored_draft.state is DraftVariantState.APPROVED


def test_review_actions_reject_success_records_reason(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )

    client = TestClient(create_app())
    response = _post_console_review_action(
        client,
        draft_id=draft.id,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'console.db'}",
        action="reject",
        reviewer="editor-b",
        reason="Off topic for this account",
    )

    assert response.status_code == 200
    assert "반려 완료" in response.text
    assert "Off topic for this account" in response.text
    assert "이 초안의 현재 상태에서는 브라우저 작업을 수행할 수 없습니다." in response.text

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft.id)

    assert stored_draft is not None
    assert stored_draft.state is DraftVariantState.REJECTED


def test_review_actions_edit_success_renders_updated_body(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )

    updated_body = "Updated operator-ready draft body https://gilgop.cloud/ai-tools"
    client = TestClient(create_app())
    response = _post_console_review_action(
        client,
        draft_id=draft.id,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'console.db'}",
        action="edit",
        reviewer="editor-c",
        body=updated_body,
    )

    assert response.status_code == 200
    assert "수정 완료" in response.text
    assert updated_body in response.text
    assert "editor-c" in response.text

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft.id)

    assert stored_draft is not None
    assert stored_draft.body == updated_body
    assert stored_draft.state is DraftVariantState.PENDING_REVIEW


def test_review_actions_schedule_success_creates_publish_job(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    body = "AI Tools Daily via example.com: Useful AI automation workflows for operators https://gilgop.cloud/ai-tools"
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            draft_state=DraftVariantState.APPROVED,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=body,
            include_provenance=True,
        )

    client = TestClient(create_app())
    response = _post_console_review_action(
        client,
        draft_id=draft.id,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'console.db'}",
        config_dir=tmp_path,
        action="schedule",
        reviewer="scheduler-a",
        scheduled_for="2026-03-18T09:00:00+09:00",
    )

    assert response.status_code == 200
    assert "예약 완료" in response.text
    assert "초안이 2026-03-18T00:00:00+00:00에 예약되었고 발행 작업 1이 생성되었습니다." in response.text
    assert "작업 완료" not in response.text

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session).list()

    assert len(jobs) == 1
    assert jobs[0].draft_variant_id == draft.id


def test_review_actions_approve_validation_error_stays_browser_readable(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body="Operator update for general readers https://gilgop.cloud/ai-tools",
            include_provenance=True,
        )

    client = TestClient(create_app())
    response = _post_console_review_action(
        client,
        draft_id=draft.id,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'console.db'}",
        config_dir=tmp_path,
        action="approve",
        reviewer="editor-a",
    )

    assert response.status_code == 422
    assert "승인 불가" in response.text
    assert "topic_guard_failed" in response.text
    assert "초안 승인" in response.text
    assert "초안 본문 수정" in response.text


def test_review_actions_schedule_conflict_preserves_submitted_slot(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    body = "AI Tools Daily via example.com: Useful AI automation workflows for operators https://gilgop.cloud/ai-tools"
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            draft_state=DraftVariantState.APPROVED,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=body,
            include_provenance=True,
        )

    schedule_draft(
        draft.id,
        scheduled_for="2026-03-18T09:00:00+09:00",
        reviewer="scheduler-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )

    client = TestClient(create_app())
    response = _post_console_review_action(
        client,
        draft_id=draft.id,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'console.db'}",
        config_dir=tmp_path,
        action="schedule",
        reviewer="scheduler-a",
        scheduled_for="2026-03-18T10:00:00+09:00",
    )

    assert response.status_code == 409
    assert "예약 불가" in response.text
    assert "already has an active publish job" in response.text
    assert 'value="2026-03-18T10:00:00+09:00"' in response.text


def test_publish_jobs_page_renders_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/publish-jobs",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "발행 작업" in response.text
    assert "대기 중이거나 완료된 발행 작업" in response.text
    assert "현재 운영 콘텍스트에 저장된 발행 작업이 아직 없습니다." in response.text


def test_publish_jobs_page_renders_rows_and_links(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        scheduled_job = _create_publish_job(
            session,
            variant_index=0,
            brief_title="Queued AI brief",
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            scheduled_for=datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc),
        )
        failed_job = _create_publish_job(
            session,
            variant_index=1,
            brief_title="Failed AI brief",
            created_at=datetime(2026, 3, 18, 9, 5, tzinfo=timezone.utc),
            scheduled_for=datetime(2026, 3, 18, 12, 30, tzinfo=timezone.utc),
            state=PublishJobState.FAILED,
            last_error="missing access token",
        )
        published_job = _create_publish_job(
            session,
            account_key="finance_news_daily",
            channel="linkedin",
            variant_index=0,
            brief_title="Published finance brief",
            created_at=datetime(2026, 3, 18, 9, 10, tzinfo=timezone.utc),
            scheduled_for=datetime(2026, 3, 18, 13, 0, tzinfo=timezone.utc),
            state=PublishJobState.PUBLISHED,
            external_post_id="li:123",
        )
        scheduled_job_id = scheduled_job.id
        scheduled_draft_id = scheduled_job.draft_variant_id
        failed_job_id = failed_job.id
        published_job_id = published_job.id

    client = TestClient(create_app())
    response = client.get(
        "/console/publish-jobs",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "표시 중인 작업" in response.text
    assert "활성 대기열" in response.text
    assert "확인 필요" in response.text
    assert "Queued AI brief" in response.text
    assert "Failed AI brief" in response.text
    assert "Published finance brief" in response.text
    assert "missing access token" in response.text
    assert "li:123" in response.text
    assert f"/console/publish-jobs/{scheduled_job_id}" in response.text
    assert f"/console/publish-jobs/{failed_job_id}" in response.text
    assert f"/console/publish-jobs/{published_job_id}" in response.text
    assert f"/console/reviews/{scheduled_draft_id}" in response.text


def test_publish_jobs_detail_page_renders_published_timeline(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        job = _create_publish_job(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            scheduled_for=datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc),
            state=PublishJobState.PUBLISHED,
            external_post_id="tweet:detail-1",
            include_provenance=True,
            log_events=[
                (
                    "scheduled",
                    "publish job queued for operator review",
                    {"scheduled_for": "2026-03-18T12:00:00+00:00"},
                ),
                (
                    "publishing",
                    "publisher execution started",
                    {"attempt_count": 1, "channel": "x"},
                ),
                (
                    "published",
                    "publish job completed successfully",
                    {"external_post_id": "tweet:detail-1"},
                ),
            ],
        )
        job_id = job.id

    client = TestClient(create_app())
    response = client.get(
        f"/console/publish-jobs/{job_id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert f"발행 작업 {job_id}" in response.text
    assert "발행 작업 목록으로 돌아가기" in response.text
    assert "검토 작업공간 열기" in response.text
    assert "publish job completed successfully" in response.text
    assert "publisher execution started" in response.text
    assert "tweet:detail-1" in response.text
    assert "AI Tools Daily" in response.text
    assert "저장된 소스 콘텍스트" in response.text


def test_publish_jobs_detail_page_renders_failed_context(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        job = _create_publish_job(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 15, tzinfo=timezone.utc),
            scheduled_for=datetime(2026, 3, 18, 12, 30, tzinfo=timezone.utc),
            state=PublishJobState.FAILED,
            last_error="missing access token",
            log_events=[
                ("publishing", "publisher execution started", {"attempt_count": 1}),
                (
                    "failed",
                    "publish job failed: missing access token",
                    {"error_message": "missing access token", "status": "failed"},
                ),
            ],
        )
        job_id = job.id

    client = TestClient(create_app())
    response = client.get(
        f"/console/publish-jobs/{job_id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert f"발행 작업 {job_id}" in response.text
    assert "실패" in response.text
    assert "missing access token" in response.text
    assert "publish job failed: missing access token" in response.text


def test_publish_jobs_detail_page_handles_missing_job(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/publish-jobs/999",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 404
    assert "발행 작업을 불러올 수 없습니다" in response.text
    assert "publish job 999 was not found" in response.text


def test_scheduler_actions_page_renders_safe_defaults(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/scheduler",
        params={
            "config_dir": "/tmp/operator-config",
            "database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}",
        },
    )

    assert response.status_code == 200
    assert "스케줄러" in response.text
    assert "뉴스 수집, 발견만 확인, 저장, 보강, 백필, 발행 예정 처리" in response.text
    assert "이 브라우저 세션에서 아직 실행된 운영 작업이 없습니다." in response.text
    assert "뉴스 수집 실행" in response.text
    assert "발견만 실행" in response.text
    assert "수집 저장 실행" in response.text
    assert "기사 보강 실행" in response.text
    assert "백필 실행" in response.text
    assert "발행 예정 처리 실행" in response.text
    assert "이번 실행에만 실발행 허용" in response.text
    assert "/tmp/operator-config" in response.text


def test_scheduler_actions_discover_post_renders_summary() -> None:
    captured: dict[str, object] = {}

    def stub_scheduler_discover(*, config_dir: str) -> SchedulerDiscoverResult:
        captured["config_dir"] = config_dir
        return SchedulerDiscoverResult(
            discovered_count=3,
            processed_sources=("ai_tools_rss", "manual_csv"),
            failure_messages=("manual_csv: feed parse failed",),
        )

    client = TestClient(create_app(scheduler_discover_runner=stub_scheduler_discover))
    response = _post_console_scheduler_action(
        client,
        action="discover",
        config_dir="/tmp/operator-config",
        database_url="sqlite+pysqlite:////tmp/operator.db",
    )

    assert response.status_code == 200
    assert captured == {"config_dir": "/tmp/operator-config"}
    assert "수집 완료" in response.text
    assert "후보 수집이 완료되었습니다. 2개의 설정된 소스에서 3개의 항목을 발견했습니다." in response.text
    assert "ai_tools_rss" in response.text
    assert "manual_csv: feed parse failed" in response.text


def test_scheduler_actions_ingest_post_renders_summary() -> None:
    captured: dict[str, object] = {}

    def stub_ingest_sources(
        *,
        config_dir: str,
        database_url: str | None = None,
    ) -> IngestSourcesResult:
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        return IngestSourcesResult(
            outcomes=(
                SourceIngestOutcome(
                    candidate=SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="entry-1",
                        source_url="https://example.com/posts/1",
                        title="Fresh item",
                    ),
                    status="saved",
                    source_item_id=10,
                ),
                SourceIngestOutcome(
                    candidate=SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="entry-2",
                        source_url="https://example.com/posts/2",
                        title="Duplicate item",
                    ),
                    status="duplicate",
                    duplicate_reason=DuplicateReason.CANONICAL_URL,
                    matched_item_id=9,
                ),
            ),
            failures=(
                SourceDiscoveryFailure(
                    source_id="ai_tools_manual",
                    stage="read",
                    message="csv missing",
                ),
            ),
            processed_sources=("ai_tools_manual", "ai_tools_rss"),
        )

    client = TestClient(create_app(ingest_sources_runner=stub_ingest_sources))
    response = _post_console_scheduler_action(
        client,
        action="ingest",
        config_dir="/tmp/operator-config",
        database_url="sqlite+pysqlite:////tmp/operator.db",
    )

    assert response.status_code == 200
    assert captured == {
        "config_dir": "/tmp/operator-config",
        "database_url": "sqlite+pysqlite:////tmp/operator.db",
    }
    assert "수집 저장 완료" in response.text
    assert "수집 저장이 완료되었습니다. 2개의 발견 후보 중 1개를 저장했고 1개 중복을 차단했습니다." in response.text
    assert "대표 URL 중복 1" in response.text
    assert "ai_tools_manual [read] csv missing" in response.text


def test_scheduler_actions_enrich_post_renders_summary() -> None:
    captured: dict[str, object] = {}

    def stub_enrich_articles(
        *,
        config_dir: str,
        database_url: str | None = None,
    ) -> EnrichArticlesResult:
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        return EnrichArticlesResult(
            processed_source_item_ids=(1, 2, 3),
            outcomes=(
                EnrichArticleOutcome(source_item_id=1, status="enriched", article_enrichment_id=21),
                EnrichArticleOutcome(source_item_id=2, status="skipped", article_enrichment_id=22),
                EnrichArticleOutcome(
                    source_item_id=3,
                    status="failed",
                    article_enrichment_id=23,
                    failure_code="extract_failed",
                    failure_stage=PipelineStage.ARTICLE_EXTRACT,
                ),
            ),
        )

    client = TestClient(create_app(enrich_articles_runner=stub_enrich_articles))
    response = _post_console_scheduler_action(
        client,
        action="enrich",
        config_dir="/tmp/operator-config",
        database_url="sqlite+pysqlite:////tmp/operator.db",
    )

    assert response.status_code == 200
    assert captured == {
        "config_dir": "/tmp/operator-config",
        "database_url": "sqlite+pysqlite:////tmp/operator.db",
    }
    assert "기사 보강 완료" in response.text
    assert "기사 보강이 완료되었습니다. 3개의 저장된 수집 항목 중 1개를 보강했고 1개를 정책에 따라 건너뛰었습니다." in response.text
    assert "본문 추출 1" in response.text


def test_scheduler_actions_run_local_post_renders_summary() -> None:
    captured: dict[str, object] = {}

    def stub_run_local_pipeline(
        *,
        config_dir: str,
        database_url: str | None = None,
    ) -> RunLocalPipelineResult:
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        return RunLocalPipelineResult(
            pipeline_run_id=77,
            status=PipelineRunStatus.PARTIAL,
            ingest_discovered_count=6,
            ingest_saved_count=4,
            enrichment_enriched_count=3,
            brief_created_count=3,
            draft_created_variant_count=9,
            failure_count=1,
            duplicate_count=2,
            duplicate_reasons=(("source_identity", 2),),
        )

    client = TestClient(create_app(run_local_pipeline_runner=stub_run_local_pipeline))
    response = _post_console_scheduler_action(
        client,
        action="run_local",
        config_dir="/tmp/operator-config",
        database_url="sqlite+pysqlite:////tmp/operator.db",
    )

    assert response.status_code == 200
    assert captured == {
        "config_dir": "/tmp/operator-config",
        "database_url": "sqlite+pysqlite:////tmp/operator.db",
    }
    assert "뉴스 수집 완료" in response.text
    assert "뉴스 수집이 완료되었습니다. 발견 6, 저장 4, 중복 차단 2, 보강 3, 브리프 3, 초안 9건입니다. 생성된 초안은 검토 대기열에 저장되었습니다." in response.text
    assert "실행 ID" in response.text
    assert "부분 완료" in response.text
    assert "중복 차단" in response.text
    assert "소스 고유 ID 중복 2" in response.text


def test_scheduler_actions_run_local_post_lists_created_draft_links() -> None:
    def stub_run_local_pipeline(
        *,
        config_dir: str,
        database_url: str | None = None,
    ) -> RunLocalPipelineResult:
        return RunLocalPipelineResult(
            pipeline_run_id=77,
            status=PipelineRunStatus.SUCCEEDED,
            ingest_discovered_count=2,
            ingest_saved_count=2,
            enrichment_enriched_count=2,
            brief_created_count=2,
            draft_created_variant_count=2,
            failure_count=0,
            duplicate_count=0,
            created_draft_ids=(401, 402),
        )

    def stub_pending_review_drafts_lister(
        *,
        database_url: str | None = None,
    ) -> PendingReviewDraftsResult:
        return PendingReviewDraftsResult(
            drafts=(
                PendingReviewDraft(
                    draft_id=401,
                    account_key="finance_insights_daily",
                    channel="x",
                    variant_index=0,
                    created_at=datetime(2026, 4, 11, 9, 0, tzinfo=timezone.utc),
                    title="Fed minutes draft",
                    body="First saved draft body with article url https://example.com/articles/401",
                ),
                PendingReviewDraft(
                    draft_id=402,
                    account_key="finance_insights_daily",
                    channel="x",
                    variant_index=1,
                    created_at=datetime(2026, 4, 11, 9, 1, tzinfo=timezone.utc),
                    title="Rate statement draft",
                    body="Second saved draft body with article url https://example.com/articles/402",
                ),
            ),
        )

    client = TestClient(
        create_app(
            run_local_pipeline_runner=stub_run_local_pipeline,
            pending_review_drafts_lister=stub_pending_review_drafts_lister,
        )
    )
    response = _post_console_scheduler_action(
        client,
        action="run_local",
        config_dir="/tmp/operator-config",
        database_url="sqlite+pysqlite:////tmp/operator.db",
    )

    assert response.status_code == 200
    assert "검토 대기열 열기" in response.text
    assert "초안 401" in response.text
    assert "Fed minutes draft" in response.text
    assert "초안 402" in response.text
    assert "Rate statement draft" in response.text
    assert "/console/reviews/pending" in response.text
    assert "/console/reviews/401" in response.text


def test_scheduler_actions_backfill_post_renders_summary() -> None:
    captured: dict[str, object] = {}

    def stub_scheduler_backfill(
        *,
        config_dir: str,
        database_url: str | None = None,
    ) -> BackfillResult:
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        return BackfillResult(
            outcomes=(
                BackfillChannelResult(
                    account_key="ai_tools_daily",
                    channel="x",
                    backlog_target=3,
                    existing_future_job_count=1,
                    eligible_draft_count=4,
                    planned_slot_count=2,
                    created_job_ids=(12, 13),
                    skipped_slot_count=0,
                ),
            )
        )

    client = TestClient(create_app(scheduler_backfill_runner=stub_scheduler_backfill))
    response = _post_console_scheduler_action(
        client,
        action="backfill",
        config_dir="/tmp/operator-config",
        database_url="sqlite+pysqlite:////tmp/operator.db",
    )

    assert response.status_code == 200
    assert captured == {
        "config_dir": "/tmp/operator-config",
        "database_url": "sqlite+pysqlite:////tmp/operator.db",
    }
    assert "백필 완료" in response.text
    assert "ai_tools_daily / X" in response.text
    assert "생성한 작업 12, 13" in response.text
    assert "확인한 경로" in response.text


def test_scheduler_actions_publish_due_defaults_to_dry_run() -> None:
    captured: dict[str, object] = {}

    def stub_publish_due(
        *,
        config_dir: str,
        database_url: str | None = None,
        dry_run: bool,
    ) -> PublishDueResult:
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        captured["dry_run"] = dry_run
        return PublishDueResult(
            outcomes=(
                PublishDueOutcome(
                    publish_job_id=42,
                    status="dry_run",
                    state=PublishJobState.SCHEDULED,
                    message="dry-run only; no state changes were applied",
                    external_post_id="dry-run:42",
                ),
            ),
            dry_run=dry_run,
        )

    client = TestClient(create_app(scheduler_publish_due_runner=stub_publish_due))
    response = _post_console_scheduler_action(
        client,
        action="publish_due",
        config_dir="/tmp/operator-config",
        database_url="sqlite+pysqlite:////tmp/operator.db",
    )

    assert response.status_code == 200
    assert captured == {
        "config_dir": "/tmp/operator-config",
        "database_url": "sqlite+pysqlite:////tmp/operator.db",
        "dry_run": True,
    }
    assert "발행 예정 처리 완료" in response.text
    assert "드라이런이 브라우저 기본 경로로 유지되어 발행 상태 변경은 적용되지 않았습니다." in response.text
    assert "발행 모드:</strong> 드라이런" in response.text
    assert "dry-run only; no state changes were applied" in response.text


def test_scheduler_actions_publish_due_live_opt_in_is_explicit() -> None:
    captured: dict[str, object] = {}

    def stub_publish_due(
        *,
        config_dir: str,
        database_url: str | None = None,
        dry_run: bool,
    ) -> PublishDueResult:
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        captured["dry_run"] = dry_run
        return PublishDueResult(
            outcomes=(
                PublishDueOutcome(
                    publish_job_id=43,
                    status="published",
                    state=PublishJobState.PUBLISHED,
                    message="published successfully",
                    external_post_id="tweet:43",
                ),
            ),
            dry_run=dry_run,
        )

    client = TestClient(create_app(scheduler_publish_due_runner=stub_publish_due))
    response = _post_console_scheduler_action(
        client,
        action="publish_due",
        config_dir="/tmp/operator-config",
        database_url="sqlite+pysqlite:////tmp/operator.db",
        live=True,
    )

    assert response.status_code == 200
    assert captured == {
        "config_dir": "/tmp/operator-config",
        "database_url": "sqlite+pysqlite:////tmp/operator.db",
        "dry_run": False,
    }
    assert "발행 예정 처리 완료" in response.text
    assert "브라우저에서 명시적으로 선택했기 때문에 실발행이 실행되었습니다." in response.text
    assert "발행 모드:</strong> 실발행" in response.text
    assert "published successfully" in response.text


def test_console_read_only_pages_share_linked_operator_context(tmp_path: Path) -> None:
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
                draft_count=2,
                failure_count=1,
                latest_error_code="fetch_blocked",
                summary_json={
                    "policy_mode_counts": {"reusable": 3, "restricted": 1},
                    "policy_skipped_count": 1,
                    "attribution_required_count": 1,
                    "rewrite_providers": ["codex_wrapper"],
                },
            )
        )
        failed_source = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="linked-entry-1",
                source_url="https://example.com/articles/linked-1",
                title="Central bank update",
                published_at=datetime(2026, 3, 17, 21, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
                policy_mode=SourcePolicyMode.RESTRICTED,
                require_attribution=True,
            )
        )
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=failed_source.id,
                source_name="Finance Feed",
                article_url="https://example.com/final/linked-1",
                published_at=datetime(2026, 3, 17, 21, 0, tzinfo=timezone.utc),
                discovered_at=datetime(2026, 3, 18, 9, 1, tzinfo=timezone.utc),
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
                external_id="linked-entry-2",
                source_url="https://example.com/articles/linked-2",
                title="Election watchdog report",
                policy_mode=SourcePolicyMode.DISCOVERY_ONLY,
                require_attribution=True,
            )
        )
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=skipped_source.id,
                source_name="Wikinews",
                article_url="https://example.com/articles/linked-2",
                policy_decision_reason="Source policy blocks full-text fetch for this item.",
                html_fetch_status=StageExecutionStatus.SKIPPED,
                article_extract_status=StageExecutionStatus.SKIPPED,
                summary_regenerate_status=StageExecutionStatus.SKIPPED,
                last_stage=PipelineStage.HTML_FETCH,
                updated_at=datetime(2026, 3, 18, 9, 9, tzinfo=timezone.utc),
            )
        )
        pending_draft = _create_pending_review_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 10, tzinfo=timezone.utc),
            brief_title="Linked pending brief",
            body="Useful AI automation workflows for operators",
        )
        publish_job = _create_publish_job(
            session,
            variant_index=1,
            brief_title="Linked scheduled brief",
            created_at=datetime(2026, 3, 18, 9, 20, tzinfo=timezone.utc),
            scheduled_for=datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc),
            include_provenance=True,
        )
        publish_job_id = publish_job.id
        linked_review_draft_id = publish_job.draft_variant_id

    database_url = f"sqlite+pysqlite:///{tmp_path / 'console.db'}"
    params = {"config_dir": "/tmp/operator-config", "database_url": database_url}
    client = TestClient(create_app())

    home_response = client.get("/console/", params=params)
    assert home_response.status_code == 200
    assert "운영 콘솔" in home_response.text
    assert "실행 및 실패" in home_response.text
    assert "발행 작업" in home_response.text
    assert "수동 검토 필수" in home_response.text

    dashboard_response = client.get("/console/dashboard", params=params)
    assert dashboard_response.status_code == 200
    assert "run_local_finance" in dashboard_response.text
    assert "Central bank update" in dashboard_response.text
    assert "Election watchdog report" in dashboard_response.text

    articles_response = client.get("/console/articles", params=params)
    assert articles_response.status_code == 200
    assert "Finance Feed" in articles_response.text
    assert "site blocked" in articles_response.text

    pending_response = client.get("/console/reviews/pending", params=params)
    assert pending_response.status_code == 200
    assert f"/console/reviews/{pending_draft.id}" in pending_response.text

    publish_jobs_response = client.get("/console/publish-jobs", params=params)
    assert publish_jobs_response.status_code == 200
    assert f"/console/publish-jobs/{publish_job_id}" in publish_jobs_response.text
    assert f"/console/reviews/{linked_review_draft_id}" in publish_jobs_response.text

    publish_job_detail_response = client.get(
        f"/console/publish-jobs/{publish_job_id}",
        params=params,
    )
    assert publish_job_detail_response.status_code == 200
    assert "발행 작업 목록으로 돌아가기" in publish_job_detail_response.text
    assert f"/console/reviews/{linked_review_draft_id}" in publish_job_detail_response.text

    scheduler_response = client.get("/console/scheduler", params=params)
    assert scheduler_response.status_code == 200
    assert "뉴스 수집 실행" in scheduler_response.text
    assert "수집 저장 실행" in scheduler_response.text
    assert "기사 보강 실행" in scheduler_response.text
    assert "발행 예정 처리 실행" in scheduler_response.text
    assert "이번 실행에만 실발행 허용" in scheduler_response.text


def test_console_mutation_flow_links_review_publish_and_safe_scheduler_actions(
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def stub_publish_due(
        *,
        config_dir: str,
        database_url: str | None = None,
        dry_run: bool,
    ) -> PublishDueResult:
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        captured["dry_run"] = dry_run
        return PublishDueResult(
            outcomes=(
                PublishDueOutcome(
                    publish_job_id=99,
                    status="dry_run",
                    state=PublishJobState.SCHEDULED,
                    message="dry-run only; no state changes were applied",
                    external_post_id="dry-run:99",
                ),
            ),
            dry_run=dry_run,
        )

    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    body_template = "AI Tools Daily via example.com: Useful AI automation workflows for operators {article_url}"
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=body_template,
            include_provenance=True,
            include_article_enrichment=True,
        )
    body = body_template.format(article_url=draft.article_url)

    database_url = f"sqlite+pysqlite:///{tmp_path / 'console.db'}"
    config_dir = str(tmp_path)
    params = {"config_dir": config_dir, "database_url": database_url}
    client = TestClient(create_app(scheduler_publish_due_runner=stub_publish_due))

    pending_before_response = client.get("/console/reviews/pending", params=params)
    assert pending_before_response.status_code == 200
    assert f"/console/reviews/{draft.id}" in pending_before_response.text

    detail_before_response = client.get(f"/console/reviews/{draft.id}", params=params)
    assert detail_before_response.status_code == 200
    assert "초안 승인" in detail_before_response.text
    assert "초안 본문 수정" in detail_before_response.text

    approve_response = _post_console_review_action(
        client,
        draft_id=draft.id,
        database_url=database_url,
        config_dir=tmp_path,
        action="approve",
        reviewer="editor-a",
    )
    assert approve_response.status_code == 200
    assert "승인 완료" in approve_response.text
    assert "발행 작업 만들기" in approve_response.text

    schedule_response = _post_console_review_action(
        client,
        draft_id=draft.id,
        database_url=database_url,
        config_dir=tmp_path,
        action="schedule",
        reviewer="scheduler-a",
        scheduled_for="2026-03-18T09:00:00+09:00",
    )
    assert schedule_response.status_code == 200
    assert "예약 완료" in schedule_response.text

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session).list()

    assert len(jobs) == 1
    publish_job_id = jobs[0].id

    pending_after_response = client.get("/console/reviews/pending", params=params)
    assert pending_after_response.status_code == 200
    assert "현재 수동 검토를 기다리는 초안이 없습니다." in pending_after_response.text

    publish_jobs_response = client.get("/console/publish-jobs", params=params)
    assert publish_jobs_response.status_code == 200
    assert f"/console/publish-jobs/{publish_job_id}" in publish_jobs_response.text
    assert f"/console/reviews/{draft.id}" in publish_jobs_response.text

    publish_job_detail_response = client.get(
        f"/console/publish-jobs/{publish_job_id}",
        params=params,
    )
    assert publish_job_detail_response.status_code == 200
    assert "검토 작업공간 열기" in publish_job_detail_response.text
    assert f"/console/reviews/{draft.id}" in publish_job_detail_response.text

    scheduler_response = _post_console_scheduler_action(
        client,
        action="publish_due",
        config_dir=config_dir,
        database_url=database_url,
    )
    assert scheduler_response.status_code == 200
    assert captured == {
        "config_dir": config_dir,
        "database_url": database_url,
        "dry_run": True,
    }
    assert "발행 예정 처리 완료" in scheduler_response.text
    assert "드라이런이 브라우저 기본 경로로 유지되어 발행 상태 변경은 적용되지 않았습니다." in scheduler_response.text


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'console.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _post_console_review_action(
    client: TestClient,
    *,
    draft_id: int,
    database_url: str,
    action: str,
    reviewer: str | None = None,
    config_dir: Path | None = None,
    reason: str | None = None,
    body: str | None = None,
    scheduled_for: str | None = None,
):
    data = {"action": action}
    if reviewer is not None:
        data["reviewer"] = reviewer
    if reason is not None:
        data["reason"] = reason
    if body is not None:
        data["body"] = body
    if scheduled_for is not None:
        data["scheduled_for"] = scheduled_for

    params = {"database_url": database_url}
    if config_dir is not None:
        params["config_dir"] = str(config_dir)

    return client.post(
        f"/console/reviews/{draft_id}",
        params=params,
        data=data,
    )


def _post_console_scheduler_action(
    client: TestClient,
    *,
    action: str,
    config_dir: str,
    database_url: str,
    live: bool = False,
):
    data = {"action": action}
    if live:
        data["live"] = "true"

    return client.post(
        "/console/scheduler",
        params={
            "config_dir": config_dir,
            "database_url": database_url,
        },
        data=data,
    )


def _create_pending_review_draft(
    session,
    *,
    variant_index: int,
    created_at: datetime,
    brief_title: str,
    body: str,
    draft_state: DraftVariantState = DraftVariantState.PENDING_REVIEW,
) -> DraftVariant:
    source_number = next(_DRAFT_SOURCE_COUNTER)
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"draft-entry-{source_number}",
            source_url=f"https://example.com/review-draft/{source_number}",
            title=f"Review draft source {source_number}",
        )
    )
    brief = ContentBriefRepository(session).add(
        ContentBrief(
            source_item_id=source_item.id,
            account_key="ai_tools_daily",
            title=brief_title,
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
        )
    )
    if draft_state is DraftVariantState.APPROVED:
        repository.transition_state(draft, DraftVariantState.APPROVED)
    return draft


def _create_review_detail_draft(
    session,
    *,
    account_key: str = "ai_tools_daily",
    channel: str = "x",
    brief_title: str = "Brief for draft",
    variant_index: int,
    draft_state: DraftVariantState = DraftVariantState.PENDING_REVIEW,
    created_at: datetime,
    body: str = "Useful AI automation workflows for operators",
    include_provenance: bool = False,
    include_article_enrichment: bool = False,
) -> DraftVariant:
    source_number = next(_DRAFT_SOURCE_COUNTER)
    source_url = f"https://example.com/drafts/{source_number}"
    article_url = f"https://example.com/articles/{source_number}" if include_article_enrichment else None
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"draft-entry-{source_number}",
            source_url=source_url,
            title=f"Draft source {source_number}",
            summary="RSS summary for review" if include_article_enrichment else None,
            published_at=datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)
            if include_article_enrichment
            else None,
            require_attribution=include_article_enrichment,
        )
    )
    if include_article_enrichment:
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=source_item.id,
                source_name="AI Tools Daily",
                article_url=article_url,
                published_at=datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc),
                discovered_at=datetime(2026, 3, 18, 9, 1, tzinfo=timezone.utc),
                regenerated_summary="Regenerated article summary for operators",
                regenerated_key_points=["Detail point one", "Detail point two"],
                classification="analysis",
            )
        )
    if article_url is not None:
        body = body.format(article_url=article_url)
    body = body.format(source_url=source_url)
    brief = ContentBriefRepository(session).add(
        ContentBrief(
            source_item_id=source_item.id,
            account_key=account_key,
            title=brief_title,
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
            channel=channel,
            variant_index=variant_index,
            body=body,
            created_at=created_at,
            source_name="AI Tools Daily" if include_provenance else None,
            source_url=source_url if include_provenance else None,
            article_url=(article_url or source_url) if include_provenance else None,
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


def _create_publish_job(
    session,
    *,
    account_key: str = "ai_tools_daily",
    channel: str = "x",
    brief_title: str = "Brief for publish job",
    variant_index: int,
    created_at: datetime,
    scheduled_for: datetime,
    state: PublishJobState = PublishJobState.SCHEDULED,
    last_error: str | None = None,
    external_post_id: str | None = None,
    include_provenance: bool = False,
    log_events: list[tuple[str, str, dict | None]] | None = None,
) -> PublishJob:
    draft = _create_review_detail_draft(
        session,
        account_key=account_key,
        channel=channel,
        brief_title=brief_title,
        variant_index=variant_index,
        draft_state=DraftVariantState.APPROVED,
        created_at=created_at,
        include_provenance=include_provenance,
    )
    jobs = PublishJobRepository(session)
    logs = PublishLogRepository(session)
    job = jobs.add(
        PublishJob(
            draft_variant=draft,
            channel=channel,
            idempotency_key=f"publish-job-{next(_DRAFT_SOURCE_COUNTER)}",
            scheduled_for=scheduled_for,
            created_at=created_at,
        )
    )
    if state is PublishJobState.PUBLISHED:
        jobs.transition_state(job, PublishJobState.PUBLISHING)
        jobs.transition_state(
            job,
            PublishJobState.PUBLISHED,
            external_post_id=external_post_id or "external-post",
            occurred_at=scheduled_for,
        )
    elif state is PublishJobState.FAILED:
        jobs.transition_state(job, PublishJobState.PUBLISHING)
        jobs.transition_state(
            job,
            PublishJobState.FAILED,
            last_error=last_error or "publish failed",
            occurred_at=scheduled_for,
        )
    elif state is PublishJobState.PUBLISHING:
        jobs.transition_state(job, PublishJobState.PUBLISHING)
    elif state is PublishJobState.CANCELLED:
        jobs.transition_state(job, PublishJobState.CANCELLED, occurred_at=scheduled_for)

    for event_type, message, payload in log_events or []:
        logs.record(
            job,
            event_type=event_type,
            message=message,
            payload=payload,
        )
    return job


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
                  window_minutes: 0
                  jitter_minutes: 0
                  min_gap_minutes: 0
                  backlog_target: 1
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
            url: https://example.com/feed.xml

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """,
    )


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
