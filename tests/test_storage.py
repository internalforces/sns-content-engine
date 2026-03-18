"""Tests for the database layer and repository behavior."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from itertools import count

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    ContentBrief,
    ContentBriefRepository,
    DatabaseSchemaError,
    DraftVariant,
    DraftVariantRepository,
    DraftVariantState,
    InvalidStateTransitionError,
    ManualApprovalRequiredError,
    PipelineStage,
    PipelineRun,
    PipelineRunRepository,
    PipelineRunStage,
    PipelineRunStageRepository,
    PipelineRunStatus,
    PublishJob,
    PublishJobRepository,
    PublishJobState,
    PublishLogRepository,
    ReviewActionRepository,
    ReviewActionType,
    StageExecutionStatus,
    SourceItem,
    SourceItemRepository,
    SourceItemState,
    bootstrap_database,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)

_DRAFT_SOURCE_COUNTER = count()


@pytest.fixture
def database_url(tmp_path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'storage.db'}"


@pytest.fixture
def session_factory(database_url):
    engine = create_database_engine(database_url)
    create_all_tables(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def test_create_all_creates_expected_tables(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        create_all_tables(engine)
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert tables == {
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


def test_source_item_can_be_inserted_and_read(session_factory) -> None:
    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        item = repository.add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-1",
                source_url="https://example.com/posts/1",
                title="Useful AI tool",
                summary="A short summary",
                published_at=datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc),
                raw_payload={"author": "team"},
                state=SourceItemState.INGESTED,
            )
        )
        item_id = item.id

    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        stored_item = repository.get(item_id)

    assert stored_item is not None
    assert stored_item.source_key == "ai_tools_rss"
    assert stored_item.external_id == "entry-1"
    assert stored_item.raw_payload == {"author": "team"}
    assert stored_item.state is SourceItemState.INGESTED
    assert stored_item.published_at == datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc)
    assert stored_item.published_at.tzinfo == timezone.utc
    assert stored_item.canonical_url == "https://example.com/posts/1"
    assert stored_item.normalized_title == "useful ai tool"
    assert len(stored_item.normalized_title_hash) == 64
    assert len(stored_item.dedupe_fingerprint) == 64


def test_article_enrichment_can_be_inserted_and_read(session_factory) -> None:
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="entry-article-1",
                source_url="https://example.com/markets/1",
                title="Markets digest",
                summary="Morning summary",
            )
        )
        enrichment = ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=source_item.id,
                source_name="Example Finance",
                article_url="https://example.com/markets/1",
                published_at=datetime(2026, 3, 18, 8, 30, tzinfo=timezone.utc),
                html_content="<html><body>Stocks rose after the central bank update.</body></html>",
                article_text="Stocks rose after the central bank update.",
                regenerated_summary="Markets rose after a central bank update.",
                regenerated_key_points=[
                    "Stocks rose after the update",
                    "Investors focused on central bank comments",
                ],
                tags=["markets", "policy"],
                company_names=["Federal Reserve"],
                tickers=["SPY"],
                markets=["US"],
                classification="macro",
                html_fetch_status=StageExecutionStatus.SUCCEEDED,
                article_extract_status=StageExecutionStatus.SUCCEEDED,
                summary_regenerate_status=StageExecutionStatus.SUCCEEDED,
                last_stage=PipelineStage.SUMMARY_REGENERATE,
                metadata_json={"rss_description": "Ignore this in favor of regenerated summary"},
            )
        )
        enrichment_id = enrichment.id

    with session_scope(session_factory) as session:
        stored = ArticleEnrichmentRepository(session).get(enrichment_id)

    assert stored is not None
    assert stored.source_name == "Example Finance"
    assert stored.article_url == "https://example.com/markets/1"
    assert stored.regenerated_summary == "Markets rose after a central bank update."
    assert stored.regenerated_key_points == [
        "Stocks rose after the update",
        "Investors focused on central bank comments",
    ]
    assert stored.classification == "macro"
    assert stored.html_fetch_status is StageExecutionStatus.SUCCEEDED
    assert stored.summary_regenerate_status is StageExecutionStatus.SUCCEEDED
    assert stored.last_stage is PipelineStage.SUMMARY_REGENERATE
    assert stored.metadata_json == {"rss_description": "Ignore this in favor of regenerated summary"}


def test_article_enrichment_get_or_create_is_idempotent(session_factory) -> None:
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="entry-article-2",
                source_url="https://example.com/markets/2",
                title="Second markets digest",
            )
        )
        repository = ArticleEnrichmentRepository(session)
        first, was_created = repository.get_or_create(
            ArticleEnrichment(
                source_item_id=source_item.id,
                article_url="https://example.com/markets/2",
                source_name="Example Finance",
            )
        )
        second, was_created_again = repository.get_or_create(
            ArticleEnrichment(
                source_item_id=source_item.id,
                article_url="https://example.com/markets/2?duplicate=1",
                source_name="Changed source name",
            )
        )

    assert was_created is True
    assert was_created_again is False
    assert second.id == first.id
    assert second.article_url == "https://example.com/markets/2"


def test_pipeline_run_and_stage_summaries_can_be_inserted_and_read(session_factory) -> None:
    with session_scope(session_factory) as session:
        run = PipelineRunRepository(session).add(
            PipelineRun(
                workflow_name="run_local_finance",
                trigger_mode="manual_local",
                status=PipelineRunStatus.PARTIAL,
                completed_at=datetime(2026, 3, 18, 9, 15, tzinfo=timezone.utc),
                source_count=2,
                discovered_count=8,
                saved_count=5,
                enriched_count=4,
                summarized_count=3,
                brief_count=3,
                draft_count=3,
                failure_count=1,
                latest_error_code="extract_failed",
                latest_error_message="기사 본문을 읽지 못했어요",
                summary_json={"notes": ["one article failed extraction"]},
            )
        )
        PipelineRunStageRepository(session).add(
            PipelineRunStage(
                pipeline_run_id=run.id,
                stage=PipelineStage.ARTICLE_EXTRACT,
                status=StageExecutionStatus.FAILED,
                item_count=5,
                success_count=4,
                failure_count=1,
                latest_error_code="extract_failed",
                latest_error_message="기사 본문을 읽지 못했어요",
                summary_json={"failed_item_ids": [12]},
            )
        )
        run_id = run.id

    with session_scope(session_factory) as session:
        stored_run = PipelineRunRepository(session).get(run_id)
        stored_stage_rows = PipelineRunStageRepository(session).list_for_run(run_id)

    assert stored_run is not None
    assert stored_run.workflow_name == "run_local_finance"
    assert stored_run.status is PipelineRunStatus.PARTIAL
    assert stored_run.failure_count == 1
    assert stored_run.latest_error_message == "기사 본문을 읽지 못했어요"
    assert len(stored_stage_rows) == 1
    assert stored_stage_rows[0].stage is PipelineStage.ARTICLE_EXTRACT
    assert stored_stage_rows[0].status is StageExecutionStatus.FAILED
    assert stored_stage_rows[0].summary_json == {"failed_item_ids": [12]}


def test_pipeline_run_stage_get_or_create_is_idempotent(session_factory) -> None:
    with session_scope(session_factory) as session:
        run = PipelineRunRepository(session).add(
            PipelineRun(workflow_name="run_local_finance")
        )
        repository = PipelineRunStageRepository(session)
        first, was_created = repository.get_or_create(
            PipelineRunStage(
                pipeline_run_id=run.id,
                stage=PipelineStage.HTML_FETCH,
                status=StageExecutionStatus.SUCCEEDED,
                item_count=3,
                success_count=3,
            )
        )
        second, was_created_again = repository.get_or_create(
            PipelineRunStage(
                pipeline_run_id=run.id,
                stage=PipelineStage.HTML_FETCH,
                status=StageExecutionStatus.FAILED,
                item_count=9,
                failure_count=9,
            )
        )

    assert was_created is True
    assert was_created_again is False
    assert second.id == first.id
    assert second.status is StageExecutionStatus.SUCCEEDED


def test_source_item_get_or_create_is_idempotent(session_factory) -> None:
    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        first_item, was_created = repository.get_or_create(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-idempotent",
                source_url="https://example.com/posts/idempotent",
                title="Original title",
            )
        )
        second_item, was_created_again = repository.get_or_create(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-idempotent",
                source_url="https://example.com/posts/idempotent-v2",
                title="Changed title should not replace original row",
            )
        )

    assert was_created is True
    assert was_created_again is False
    assert second_item.id == first_item.id
    assert second_item.title == "Original title"


def test_source_item_duplicate_lookup_supports_canonical_url_and_title_hash(session_factory) -> None:
    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        created = repository.add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-lookup",
                source_url="https://example.com/posts/lookup?utm_source=x",
                title="AI Tool Launch",
                summary="A short summary",
            )
        )

    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        by_url = repository.get_by_canonical_url("https://example.com/posts/lookup")
        by_title_hash = repository.get_by_normalized_title_hash(created.normalized_title_hash)

    assert by_url is not None
    assert by_url.id == created.id
    assert by_title_hash is not None
    assert by_title_hash.id == created.id


def test_source_item_duplicate_canonical_url_is_rejected(session_factory) -> None:
    with session_scope(session_factory) as session:
        SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-a",
                source_url="https://example.com/posts/same",
                title="First title",
            )
        )

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            SourceItemRepository(session).add(
                SourceItem(
                    source_key="ai_tools_manual",
                    external_id="entry-b",
                    source_url="https://example.com/posts/same?utm_source=x",
                    title="Second title",
                )
            )


def test_source_item_duplicate_normalized_title_hash_is_rejected(session_factory) -> None:
    with session_scope(session_factory) as session:
        SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-title-a",
                source_url="https://example.com/posts/title-a",
                title="AI Tool Launch",
            )
        )

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            SourceItemRepository(session).add(
                SourceItem(
                    source_key="ai_tools_manual",
                    external_id="entry-title-b",
                    source_url="https://example.com/posts/title-b",
                    title="AI   Tool: Launch!",
                )
            )


def test_source_item_recent_fingerprint_lookup_honors_window_cutoff(session_factory) -> None:
    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        repository.add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-old",
                source_url="https://example.com/posts/old",
                title="Shared Summary Title",
                summary="Same text",
                created_at=datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc),
            )
        )
        recent = repository.add(
            SourceItem(
                source_key="ai_tools_manual",
                external_id="entry-recent",
                source_url="https://example.com/posts/recent",
                title="Title Shared Summary",
                summary="Same text",
                created_at=datetime(2026, 3, 15, 9, 0, tzinfo=timezone.utc),
            )
        )
        fingerprint = recent.dedupe_fingerprint

    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        match = repository.get_recent_by_dedupe_fingerprint(
            fingerprint,
            created_since=datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc),
        )

    assert match is not None
    assert match.id == recent.id


def test_source_item_duplicate_identity_is_rejected(session_factory) -> None:
    with session_scope(session_factory) as session:
        SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-duplicate",
                source_url="https://example.com/posts/duplicate",
                title="First version",
            )
        )

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            SourceItemRepository(session).add(
                SourceItem(
                    source_key="ai_tools_rss",
                    external_id="entry-duplicate",
                    source_url="https://example.com/posts/duplicate-v2",
                    title="Second version",
                )
            )


def test_content_brief_relationship_and_publish_logs_are_persisted(session_factory) -> None:
    with session_scope(session_factory) as session:
        source_items = SourceItemRepository(session)
        briefs = ContentBriefRepository(session)
        drafts = DraftVariantRepository(session)
        jobs = PublishJobRepository(session)
        logs = PublishLogRepository(session)

        source_item = source_items.add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-2",
                source_url="https://example.com/posts/2",
                title="Another tool",
                summary="Another summary",
                raw_payload={"kind": "rss"},
                state=SourceItemState.BRIEF_CREATED,
            )
        )
        brief = briefs.add(
            ContentBrief(
                source_item=source_item,
                account_key="ai_tools_daily",
                title="AI workflow brief",
                summary="Summarized brief",
                key_points=["AI workflow brief", "Key supporting point"],
                landing_url="https://gilgop.cloud/ai-tools",
                tags=["ai", "workflow"],
                angle="topic_takeaway",
                language="en",
            )
        )
        draft = drafts.add(
            DraftVariant(
                content_brief=brief,
                channel="x",
                variant_index=0,
                body="A concise X draft",
            )
        )
        drafts.transition_state(draft, DraftVariantState.APPROVED)
        job = jobs.add(
            PublishJob(
                draft_variant=draft,
                channel="x",
                scheduled_for=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
            )
        )
        log = logs.record(
            job,
            event_type="scheduled",
            message="Publish job created",
            payload={"source": "manual"},
        )
        brief_id = brief.id
        job_id = job.id
        log_id = log.id

    with session_scope(session_factory) as session:
        brief = ContentBriefRepository(session).get(brief_id)
        stored_logs = PublishLogRepository(session).list_for_job(job_id)
        stored_log = PublishLogRepository(session).get(log_id)
        assert brief is not None
        assert brief.source_item is not None
        assert brief.source_item.external_id == "entry-2"
        assert brief.key_points == ["AI workflow brief", "Key supporting point"]
        assert brief.tags == ["ai", "workflow"]
        assert brief.angle == "topic_takeaway"
        assert brief.language == "en"
        assert len(stored_logs) == 1
        assert stored_logs[0].event_type == "scheduled"
        assert stored_log is not None
        assert stored_log.payload == {"source": "manual"}


def test_content_brief_get_or_create_is_idempotent(session_factory) -> None:
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="brief-idempotent",
                source_url="https://example.com/posts/brief-idempotent",
                title="Idempotent brief source",
            )
        )
        repository = ContentBriefRepository(session)
        first_brief, was_created = repository.get_or_create(
            ContentBrief(
                source_item_id=source_item.id,
                account_key="ai_tools_daily",
                title="Stored title",
                summary="Stored summary",
                key_points=["Stored title"],
                landing_url="https://gilgop.cloud/ai-tools",
                tags=["ai"],
                angle="topic_takeaway",
                language="en",
            )
        )
        second_brief, was_created_again = repository.get_or_create(
            ContentBrief(
                source_item_id=source_item.id,
                account_key="ai_tools_daily",
                title="Changed title should not replace the original row",
                summary="Changed summary",
                key_points=["Changed title"],
                landing_url="https://gilgop.cloud/other",
                tags=["automation"],
                angle="product_update",
                language="en",
            )
        )

    assert was_created is True
    assert was_created_again is False
    assert second_brief.id == first_brief.id
    assert second_brief.title == "Stored title"


def test_content_brief_get_or_create_recovers_from_integrity_error() -> None:
    existing = ContentBrief(
        id=99,
        source_item_id=42,
        account_key="ai_tools_daily",
        title="Stored title",
        key_points=["Stored title"],
        landing_url="https://gilgop.cloud/ai-tools",
        tags=["ai"],
        angle="topic_takeaway",
        language="en",
    )
    session = _IntegrityErrorRecoveringSession(existing)
    repository = ContentBriefRepository(session)

    brief, was_created = repository.get_or_create(
        ContentBrief(
            source_item_id=42,
            account_key="ai_tools_daily",
            title="Racing insert",
            key_points=["Racing insert"],
            landing_url="https://gilgop.cloud/ai-tools",
            tags=["ai"],
            angle="topic_takeaway",
            language="en",
        )
    )

    assert was_created is False
    assert brief is existing
    assert session.scalar_call_count == 2
    assert session.flush_call_count == 1


def test_content_brief_duplicate_source_account_is_rejected(session_factory) -> None:
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="brief-duplicate",
                source_url="https://example.com/posts/brief-duplicate",
                title="Duplicate brief source",
            )
        )
        ContentBriefRepository(session).add(
            ContentBrief(
                source_item_id=source_item.id,
                account_key="ai_tools_daily",
                title="First brief",
                key_points=["First brief"],
                landing_url="https://gilgop.cloud/ai-tools",
                tags=["ai"],
                angle="topic_takeaway",
                language="en",
            )
        )

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            ContentBriefRepository(session).add(
                ContentBrief(
                    source_item_id=source_item.id,
                    account_key="ai_tools_daily",
                    title="Second brief",
                    key_points=["Second brief"],
                    landing_url="https://gilgop.cloud/ai-tools",
                    tags=["ai"],
                    angle="topic_takeaway",
                    language="en",
                )
            )


def test_draft_variant_state_transitions_are_enforced(session_factory) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session)
        repository = DraftVariantRepository(session)
        repository.transition_state(draft, DraftVariantState.APPROVED)
        draft_id = draft.id

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft_id)

    assert stored_draft is not None
    assert stored_draft.state is DraftVariantState.APPROVED
    assert stored_draft.reviewed_at is not None
    assert stored_draft.rejection_reason is None

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft_id)
        assert stored_draft is not None
        with pytest.raises(InvalidStateTransitionError):
            DraftVariantRepository(session).transition_state(
                stored_draft,
                DraftVariantState.REJECTED,
                rejection_reason="Already approved",
            )


def test_draft_variant_get_or_create_is_idempotent(session_factory) -> None:
    with session_scope(session_factory) as session:
        brief = _create_content_brief_for_draft(session)
        repository = DraftVariantRepository(session)
        first_draft, was_created = repository.get_or_create(
            DraftVariant(
                content_brief_id=brief.id,
                channel="x",
                variant_index=0,
                body="Stored draft text",
            )
        )
        second_draft, was_created_again = repository.get_or_create(
            DraftVariant(
                content_brief_id=brief.id,
                channel="x",
                variant_index=0,
                body="Changed draft text should not replace the original row",
            )
        )

    assert was_created is True
    assert was_created_again is False
    assert second_draft.id == first_draft.id
    assert second_draft.body == "Stored draft text"


def test_draft_variant_get_or_create_recovers_from_integrity_error() -> None:
    existing = DraftVariant(
        id=99,
        content_brief_id=42,
        channel="x",
        variant_index=1,
        body="Stored draft",
    )
    session = _DraftIntegrityErrorRecoveringSession(existing)
    repository = DraftVariantRepository(session)

    draft, was_created = repository.get_or_create(
        DraftVariant(
            content_brief_id=42,
            channel="x",
            variant_index=1,
            body="Racing draft",
        )
    )

    assert was_created is False
    assert draft is existing
    assert session.scalar_call_count == 2
    assert session.flush_call_count == 1


def test_draft_variant_duplicate_identity_is_rejected(session_factory) -> None:
    with session_scope(session_factory) as session:
        brief = _create_content_brief_for_draft(session)
        repository = DraftVariantRepository(session)
        repository.add(
            DraftVariant(
                content_brief_id=brief.id,
                channel="x",
                variant_index=0,
                body="First stored draft",
            )
        )

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            DraftVariantRepository(session).add(
                DraftVariant(
                    content_brief_id=brief.id,
                    channel="x",
                    variant_index=0,
                    body="Duplicate stored draft",
                )
            )


def test_draft_variant_list_recent_by_account_and_channel_filters_scope(session_factory) -> None:
    now = datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)

    with session_scope(session_factory) as session:
        repository = DraftVariantRepository(session)
        included = _create_draft_variant(
            session,
            body="Included recent draft",
            created_at=now - timedelta(days=2),
        )
        excluded_self = _create_draft_variant(
            session,
            body="Excluded self draft",
            created_at=now - timedelta(days=1),
        )
        _create_draft_variant(
            session,
            channel="threads",
            body="Different channel draft",
            created_at=now - timedelta(days=1),
        )
        _create_draft_variant(
            session,
            account_key="finance_news_daily",
            body="Different account draft",
            created_at=now - timedelta(days=1),
        )
        _create_draft_variant(
            session,
            draft_state=DraftVariantState.REJECTED,
            body="Rejected draft",
            created_at=now - timedelta(days=1),
        )
        _create_draft_variant(
            session,
            body="Stale draft",
            created_at=now - timedelta(days=10),
        )

        recent_drafts = repository.list_recent_by_account_and_channel(
            "ai_tools_daily",
            "x",
            created_since=now - timedelta(days=7),
            exclude_draft_id=excluded_self.id,
        )

    assert [draft.id for draft in recent_drafts] == [included.id]


def test_publish_job_state_transitions_are_enforced(session_factory) -> None:
    with session_scope(session_factory) as session:
        job = _create_publish_job(session, draft_state=DraftVariantState.APPROVED)
        repository = PublishJobRepository(session)
        repository.transition_state(job, PublishJobState.PUBLISHING)
        repository.transition_state(
            job,
            PublishJobState.PUBLISHED,
            external_post_id="tweet-123",
        )
        job_id = job.id

    with session_scope(session_factory) as session:
        stored_job = PublishJobRepository(session).get(job_id)

    assert stored_job is not None
    assert stored_job.state is PublishJobState.PUBLISHED
    assert stored_job.attempt_count == 1
    assert stored_job.external_post_id == "tweet-123"
    assert stored_job.idempotency_key
    assert stored_job.published_at is not None

    with session_scope(session_factory) as session:
        invalid_job = _create_publish_job(session, draft_state=DraftVariantState.APPROVED)
        with pytest.raises(InvalidStateTransitionError):
            PublishJobRepository(session).transition_state(invalid_job, PublishJobState.PUBLISHED)


def test_publish_job_requires_manual_approval_before_creation(session_factory) -> None:
    with pytest.raises(ManualApprovalRequiredError):
        with session_scope(session_factory) as session:
            pending_draft = _create_draft_variant(session)
            PublishJobRepository(session).add(
                PublishJob(
                    draft_variant=pending_draft,
                    channel="x",
                    idempotency_key="pending-draft-job",
                    scheduled_for=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
                )
            )

    with pytest.raises(ManualApprovalRequiredError):
        with session_scope(session_factory) as session:
            rejected_draft = _create_draft_variant(session, draft_state=DraftVariantState.REJECTED)
            PublishJobRepository(session).add(
                PublishJob(
                    draft_variant=rejected_draft,
                    channel="x",
                    idempotency_key="rejected-draft-job",
                    scheduled_for=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
                )
            )


def test_publish_job_forward_transitions_recheck_manual_approval(session_factory) -> None:
    with session_scope(session_factory) as session:
        job = _create_publish_job(session, draft_state=DraftVariantState.APPROVED)
        job_id = job.id

    with session_scope(session_factory) as session:
        stored_job = PublishJobRepository(session).get(job_id)
        assert stored_job is not None
        stored_job.draft_variant.state = DraftVariantState.REJECTED

        with pytest.raises(ManualApprovalRequiredError):
            PublishJobRepository(session).transition_state(stored_job, PublishJobState.PUBLISHING)


def test_review_action_repository_records_and_lists_for_draft(session_factory) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session)
        repository = ReviewActionRepository(session)
        action = repository.record(
            draft=draft,
            action_type=ReviewActionType.EDIT,
            reviewer="editor-a",
            before_text="Draft text",
            after_text="Updated draft text",
            draft_state_before=DraftVariantState.PENDING_REVIEW,
            draft_state_after=DraftVariantState.PENDING_REVIEW,
        )
        action_id = action.id
        draft_id = draft.id

    with session_scope(session_factory) as session:
        stored_action = ReviewActionRepository(session).get(action_id)
        draft_actions = ReviewActionRepository(session).list_for_draft(draft_id)

    assert stored_action is not None
    assert stored_action.reviewer == "editor-a"
    assert stored_action.before_text == "Draft text"
    assert stored_action.after_text == "Updated draft text"
    assert stored_action.draft_state_before is DraftVariantState.PENDING_REVIEW
    assert stored_action.draft_state_after is DraftVariantState.PENDING_REVIEW
    assert [draft_action.id for draft_action in draft_actions] == [action_id]


def test_publish_job_repository_detects_only_active_jobs_for_draft(session_factory) -> None:
    with session_scope(session_factory) as session:
        repository = PublishJobRepository(session)
        cancelled_draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        cancelled_job = repository.add(
            PublishJob(
                draft_variant=cancelled_draft,
                channel="x",
                idempotency_key="cancelled-job",
                scheduled_for=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            )
        )
        repository.transition_state(cancelled_job, PublishJobState.CANCELLED)
        cancelled_draft_id = cancelled_draft.id

        active_draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        repository.add(
            PublishJob(
                draft_variant=active_draft,
                channel="x",
                idempotency_key="active-job",
                scheduled_for=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
            )
        )
        active_draft_id = active_draft.id

    with session_scope(session_factory) as session:
        repository = PublishJobRepository(session)
        assert repository.has_active_job_for_draft(cancelled_draft_id) is False
        assert repository.has_active_job_for_draft(active_draft_id) is True


def test_publish_job_active_unique_index_rejects_duplicate_active_jobs(session_factory) -> None:
    with session_scope(session_factory) as session:
        repository = PublishJobRepository(session)
        draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        repository.add(
            PublishJob(
                draft_variant=draft,
                channel="x",
                idempotency_key="first-active-job",
                scheduled_for=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            )
        )

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            draft = DraftVariantRepository(session).list_by_state(DraftVariantState.APPROVED)[0]
            PublishJobRepository(session).add(
                PublishJob(
                    draft_variant=draft,
                    channel="x",
                    idempotency_key="second-active-job",
                    scheduled_for=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
                )
            )


def test_publish_job_idempotency_key_is_generated_when_missing(session_factory) -> None:
    with session_scope(session_factory) as session:
        job = _create_publish_job(session, draft_state=DraftVariantState.APPROVED)
        job_id = job.id

    with session_scope(session_factory) as session:
        stored_job = PublishJobRepository(session).get(job_id)

    assert stored_job is not None
    assert len(stored_job.idempotency_key) == 64


def test_publish_job_idempotency_unique_index_rejects_duplicates(session_factory) -> None:
    with session_scope(session_factory) as session:
        first_draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        second_draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        repository = PublishJobRepository(session)
        repository.add(
            PublishJob(
                draft_variant=first_draft,
                channel="x",
                idempotency_key="duplicate-key",
                scheduled_for=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            )
        )

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            draft = DraftVariantRepository(session).get(second_draft.id)
            assert draft is not None
            PublishJobRepository(session).add(
                PublishJob(
                    draft_variant=draft,
                    channel="x",
                    idempotency_key="duplicate-key",
                    scheduled_for=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
                )
            )


def test_publish_job_repository_lists_due_scheduled_jobs(session_factory) -> None:
    with session_scope(session_factory) as session:
        repository = PublishJobRepository(session)
        due_job = _create_publish_job(session, draft_state=DraftVariantState.APPROVED)
        future_job = repository.add(
            PublishJob(
                draft_variant=_create_draft_variant(session, draft_state=DraftVariantState.APPROVED),
                channel="x",
                idempotency_key="future-job",
                scheduled_for=datetime(2026, 3, 18, 11, 0, tzinfo=timezone.utc),
            )
        )
        failed_job = repository.add(
            PublishJob(
                draft_variant=_create_draft_variant(session, draft_state=DraftVariantState.APPROVED),
                channel="x",
                idempotency_key="failed-job",
                scheduled_for=datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
            )
        )
        repository.transition_state(failed_job, PublishJobState.FAILED, last_error="boom")

    with session_scope(session_factory) as session:
        due_jobs = PublishJobRepository(session).list_due_scheduled(
            as_of=datetime(2026, 3, 18, 9, 30, tzinfo=timezone.utc)
        )

    assert [job.id for job in due_jobs] == [due_job.id]
    assert future_job.id not in [job.id for job in due_jobs]


def test_publish_job_repository_lists_approved_drafts_without_active_jobs(session_factory) -> None:
    with session_scope(session_factory) as session:
        eligible = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            created_at=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
        )
        active_job_draft = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            created_at=datetime(2026, 3, 17, 10, 0, tzinfo=timezone.utc),
        )
        _create_publish_job_for_draft(session, active_job_draft, idempotency_key="active-job-for-draft")
        failed_job_draft = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            created_at=datetime(2026, 3, 17, 10, 30, tzinfo=timezone.utc),
        )
        failed_job = _create_publish_job_for_draft(
            session,
            failed_job_draft,
            idempotency_key="failed-job-for-draft",
        )
        PublishJobRepository(session).transition_state(failed_job, PublishJobState.FAILED, last_error="boom")
        _create_draft_variant(
            session,
            draft_state=DraftVariantState.PENDING_REVIEW,
            created_at=datetime(2026, 3, 17, 11, 0, tzinfo=timezone.utc),
        )
        _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            account_key="finance_news_daily",
            created_at=datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc),
        )

    with session_scope(session_factory) as session:
        drafts = PublishJobRepository(session).list_approved_without_active_job("ai_tools_daily", "x")

    assert [draft.id for draft in drafts] == [eligible.id]


def test_publish_job_repository_claim_due_job_is_atomic(session_factory) -> None:
    with session_scope(session_factory) as session:
        job = _create_publish_job(session, draft_state=DraftVariantState.APPROVED)
        job_id = job.id

    with session_scope(session_factory) as session:
        claimed_job = PublishJobRepository(session).claim_due_job(
            job_id,
            as_of=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
            claimed_at=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
        )
        assert claimed_job is not None
        assert claimed_job.state is PublishJobState.PUBLISHING
        assert claimed_job.attempt_count == 1

    with session_scope(session_factory) as session:
        claimed_again = PublishJobRepository(session).claim_due_job(
            job_id,
            as_of=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
            claimed_at=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
        )

    assert claimed_again is None


def test_session_scope_rolls_back_when_an_exception_occurs(session_factory) -> None:
    with pytest.raises(RuntimeError):
        with session_scope(session_factory) as session:
            SourceItemRepository(session).add(
                SourceItem(
                    source_key="ai_tools_rss",
                    external_id="entry-rollback",
                    source_url="https://example.com/posts/rollback",
                    title="Rollback me",
                    summary="Should not persist",
                )
            )
            raise RuntimeError("force rollback")

    with session_scope(session_factory) as session:
        items = SourceItemRepository(session).list()

    assert items == []


def test_bootstrap_database_rejects_outdated_schema(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE source_items (
                    id INTEGER PRIMARY KEY,
                    source_key VARCHAR(100) NOT NULL,
                    external_id VARCHAR(255) NOT NULL,
                    source_url VARCHAR(2048) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    summary TEXT,
                    published_at DATETIME,
                    raw_payload JSON,
                    state VARCHAR(32) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE article_enrichments (
                    id INTEGER PRIMARY KEY,
                    source_item_id INTEGER NOT NULL,
                    source_name VARCHAR(255),
                    article_url VARCHAR(2048) NOT NULL,
                    published_at DATETIME,
                    discovered_at DATETIME NOT NULL,
                    fetched_at DATETIME,
                    extracted_at DATETIME,
                    summarized_at DATETIME,
                    html_content TEXT,
                    article_text TEXT,
                    regenerated_summary TEXT,
                    regenerated_key_points JSON NOT NULL,
                    tags JSON NOT NULL,
                    company_names JSON NOT NULL,
                    tickers JSON NOT NULL,
                    markets JSON NOT NULL,
                    classification VARCHAR(50),
                    rss_discovered_status VARCHAR(32) NOT NULL,
                    saved_status VARCHAR(32) NOT NULL,
                    html_fetch_status VARCHAR(32) NOT NULL,
                    article_extract_status VARCHAR(32) NOT NULL,
                    summary_regenerate_status VARCHAR(32) NOT NULL,
                    brief_build_status VARCHAR(32) NOT NULL,
                    draft_generate_status VARCHAR(32) NOT NULL,
                    review_status VARCHAR(32) NOT NULL,
                    last_stage VARCHAR(32) NOT NULL,
                    failure_stage VARCHAR(32),
                    failure_code VARCHAR(100),
                    failure_message TEXT,
                    metadata_json JSON,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT uq_article_enrichments_source_item_id UNIQUE (source_item_id)
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE content_briefs (
                    id INTEGER PRIMARY KEY,
                    source_item_id INTEGER NOT NULL,
                    account_key VARCHAR(100) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    summary TEXT,
                    key_points JSON NOT NULL,
                    landing_url VARCHAR(2048) NOT NULL,
                    tags JSON NOT NULL,
                    angle VARCHAR(64) NOT NULL,
                    language VARCHAR(8) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE draft_variants (
                    id INTEGER PRIMARY KEY,
                    content_brief_id INTEGER NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    variant_index INTEGER NOT NULL,
                    body TEXT NOT NULL,
                    state VARCHAR(32) NOT NULL,
                    rejection_reason TEXT,
                    reviewed_at DATETIME,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE publish_jobs (
                    id INTEGER PRIMARY KEY,
                    draft_variant_id INTEGER NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    idempotency_key VARCHAR(64) NOT NULL,
                    scheduled_for DATETIME,
                    state VARCHAR(32) NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    external_post_id VARCHAR(255),
                    last_error TEXT,
                    published_at DATETIME,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE publish_logs (
                    id INTEGER PRIMARY KEY,
                    publish_job_id INTEGER NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    payload JSON,
                    created_at DATETIME NOT NULL
                )
                """
            )
    finally:
        engine.dispose()

    with pytest.raises(DatabaseSchemaError, match="outdated"):
        bootstrap_database(database_url)


