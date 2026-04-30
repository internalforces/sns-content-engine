"""Tests for the FastAPI operator routes."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from textwrap import dedent

from fastapi.testclient import TestClient

from app.api import create_app
from app.scheduler import (
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
    PublishJob,
    PublishJobRepository,
    PublishLogRepository,
    PublishJobState,
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
from app.workflows.review_queue import (
    approve_draft,
    complete_manual_publish_handoff,
    edit_draft,
    schedule_draft,
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


def test_publish_jobs_endpoint_returns_filtered_rows(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        scheduled_draft = _create_draft_variant(
            session,
            account_key="ai_tools_daily",
            brief_title="Queued AI brief",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
        )
        failed_draft = _create_draft_variant(
            session,
            account_key="ai_tools_daily",
            brief_title="Failed AI brief",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 5, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
        )
        published_draft = _create_draft_variant(
            session,
            account_key="finance_news_daily",
            channel="linkedin",
            brief_title="Published finance brief",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 10, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
        )

        jobs = PublishJobRepository(session)
        scheduled_job = jobs.add(
            PublishJob(
                draft_variant=scheduled_draft,
                channel="x",
                idempotency_key="scheduled-job",
                scheduled_for=datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            )
        )
        failed_job = jobs.add(
            PublishJob(
                draft_variant=failed_draft,
                channel="x",
                idempotency_key="failed-job",
                scheduled_for=datetime(2026, 3, 18, 12, 30, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 18, 9, 5, tzinfo=timezone.utc),
            )
        )
        jobs.transition_state(failed_job, PublishJobState.FAILED, last_error="publisher rejected draft")
        published_job = jobs.add(
            PublishJob(
                draft_variant=published_draft,
                channel="linkedin",
                idempotency_key="published-job",
                scheduled_for=datetime(2026, 3, 18, 13, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 18, 9, 10, tzinfo=timezone.utc),
            )
        )
        jobs.transition_state(published_job, PublishJobState.PUBLISHING)
        jobs.transition_state(
            published_job,
            PublishJobState.PUBLISHED,
            external_post_id="li:123",
            occurred_at=datetime(2026, 3, 18, 13, 5, tzinfo=timezone.utc),
        )

    client = TestClient(create_app())

    filtered_response = client.get(
        "/publish-jobs",
        params={
            "database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
            "account_key": "ai_tools_daily",
            "channel": "x",
            "limit": 1,
        },
    )

    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert [job["publish_job_id"] for job in filtered_payload["jobs"]] == [failed_job.id]
    assert filtered_payload["jobs"][0]["draft_id"] == failed_draft.id
    assert filtered_payload["jobs"][0]["account_key"] == "ai_tools_daily"
    assert filtered_payload["jobs"][0]["channel"] == "x"
    assert filtered_payload["jobs"][0]["state"] == "failed"
    assert filtered_payload["jobs"][0]["last_error"] == "publisher rejected draft"
    assert filtered_payload["jobs"][0]["variant_index"] == 0
    assert filtered_payload["jobs"][0]["draft_state"] == "approved"
    assert filtered_payload["jobs"][0]["brief_title"] == "Failed AI brief"
    assert filtered_payload["jobs"][0]["source_title"].startswith("Draft source ")

    published_response = client.get(
        "/publish-jobs",
        params={
            "database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
            "state": "published",
        },
    )

    assert published_response.status_code == 200
    published_payload = published_response.json()
    assert [job["publish_job_id"] for job in published_payload["jobs"]] == [published_job.id]
    assert published_payload["jobs"][0]["account_key"] == "finance_news_daily"
    assert published_payload["jobs"][0]["channel"] == "linkedin"
    assert published_payload["jobs"][0]["state"] == "published"
    assert published_payload["jobs"][0]["external_post_id"] == "li:123"
    assert published_payload["jobs"][0]["published_at"] == "2026-03-18T13:05:00+00:00"
    assert published_payload["jobs"][0]["brief_title"] == "Published finance brief"
    assert scheduled_job.id not in [job["publish_job_id"] for job in published_payload["jobs"]]


def test_publish_jobs_endpoint_returns_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/publish-jobs",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    assert response.json() == {"jobs": []}


def test_publish_job_detail_endpoint_returns_published_job_timeline(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
            include_provenance=True,
        )
        jobs = PublishJobRepository(session)
        logs = PublishLogRepository(session)
        job = jobs.add(
            PublishJob(
                draft_variant=draft,
                channel="x",
                idempotency_key="detail-published-job",
                scheduled_for=datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            )
        )
        logs.record(
            job,
            event_type="scheduled",
            message="publish job queued for operator review",
            payload={"scheduled_for": "2026-03-18T12:00:00+00:00"},
        )
        jobs.transition_state(job, PublishJobState.PUBLISHING)
        logs.record(
            job,
            event_type="publishing",
            message="publisher execution started",
            payload={"attempt_count": 1, "channel": "x"},
        )
        jobs.transition_state(
            job,
            PublishJobState.PUBLISHED,
            external_post_id="tweet:detail-1",
            occurred_at=datetime(2026, 3, 18, 12, 5, tzinfo=timezone.utc),
        )
        logs.record(
            job,
            event_type="published",
            message="publish job completed successfully",
            payload={"external_post_id": "tweet:detail-1"},
        )

    client = TestClient(create_app())
    response = client.get(
        f"/publish-jobs/{job.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["publish_job_id"] == job.id
    assert payload["account_key"] == "ai_tools_daily"
    assert payload["channel"] == "x"
    assert payload["state"] == "published"
    assert payload["scheduled_for"] == "2026-03-18T12:00:00+00:00"
    assert payload["published_at"] == "2026-03-18T12:05:00+00:00"
    assert payload["attempt_count"] == 1
    assert payload["external_post_id"] == "tweet:detail-1"
    assert payload["last_error"] is None
    assert payload["draft"]["draft_id"] == draft.id
    assert payload["draft"]["variant_index"] == 0
    assert payload["draft"]["draft_state"] == "approved"
    assert payload["provenance"]["source_name"] == "AI Tools Daily"
    assert payload["brief"]["title"] == "Brief for draft"
    assert payload["source_item"]["title"].startswith("Draft source ")
    assert [entry["event_type"] for entry in payload["publish_logs"]] == [
        "scheduled",
        "publishing",
        "published",
    ]
    assert payload["publish_logs"][2]["payload"] == {"external_post_id": "tweet:detail-1"}


def test_publish_job_detail_endpoint_returns_failed_job_context(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 15, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
        )
        jobs = PublishJobRepository(session)
        logs = PublishLogRepository(session)
        job = jobs.add(
            PublishJob(
                draft_variant=draft,
                channel="x",
                idempotency_key="detail-failed-job",
                scheduled_for=datetime(2026, 3, 18, 12, 30, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 18, 9, 15, tzinfo=timezone.utc),
            )
        )
        jobs.transition_state(job, PublishJobState.PUBLISHING)
        logs.record(
            job,
            event_type="publishing",
            message="publisher execution started",
            payload={"attempt_count": 1},
        )
        jobs.transition_state(
            job,
            PublishJobState.FAILED,
            last_error="missing access token",
            occurred_at=datetime(2026, 3, 18, 12, 31, tzinfo=timezone.utc),
        )
        logs.record(
            job,
            event_type="failed",
            message="publish job failed: missing access token",
            payload={"error_message": "missing access token", "status": "failed"},
        )

    client = TestClient(create_app())
    response = client.get(
        f"/publish-jobs/{job.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["publish_job_id"] == job.id
    assert payload["state"] == "failed"
    assert payload["attempt_count"] == 1
    assert payload["external_post_id"] is None
    assert payload["last_error"] == "missing access token"
    assert payload["draft"]["draft_state"] == "approved"
    assert [entry["event_type"] for entry in payload["publish_logs"]] == ["publishing", "failed"]
    assert payload["publish_logs"][1]["message"] == "publish job failed: missing access token"


def test_publish_job_detail_endpoint_returns_empty_log_timeline(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 30, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
        )
        job = PublishJobRepository(session).add(
            PublishJob(
                draft_variant=draft,
                channel="x",
                idempotency_key="detail-empty-log-job",
                scheduled_for=datetime(2026, 3, 18, 13, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 18, 9, 30, tzinfo=timezone.utc),
            )
        )

    client = TestClient(create_app())
    response = client.get(
        f"/publish-jobs/{job.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["publish_job_id"] == job.id
    assert payload["state"] == "scheduled"
    assert payload["publish_logs"] == []
    assert payload["last_error"] is None


def test_publish_job_detail_endpoint_returns_not_found_error(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/publish-jobs/999",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "publish_job_not_found",
        "message": "publish job 999 was not found",
    }


def test_control_plane_read_endpoints_share_consistent_linked_context(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    attributed_body_template = (
        "Useful AI automation workflows for operators via AI Tools Daily "
        "example.com {article_url}"
    )
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=attributed_body_template,
            include_provenance=True,
            include_article_enrichment=True,
        )
    attributed_body = attributed_body_template.format(article_url=draft.article_url)

    approve_draft(
        draft.id,
        reviewer="editor-a",
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
        job = PublishJobRepository(session).get(schedule_result.publish_job_id)
        assert job is not None
        PublishLogRepository(session).record(
            job,
            event_type="scheduled",
            message="publish job queued from review action",
            payload={"scheduled_for": job.scheduled_for.isoformat() if job.scheduled_for else None},
        )

    client = TestClient(create_app())
    review_response = client.get(
        f"/reviews/{draft.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )
    publish_list_response = client.get(
        "/publish-jobs",
        params={
            "database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
            "state": "scheduled",
            "account_key": "ai_tools_daily",
        },
    )
    publish_detail_response = client.get(
        f"/publish-jobs/{schedule_result.publish_job_id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert review_response.status_code == 200
    assert publish_list_response.status_code == 200
    assert publish_detail_response.status_code == 200

    review_payload = review_response.json()
    publish_list_payload = publish_list_response.json()
    publish_detail_payload = publish_detail_response.json()

    assert [action["action_type"] for action in review_payload["review_actions"]] == [
        "approve",
        "schedule",
    ]
    assert len(publish_list_payload["jobs"]) == 1
    publish_row = publish_list_payload["jobs"][0]

    assert review_payload["draft_id"] == draft.id
    assert publish_row["draft_id"] == draft.id
    assert publish_detail_payload["draft"]["draft_id"] == draft.id
    assert review_payload["draft_state"] == "approved"
    assert publish_row["draft_state"] == "approved"
    assert publish_detail_payload["draft"]["draft_state"] == "approved"
    assert publish_row["publish_job_id"] == schedule_result.publish_job_id
    assert publish_detail_payload["publish_job_id"] == schedule_result.publish_job_id
    assert publish_row["state"] == "scheduled"
    assert publish_detail_payload["state"] == "scheduled"
    assert review_payload["brief"]["title"] == publish_row["brief_title"] == publish_detail_payload["brief"]["title"]
    assert (
        review_payload["source_item"]["title"]
        == publish_row["source_title"]
        == publish_detail_payload["source_item"]["title"]
    )
    assert review_payload["provenance"]["source_url"] == publish_detail_payload["provenance"]["source_url"]
    assert review_payload["provenance"]["article_url"] == publish_detail_payload["provenance"]["article_url"]
    assert review_payload["article_enrichment"]["article_url"] == review_payload["source_item"]["source_url"].replace(
        "/drafts/",
        "/articles/",
    )
    assert [entry["event_type"] for entry in publish_detail_payload["publish_logs"]] == ["scheduled"]

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft.id)
        stored_job = PublishJobRepository(session).get(schedule_result.publish_job_id)
        stored_logs = PublishLogRepository(session).list()

    assert stored_draft is not None
    assert stored_job is not None
    assert stored_draft.state is DraftVariantState.APPROVED
    assert stored_job.state is PublishJobState.SCHEDULED
    assert stored_job.attempt_count == 0
    assert [log.event_type for log in stored_logs] == ["scheduled"]


def test_scheduler_discover_endpoint_returns_summary_payload() -> None:
    captured: dict[str, object] = {}

    def stub_scheduler_discover(*, config_dir: str) -> SchedulerDiscoverResult:
        captured["config_dir"] = config_dir
        return SchedulerDiscoverResult(
            discovered_count=3,
            processed_sources=("ai_tools_rss", "manual_csv"),
            failure_messages=("manual_csv: feed parse failed",),
        )

    client = TestClient(create_app(scheduler_discover_runner=stub_scheduler_discover))
    response = client.post(
        "/scheduler/discover",
        json={"config_dir": "/tmp/operator-config"},
    )

    assert response.status_code == 200
    assert captured == {"config_dir": "/tmp/operator-config"}
    assert response.json() == {
        "discovered_count": 3,
        "processed_sources": ["ai_tools_rss", "manual_csv"],
        "failure_count": 1,
        "failure_messages": ["manual_csv: feed parse failed"],
    }


def test_scheduler_backfill_endpoint_creates_jobs_from_existing_workflow(tmp_path: Path) -> None:
    _write_scheduler_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 7, 30, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
        )

    client = TestClient(create_app())
    response = client.post(
        "/scheduler/backfill",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"config_dir": str(tmp_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_channel_count"] == 1
    assert payload["created_count"] == 1
    assert payload["existing_count"] == 0
    assert payload["skipped_count"] == 0
    assert payload["outcomes"] == [
        {
            "account_key": "ai_tools_daily",
            "channel": "x",
            "backlog_target": 1,
            "existing_future_job_count": 0,
            "eligible_draft_count": 1,
            "planned_slot_count": 1,
            "created_job_ids": [1],
            "created_count": 1,
            "skipped_slot_count": 0,
        }
    ]

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session).list()
        logs = PublishLogRepository(session).list()

    assert len(jobs) == 1
    assert jobs[0].state is PublishJobState.SCHEDULED
    assert jobs[0].scheduled_for is not None
    assert jobs[0].scheduled_for.tzinfo is timezone.utc
    assert [log.event_type for log in logs] == ["scheduled"]


def test_scheduler_backfill_endpoint_includes_live_threads_when_configured(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_scheduler_project_config(tmp_path, include_threads_publisher=True)
    monkeypatch.setenv(
        "THREADS_TEST_CREDENTIALS",
        '{"access_token":"threads-user-token","threads_user_id":"threads-user-1"}',
    )
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        _create_draft_variant(
            session,
            channel="threads",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 7, 30, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
        )

    client = TestClient(create_app())
    response = client.post(
        "/scheduler/backfill",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"config_dir": str(tmp_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    threads_outcome = next(outcome for outcome in payload["outcomes"] if outcome["channel"] == "threads")
    assert threads_outcome["created_count"] == 1
    assert threads_outcome["eligible_draft_count"] == 1
    assert threads_outcome["created_job_ids"] == [1]

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session).list()

    assert len(jobs) == 1
    assert jobs[0].channel == "threads"


def test_scheduler_publish_due_endpoint_defaults_to_dry_run(tmp_path: Path) -> None:
    _write_scheduler_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 7, 45, tzinfo=timezone.utc),
            draft_state=DraftVariantState.APPROVED,
        )
        job = PublishJobRepository(session).add(
            PublishJob(
                draft_variant=draft,
                channel="x",
                idempotency_key="api-dry-run-job",
                scheduled_for=datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
            )
        )
        job_id = job.id

    client = TestClient(create_app())
    response = client.post(
        "/scheduler/publish-due",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"config_dir": str(tmp_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run"] is True
    assert payload["processed_count"] == 1
    assert payload["published_count"] == 0
    assert payload["failed_count"] == 0
    assert payload["dry_run_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["outcomes"] == [
        {
            "publish_job_id": job_id,
            "status": "dry_run",
            "state": "scheduled",
            "message": "dry-run only; no state changes were applied",
            "external_post_id": f"dry-run:{job_id}",
        }
    ]

    with session_scope(session_factory) as session:
        stored_job = PublishJobRepository(session).get(job_id)

    assert stored_job is not None
    assert stored_job.state is PublishJobState.SCHEDULED
    assert stored_job.attempt_count == 0
    assert stored_job.external_post_id is None


def test_scheduler_publish_due_endpoint_requires_explicit_live_opt_in() -> None:
    captured: dict[str, object] = {}

    def stub_publish_due_runner(
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
                    status="published",
                    state=PublishJobState.PUBLISHED,
                    message="published successfully",
                    external_post_id="tweet:42",
                ),
            ),
            dry_run=dry_run,
        )

    client = TestClient(create_app(scheduler_publish_due_runner=stub_publish_due_runner))
    response = client.post(
        "/scheduler/publish-due",
        params={"database_url": "sqlite+pysqlite:////tmp/operator.db"},
        json={"config_dir": "/tmp/operator-config", "live": True},
    )

    assert response.status_code == 200
    assert captured == {
        "config_dir": "/tmp/operator-config",
        "database_url": "sqlite+pysqlite:////tmp/operator.db",
        "dry_run": False,
    }
    assert response.json() == {
        "dry_run": False,
        "processed_count": 1,
        "published_count": 1,
        "failed_count": 0,
        "dry_run_count": 0,
        "skipped_count": 0,
        "outcomes": [
            {
                "publish_job_id": 42,
                "status": "published",
                "state": "published",
                "message": "published successfully",
                "external_post_id": "tweet:42",
            }
        ],
    }


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


def test_review_detail_endpoint_returns_full_draft_context(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            include_provenance=True,
            include_article_enrichment=True,
        )

    client = TestClient(create_app())
    response = client.get(
        f"/reviews/{draft.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_id"] == draft.id
    assert payload["account_key"] == "ai_tools_daily"
    assert payload["channel"] == "x"
    assert payload["variant_index"] == 0
    assert payload["body"] == "Useful AI automation workflows for operators"
    assert payload["draft_state"] == "pending_review"
    assert payload["rejection_reason"] is None
    assert payload["reviewed_at"] is None
    assert payload["provenance"]["source_name"] == "AI Tools Daily"
    assert payload["provenance"]["source_url"].startswith("https://example.com/drafts/")
    assert payload["provenance"]["article_url"] == payload["article_enrichment"]["article_url"]
    assert payload["provenance"]["source_published_at"] == "2026-03-17T12:00:00+00:00"
    assert payload["provenance"]["source_policy_mode"] == "reusable"
    assert payload["brief"]["brief_id"] > 0
    assert payload["brief"]["title"] == "Brief for draft"
    assert payload["brief"]["summary"] == "Summary for review"
    assert payload["brief"]["key_points"] == ["Point one"]
    assert payload["brief"]["landing_url"] == "https://gilgop.cloud/ai-tools"
    assert payload["brief"]["tags"] == ["ai"]
    assert payload["brief"]["angle"] == "topic_takeaway"
    assert payload["brief"]["language"] == "en"
    assert payload["source_item"]["source_item_id"] > 0
    assert payload["source_item"]["source_key"] == "ai_tools_rss"
    assert payload["source_item"]["external_id"].startswith("draft-entry-")
    assert payload["source_item"]["title"].startswith("Draft source ")
    assert payload["source_item"]["summary"] == "RSS summary for review"
    assert payload["source_item"]["source_url"].startswith("https://example.com/drafts/")
    assert payload["source_item"]["canonical_url"] == payload["source_item"]["source_url"]
    assert payload["source_item"]["published_at"] == "2026-03-17T12:00:00+00:00"
    assert payload["source_item"]["policy_mode"] == "reusable"
    assert payload["source_item"]["require_attribution"] is True
    assert payload["article_enrichment"]["article_enrichment_id"] > 0
    assert payload["article_enrichment"]["source_name"] == "AI Tools Daily"
    assert payload["article_enrichment"]["article_url"].startswith("https://example.com/articles/")
    assert payload["article_enrichment"]["published_at"] == "2026-03-17T12:00:00+00:00"
    assert payload["article_enrichment"]["discovered_at"] == "2026-03-18T09:01:00+00:00"
    assert payload["article_enrichment"]["regenerated_summary"] == "Regenerated article summary for operators"
    assert payload["article_enrichment"]["regenerated_key_points"] == [
        "Detail point one",
        "Detail point two",
    ]
    assert payload["article_enrichment"]["classification"] == "analysis"
    assert payload["sensitivity"] == {
        "is_high_risk": False,
        "domain": None,
        "matched_terms": [],
        "review_note": None,
        "prompt_guidance": None,
    }
    assert payload["review_actions"] == []
    assert payload["sibling_variants"] == []


def test_review_detail_endpoint_returns_sensitive_topic_context(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            brief_title="Defense ministry reports missile launch",
            brief_summary="Officials said national security agencies are reviewing the launch.",
            tags=("security", "defense"),
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )

    client = TestClient(create_app())
    response = client.get(
        f"/reviews/{draft.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    sensitivity = response.json()["sensitivity"]
    assert sensitivity["is_high_risk"] is True
    assert sensitivity["domain"] == "security"
    assert "defense" in sensitivity["matched_terms"]
    assert "Security coverage should verify attribution" in sensitivity["review_note"]


def test_review_detail_endpoint_returns_audit_history_and_sibling_variants(tmp_path: Path) -> None:
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

    edited_body = "Edited AI automation workflow summary for operators https://gilgop.cloud/ai-tools"
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
        repository.add(
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
        f"/reviews/{draft.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [action["action_type"] for action in payload["review_actions"]] == [
        "edit",
        "approve",
        "schedule",
    ]
    assert [action["reviewer"] for action in payload["review_actions"]] == [
        "editor-a",
        "editor-b",
        "scheduler-a",
    ]
    assert payload["review_actions"][0]["before_text"] == _VALID_REVIEW_DRAFT_BODY
    assert payload["review_actions"][0]["after_text"] == edited_body
    assert payload["review_actions"][0]["draft_state_before"] == "pending_review"
    assert payload["review_actions"][0]["draft_state_after"] == "pending_review"
    assert payload["review_actions"][1]["draft_state_before"] == "pending_review"
    assert payload["review_actions"][1]["draft_state_after"] == "approved"
    assert payload["review_actions"][2]["publish_job_id"] == schedule_result.publish_job_id
    assert payload["review_actions"][2]["scheduled_for"] == "2026-03-18T00:00:00+00:00"
    assert [variant["variant_index"] for variant in payload["sibling_variants"]] == [1, 2]
    assert [variant["body"] for variant in payload["sibling_variants"]] == [
        "Variant one with a shorter operator hook",
        "Variant two for deeper operator analysis",
    ]
    assert all(variant["draft_state"] == "pending_review" for variant in payload["sibling_variants"])


def test_review_detail_endpoint_returns_not_found_error(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/reviews/999",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "draft_not_found",
        "message": "draft 999 was not found",
    }


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


def test_review_approve_endpoint_returns_manual_handoff_publish_job_for_linkedin(
    tmp_path: Path,
) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="linkedin",
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
    assert payload["action_type"] == "approve"
    assert payload["draft_state"] == "approved"
    assert payload["publish_job_id"] is not None
    assert payload["scheduled_for"] is None

    detail_response = client.get(
        f"/publish-jobs/{payload['publish_job_id']}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["channel"] == "linkedin"
    assert detail_payload["scheduled_for"] is None
    assert [entry["event_type"] for entry in detail_payload["publish_logs"]] == [
        "manual_handoff_created"
    ]


def test_review_approve_endpoint_returns_no_manual_handoff_for_live_threads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_minimal_project_config(tmp_path, include_threads_publisher=True)
    monkeypatch.setenv(
        "THREADS_TEST_CREDENTIALS",
        '{"access_token":"threads-user-token","threads_user_id":"threads-user-1"}',
    )
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="threads",
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
    assert payload["action_type"] == "approve"
    assert payload["draft_state"] == "approved"
    assert payload["publish_job_id"] is None
    assert payload["scheduled_for"] is None

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session).list()

    assert jobs == []


def test_publish_job_detail_endpoint_returns_manual_publish_completion_timeline(
    tmp_path: Path,
) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="linkedin",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    approval = approve_draft(
        draft.id,
        reviewer="editor-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )
    assert approval.publish_job_id is not None

    complete_manual_publish_handoff(
        approval.publish_job_id,
        operator="publisher-a",
        external_post_id="linkedin-post-123",
        session_factory=session_factory,
    )

    client = TestClient(create_app())
    response = client.get(
        f"/publish-jobs/{approval.publish_job_id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["channel"] == "linkedin"
    assert payload["state"] == "published"
    assert payload["scheduled_for"] is None
    assert payload["external_post_id"] == "linkedin-post-123"
    assert payload["published_at"] is not None
    assert [entry["event_type"] for entry in payload["publish_logs"]] == [
        "manual_handoff_created",
        "published",
    ]
    assert payload["publish_logs"][1]["payload"] == {
        "status": "published",
        "account_key": "ai_tools_daily",
        "channel": "linkedin",
        "draft_variant_id": draft.id,
        "handoff_mode": "manual_upload",
        "operator": "publisher-a",
        "attempt_count": 1,
        "external_post_id": "linkedin-post-123",
        "last_error": None,
        "reason": None,
    }


def test_manual_publish_complete_endpoint_records_manual_handoff_outcome(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="linkedin",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    approval = approve_draft(
        draft.id,
        reviewer="editor-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )
    assert approval.publish_job_id is not None

    client = TestClient(create_app())
    response = client.post(
        f"/publish-jobs/{approval.publish_job_id}/manual/complete",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"operator": "publisher-a", "external_post_id": "linkedin-post-456"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "publish_job_id": approval.publish_job_id,
        "channel": "linkedin",
        "operator": "publisher-a",
        "previous_state": "scheduled",
        "publish_job_state": "published",
        "external_post_id": "linkedin-post-456",
        "last_error": None,
        "published_at": payload["published_at"],
    }
    assert payload["published_at"] is not None


def test_manual_publish_fail_endpoint_records_manual_handoff_failure(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="threads",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    approval = approve_draft(
        draft.id,
        reviewer="editor-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )
    assert approval.publish_job_id is not None

    client = TestClient(create_app())
    response = client.post(
        f"/publish-jobs/{approval.publish_job_id}/manual/fail",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"operator": "publisher-b", "error_message": "upload window expired"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "publish_job_id": approval.publish_job_id,
        "channel": "threads",
        "operator": "publisher-b",
        "previous_state": "scheduled",
        "publish_job_state": "failed",
        "external_post_id": None,
        "last_error": "upload window expired",
        "published_at": None,
    }


def test_manual_publish_failed_handoff_appears_in_publish_jobs_list(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="threads",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    approval = approve_draft(
        draft.id,
        reviewer="editor-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )
    assert approval.publish_job_id is not None

    client = TestClient(create_app())
    fail_response = client.post(
        f"/publish-jobs/{approval.publish_job_id}/manual/fail",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"operator": "publisher-b", "error_message": "upload window expired"},
    )

    assert fail_response.status_code == 200

    list_response = client.get(
        "/publish-jobs",
        params={
            "database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
            "state": "failed",
            "channel": "threads",
        },
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert [job["publish_job_id"] for job in payload["jobs"]] == [approval.publish_job_id]
    assert payload["jobs"][0]["draft_id"] == draft.id
    assert payload["jobs"][0]["channel"] == "threads"
    assert payload["jobs"][0]["state"] == "failed"
    assert payload["jobs"][0]["scheduled_for"] is None
    assert payload["jobs"][0]["last_error"] == "upload window expired"
    assert payload["jobs"][0]["draft_state"] == "approved"


def test_manual_publish_cancel_endpoint_records_manual_handoff_cancellation(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="linkedin",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    approval = approve_draft(
        draft.id,
        reviewer="editor-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )
    assert approval.publish_job_id is not None

    client = TestClient(create_app())
    response = client.post(
        f"/publish-jobs/{approval.publish_job_id}/manual/cancel",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"operator": "publisher-c", "reason": "campaign paused"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "publish_job_id": approval.publish_job_id,
        "channel": "linkedin",
        "operator": "publisher-c",
        "previous_state": "scheduled",
        "publish_job_state": "cancelled",
        "external_post_id": None,
        "last_error": None,
        "published_at": None,
    }


def test_manual_publish_complete_endpoint_returns_conflict_for_closed_handoff(
    tmp_path: Path,
) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="linkedin",
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=_VALID_REVIEW_DRAFT_BODY,
            include_provenance=True,
        )

    approval = approve_draft(
        draft.id,
        reviewer="editor-a",
        config_dir=tmp_path,
        session_factory=session_factory,
    )
    assert approval.publish_job_id is not None

    complete_manual_publish_handoff(
        approval.publish_job_id,
        operator="publisher-a",
        external_post_id="linkedin-post-789",
        session_factory=session_factory,
    )

    client = TestClient(create_app())
    response = client.post(
        f"/publish-jobs/{approval.publish_job_id}/manual/complete",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'api.db'}"},
        json={"operator": "publisher-a", "external_post_id": "linkedin-post-789"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "manual_publish_state_conflict"


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


def test_review_schedule_endpoint_accepts_live_threads_when_configured(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_minimal_project_config(tmp_path, include_threads_publisher=True)
    monkeypatch.setenv(
        "THREADS_TEST_CREDENTIALS",
        '{"access_token":"threads-user-token","threads_user_id":"threads-user-1"}',
    )
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            channel="threads",
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
    assert payload["action_type"] == "schedule"
    assert payload["publish_job_id"] is not None
    assert payload["scheduled_for"] == "2026-03-18T00:00:00+00:00"

    with session_scope(session_factory) as session:
        job = PublishJobRepository(session).get(payload["publish_job_id"])

    assert job is not None
    assert job.channel == "threads"
    assert job.scheduled_for == datetime(2026, 3, 18, 0, 0, tzinfo=timezone.utc)


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'api.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _write_minimal_project_config(
    path: Path,
    *,
    source_url: str = "https://gilgop.cloud/feed.xml",
    include_threads_publisher: bool = False,
) -> None:
    threads_publisher_block = ""
    if include_threads_publisher:
        threads_publisher_block = """
                publisher:
                  credential_ref: THREADS_TEST_CREDENTIALS
        """

    _write_file(
        path / "accounts.yaml",
        f"""
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
              linkedin:
                schedule:
                  cron: "0 10 * * *"
                render:
                  max_chars: 3000
                validation:
                  max_links: 1
                  banned_phrases: []
                  recent_duplicate_window_days: 7
              threads:
                schedule:
                  cron: "0 11 * * *"
                render:
                  max_chars: 10000
                validation:
                  max_links: 1
                  banned_phrases: []
                  recent_duplicate_window_days: 7
{threads_publisher_block}        """,
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


def _write_scheduler_project_config(path: Path, *, include_threads_publisher: bool = False) -> None:
    threads_channel_block = """
              threads:
                schedule:
                  cron: "0 11 * * *"
                  window_minutes: 0
                  jitter_minutes: 0
                  min_gap_minutes: 0
                  backlog_target: 1
                render:
                  max_chars: 10000
                validation:
                  max_links: 1
                  banned_phrases: []
                  recent_duplicate_window_days: 7
    """
    if include_threads_publisher:
        threads_channel_block += """
                publisher:
                  credential_ref: THREADS_TEST_CREDENTIALS
    """

    _write_file(
        path / "accounts.yaml",
        f"""
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
{threads_channel_block}        """,
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


def _create_draft_variant(
    session,
    *,
    account_key: str = "ai_tools_daily",
    channel: str = "x",
    brief_title: str = "Brief for draft",
    brief_summary: str = "Summary for review",
    tags: tuple[str, ...] = ("ai",),
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
            summary=brief_summary,
            key_points=["Point one"],
            landing_url="https://gilgop.cloud/ai-tools",
            tags=list(tags),
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
