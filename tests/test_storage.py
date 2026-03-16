"""Tests for the database layer and repository behavior."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect

from app.storage import (
    ContentBrief,
    ContentBriefRepository,
    DraftVariant,
    DraftVariantRepository,
    DraftVariantState,
    InvalidStateTransitionError,
    PublishJob,
    PublishJobRepository,
    PublishJobState,
    PublishLogRepository,
    SourceItem,
    SourceItemRepository,
    SourceItemState,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)


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
        "content_briefs",
        "draft_variants",
        "publish_jobs",
        "publish_logs",
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
                landing_url="https://gilgop.cloud/ai-tools",
                tags=["ai", "workflow"],
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
        assert brief.tags == ["ai", "workflow"]
        assert len(stored_logs) == 1
        assert stored_logs[0].event_type == "scheduled"
        assert stored_log is not None
        assert stored_log.payload == {"source": "manual"}


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


def test_publish_job_state_transitions_are_enforced(session_factory) -> None:
    with session_scope(session_factory) as session:
        job = _create_publish_job(session)
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
    assert stored_job.published_at is not None

    with session_scope(session_factory) as session:
        invalid_job = _create_publish_job(session)
        with pytest.raises(InvalidStateTransitionError):
            PublishJobRepository(session).transition_state(invalid_job, PublishJobState.PUBLISHED)


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


def _create_draft_variant(session) -> DraftVariant:
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id="draft-source",
            source_url="https://example.com/posts/draft",
            title="Draft source",
            summary="Draft source summary",
        )
    )
    brief = ContentBriefRepository(session).add(
        ContentBrief(
            source_item=source_item,
            account_key="ai_tools_daily",
            title="Brief for draft",
            summary="Brief summary",
            landing_url="https://gilgop.cloud/ai-tools",
            tags=["ai"],
        )
    )
    return DraftVariantRepository(session).add(
        DraftVariant(
            content_brief=brief,
            channel="x",
            variant_index=0,
            body="Draft text",
        )
    )


def _create_publish_job(session) -> PublishJob:
    draft = _create_draft_variant(session)
    return PublishJobRepository(session).add(
        PublishJob(
            draft_variant=draft,
            channel="x",
            scheduled_for=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )
    )