def test_bootstrap_database_detects_missing_new_content_brief_columns(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        create_all_tables(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE content_briefs")
            connection.exec_driver_sql(
                """
                CREATE TABLE content_briefs (
                    id INTEGER PRIMARY KEY,
                    source_item_id INTEGER NOT NULL,
                    account_key VARCHAR(100) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    summary TEXT,
                    landing_url VARCHAR(2048) NOT NULL,
                    tags JSON NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
    finally:
        engine.dispose()

    with pytest.raises(DatabaseSchemaError, match="content_briefs: missing columns angle, key_points, language"):
        bootstrap_database(database_url)


def test_bootstrap_database_detects_missing_draft_variant_unique_constraint(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        create_all_tables(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE draft_variants")
            connection.exec_driver_sql(
                """
                CREATE TABLE draft_variants (
                    id INTEGER PRIMARY KEY,
                    content_brief_id INTEGER NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    variant_index INTEGER NOT NULL,
                    body TEXT NOT NULL,
                    state VARCHAR(32) NOT NULL,
                    rejection_reason TEXT,
                    reviewed_at DATETIME,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
    finally:
        engine.dispose()

    with pytest.raises(
        DatabaseSchemaError,
        match="draft_variants: missing unique constraints uq_draft_variants_content_brief_id_channel_variant_index",
    ):
        bootstrap_database(database_url)


def test_bootstrap_database_detects_missing_review_actions_table(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        create_all_tables(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE review_actions")
    finally:
        engine.dispose()

    with pytest.raises(DatabaseSchemaError, match="missing required tables: review_actions"):
        bootstrap_database(database_url)


def test_bootstrap_database_detects_missing_publish_job_active_unique_index(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE source_items (
                    id INTEGER PRIMARY KEY,
                    source_key VARCHAR(100) NOT NULL,
                    external_id VARCHAR(255) NOT NULL,
                    source_url VARCHAR(2048) NOT NULL,
                    canonical_url VARCHAR(2048) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    normalized_title VARCHAR(500) NOT NULL,
                    normalized_title_hash VARCHAR(64) NOT NULL,
                    summary TEXT,
                    dedupe_fingerprint VARCHAR(64) NOT NULL,
                    published_at DATETIME,
                    raw_payload JSON,
                    state VARCHAR(32) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT uq_source_items_source_key_external_id UNIQUE (source_key, external_id),
                    CONSTRAINT uq_source_items_canonical_url UNIQUE (canonical_url),
                    CONSTRAINT uq_source_items_normalized_title_hash UNIQUE (normalized_title_hash)
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE source_item_recent_fingerprint_claims (
                    id INTEGER PRIMARY KEY,
                    dedupe_fingerprint VARCHAR(64) NOT NULL,
                    source_item_id INTEGER,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_source_item_recent_fingerprint_claims_dedupe_fingerprint UNIQUE (dedupe_fingerprint),
                    CONSTRAINT uq_source_item_recent_fingerprint_claims_source_item_id UNIQUE (source_item_id)
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE pipeline_runs (
                    id INTEGER PRIMARY KEY,
                    workflow_name VARCHAR(100) NOT NULL,
                    trigger_mode VARCHAR(50) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    source_count INTEGER NOT NULL,
                    discovered_count INTEGER NOT NULL,
                    saved_count INTEGER NOT NULL,
                    enriched_count INTEGER NOT NULL,
                    summarized_count INTEGER NOT NULL,
                    brief_count INTEGER NOT NULL,
                    draft_count INTEGER NOT NULL,
                    failure_count INTEGER NOT NULL,
                    latest_error_code VARCHAR(100),
                    latest_error_message TEXT,
                    summary_json JSON,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE pipeline_run_stages (
                    id INTEGER PRIMARY KEY,
                    pipeline_run_id INTEGER NOT NULL,
                    stage VARCHAR(32) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    item_count INTEGER NOT NULL,
                    success_count INTEGER NOT NULL,
                    failure_count INTEGER NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME,
                    latest_error_code VARCHAR(100),
                    latest_error_message TEXT,
                    summary_json JSON,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT uq_pipeline_run_stages_pipeline_run_id_stage UNIQUE (pipeline_run_id, stage)
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE article_enrichments (
                    id INTEGER PRIMARY KEY,
                    source_item_id INTEGER NOT NULL,
                    source_name VARCHAR(255),
                    article_url VARCHAR(2048) NOT NULL,
                    published_at DATETIME,
                    discovered_at DATETIME NOT NULL,
                    fetched_at DATETIME,
                    extracted_at DATETIME,
                    summarized_at DATETIME,
                    html_content TEXT,
                    article_text TEXT,
                    regenerated_summary TEXT,
                    regenerated_key_points JSON NOT NULL,
                    tags JSON NOT NULL,
                    company_names JSON NOT NULL,
                    tickers JSON NOT NULL,
                    markets JSON NOT NULL,
                    classification VARCHAR(50),
                    rss_discovered_status VARCHAR(32) NOT NULL,
                    saved_status VARCHAR(32) NOT NULL,
                    html_fetch_status VARCHAR(32) NOT NULL,
                    article_extract_status VARCHAR(32) NOT NULL,
                    summary_regenerate_status VARCHAR(32) NOT NULL,
                    brief_build_status VARCHAR(32) NOT NULL,
                    draft_generate_status VARCHAR(32) NOT NULL,
                    review_status VARCHAR(32) NOT NULL,
                    last_stage VARCHAR(32) NOT NULL,
                    failure_stage VARCHAR(32),
                    failure_code VARCHAR(100),
                    failure_message TEXT,
                    metadata_json JSON,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT uq_article_enrichments_source_item_id UNIQUE (source_item_id)
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE content_briefs (
                    id INTEGER PRIMARY KEY,
                    source_item_id INTEGER NOT NULL,
                    account_key VARCHAR(100) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    summary TEXT,
                    key_points JSON NOT NULL,
                    landing_url VARCHAR(2048) NOT NULL,
                    tags JSON NOT NULL,
                    angle VARCHAR(64) NOT NULL,
                    language VARCHAR(8) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT uq_content_briefs_source_item_id_account_key UNIQUE (source_item_id, account_key)
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE draft_variants (
                    id INTEGER PRIMARY KEY,
                    content_brief_id INTEGER NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    variant_index INTEGER NOT NULL,
                    body TEXT NOT NULL,
                    state VARCHAR(32) NOT NULL,
                    rejection_reason TEXT,
                    reviewed_at DATETIME,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    CONSTRAINT uq_draft_variants_content_brief_id_channel_variant_index UNIQUE (content_brief_id, channel, variant_index)
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE publish_jobs (
                    id INTEGER PRIMARY KEY,
                    draft_variant_id INTEGER NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    idempotency_key VARCHAR(64) NOT NULL,
                    scheduled_for DATETIME,
                    state VARCHAR(32) NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    external_post_id VARCHAR(255),
                    last_error TEXT,
                    published_at DATETIME,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX uq_publish_jobs_idempotency_key ON publish_jobs (idempotency_key)"
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE publish_logs (
                    id INTEGER PRIMARY KEY,
                    publish_job_id INTEGER NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    payload JSON,
                    created_at DATETIME NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE review_actions (
                    id INTEGER PRIMARY KEY,
                    draft_variant_id INTEGER NOT NULL,
                    action_type VARCHAR(32) NOT NULL,
                    reviewer VARCHAR(255) NOT NULL,
                    before_text TEXT NOT NULL,
                    after_text TEXT NOT NULL,
                    draft_state_before VARCHAR(32) NOT NULL,
                    draft_state_after VARCHAR(32) NOT NULL,
                    rejection_reason TEXT,
                    scheduled_for DATETIME,
                    publish_job_id INTEGER,
                    created_at DATETIME NOT NULL
                )
                """
            )
    finally:
        engine.dispose()

    with pytest.raises(
        DatabaseSchemaError,
        match="publish_jobs: missing unique indexes uq_publish_jobs_active_draft_variant_id",
    ):
        bootstrap_database(database_url)


def test_bootstrap_database_detects_missing_publish_job_idempotency_column(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        create_all_tables(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE publish_jobs")
            connection.exec_driver_sql(
                """
                CREATE TABLE publish_jobs (
                    id INTEGER PRIMARY KEY,
                    draft_variant_id INTEGER NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    scheduled_for DATETIME,
                    state VARCHAR(32) NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    external_post_id VARCHAR(255),
                    last_error TEXT,
                    published_at DATETIME,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX uq_publish_jobs_active_draft_variant_id "
                "ON publish_jobs (draft_variant_id) WHERE state IN ('SCHEDULED', 'PUBLISHING', 'PUBLISHED')"
            )
    finally:
        engine.dispose()

    with pytest.raises(DatabaseSchemaError, match="publish_jobs: missing columns idempotency_key"):
        bootstrap_database(database_url)


def test_bootstrap_database_detects_missing_publish_job_idempotency_unique_index(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        create_all_tables(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP INDEX uq_publish_jobs_idempotency_key")
    finally:
        engine.dispose()

    with pytest.raises(
        DatabaseSchemaError,
        match="publish_jobs: missing unique indexes uq_publish_jobs_idempotency_key",
    ):
        bootstrap_database(database_url)


def _create_draft_variant(
    session,
    *,
    draft_state: DraftVariantState = DraftVariantState.PENDING_REVIEW,
    account_key: str = "ai_tools_daily",
    channel: str = "x",
    body: str = "Draft text",
    created_at: datetime | None = None,
) -> DraftVariant:
    source_id = next(_DRAFT_SOURCE_COUNTER)
    brief = _create_content_brief_for_draft(
        session,
        source_id=source_id,
        account_key=account_key,
    )
    repository = DraftVariantRepository(session)
    draft = repository.add(
        DraftVariant(
            content_brief=brief,
            channel=channel,
            variant_index=0,
            body=body,
            created_at=created_at or datetime.now(timezone.utc),
        )
    )
    if draft_state is DraftVariantState.APPROVED:
        repository.transition_state(draft, DraftVariantState.APPROVED)
    elif draft_state is DraftVariantState.REJECTED:
        repository.transition_state(
            draft,
            DraftVariantState.REJECTED,
            rejection_reason="Rejected during fixture setup",
        )
    return draft


def _create_content_brief_for_draft(
    session,
    *,
    source_id: int | None = None,
    account_key: str = "ai_tools_daily",
) -> ContentBrief:
    resolved_source_id = next(_DRAFT_SOURCE_COUNTER) if source_id is None else source_id
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"draft-source-{resolved_source_id}",
            source_url=f"https://example.com/posts/draft/{resolved_source_id}",
            title=f"Draft source {resolved_source_id}",
            summary=f"Draft source summary {resolved_source_id}",
        )
    )
    return ContentBriefRepository(session).add(
        ContentBrief(
            source_item=source_item,
            account_key=account_key,
            title="Brief for draft",
            summary="Brief summary",
            key_points=["Brief for draft"],
            landing_url="https://gilgop.cloud/ai-tools",
            tags=["ai"],
            angle="topic_takeaway",
            language="en",
        )
    )


def _create_publish_job(
    session,
    *,
    draft_state: DraftVariantState = DraftVariantState.APPROVED,
) -> PublishJob:
    draft = _create_draft_variant(session, draft_state=draft_state)
    return _create_publish_job_for_draft(session, draft)


def _create_publish_job_for_draft(
    session,
    draft: DraftVariant,
    *,
    idempotency_key: str | None = None,
) -> PublishJob:
    return PublishJobRepository(session).add(
        PublishJob(
            draft_variant=draft,
            channel="x",
            idempotency_key=idempotency_key or "",
            scheduled_for=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )
    )


class _IntegrityErrorRecoveringSession:
    def __init__(self, existing_brief: ContentBrief) -> None:
        self._existing_brief = existing_brief
        self.scalar_call_count = 0
        self.flush_call_count = 0

    def add(self, _brief: ContentBrief) -> None:
        return None

    def begin_nested(self):
        return nullcontext()

    def flush(self) -> None:
        self.flush_call_count += 1
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    def scalar(self, _statement):
        self.scalar_call_count += 1
        if self.scalar_call_count == 1:
            return None
        return self._existing_brief


class _DraftIntegrityErrorRecoveringSession:
    def __init__(self, existing_draft: DraftVariant) -> None:
        self._existing_draft = existing_draft
        self.scalar_call_count = 0
        self.flush_call_count = 0

    def add(self, _draft: DraftVariant) -> None:
        return None

    def begin_nested(self):
        return nullcontext()

    def flush(self) -> None:
        self.flush_call_count += 1
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    def scalar(self, _statement):
        self.scalar_call_count += 1
        if self.scalar_call_count == 1:
            return None
        return self._existing_draft
