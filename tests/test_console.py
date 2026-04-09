"""Focused tests for the server-rendered operator console shell."""

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
from app.workflows.review_queue import approve_draft, edit_draft, schedule_draft

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


def test_articles_page_renders_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/articles",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "Article Status" in response.text
    assert "Showing up to 25 recent source items in stored discovery order" in response.text
    assert "No stored article rows are available for this operator context yet." in response.text


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
    assert "Article Status" in response.text
    assert "Central bank update" in response.text
    assert "Finance Feed" in response.text
    assert "https://example.com/final/2" in response.text
    assert "Failed" in response.text
    assert "Fetch Failed / Extract Pending / Summarize Pending" in response.text
    assert "site blocked" in response.text
    assert "Operator checklist update" in response.text
    assert "Resolved article not recorded yet." in response.text


def test_pending_review_page_renders_empty_state(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())

    response = client.get(
        "/console/reviews/pending",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )

    assert response.status_code == 200
    assert "Pending Review" in response.text
    assert "Each queue row now links into one draft workspace" in response.text
    assert "No drafts are currently waiting for manual review." in response.text


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
    assert "Pending Review" in response.text
    assert f"Draft {pending_draft.id}" in response.text
    assert "Variant 0" in response.text
    assert "ai_tools_daily" in response.text
    assert "Useful AI automation workflows for operators" in response.text
    assert f'/console/reviews/{pending_draft.id}' in response.text
    assert "Hidden approved draft" not in response.text
    assert "This approved draft should not appear in the pending queue" not in response.text


def test_review_detail_page_renders_full_draft_context(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    attributed_body = "AI Tools Daily via example.com: Useful AI automation workflows for operators https://gilgop.cloud/ai-tools"
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session,
            variant_index=0,
            created_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            body=attributed_body,
            include_provenance=True,
            include_article_enrichment=True,
        )

    edited_body = "AI Tools Daily via example.com: Edited AI automation workflow summary for operators https://gilgop.cloud/ai-tools"
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
    assert f"Review Draft {draft.id}" in response.text
    assert f"Draft {draft.id}" in response.text
    assert "Brief for draft" in response.text
    assert "AI Tools Daily" in response.text
    assert "Regenerated article summary for operators" in response.text
    assert "Detail point one" in response.text
    assert "editor-a" in response.text
    assert "editor-b" in response.text
    assert "scheduler-a" in response.text
    assert attributed_body in response.text
    assert edited_body in response.text
    assert f"Publish job {schedule_result.publish_job_id}" in response.text
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
    assert "Review Draft Not Found" in response.text
    assert "draft 999 was not found" in response.text
    assert "/console/reviews/pending" in response.text


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'console.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


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
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"draft-entry-{source_number}",
            source_url=f"https://example.com/drafts/{source_number}",
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
                article_url=f"https://example.com/articles/{source_number}",
                published_at=datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc),
                discovered_at=datetime(2026, 3, 18, 9, 1, tzinfo=timezone.utc),
                regenerated_summary="Regenerated article summary for operators",
                regenerated_key_points=["Detail point one", "Detail point two"],
                classification="analysis",
            )
        )
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
