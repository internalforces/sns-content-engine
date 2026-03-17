"""Tests for the database layer and repository behavior."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.storage import (
    ContentBrief,
    ContentBriefRepository,
    DatabaseSchemaError,
    DraftVariant,
    DraftVariantRepository,
    DraftVariantState,
    InvalidStateTransitionError,
    ManualApprovalRequiredError,
    PublishJob,
    PublishJobRepository,
    PublishJobState,
    PublishLogRepository,
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
        "content_briefs",
        "draft_variants",
        "publish_jobs",
        "publish_logs",
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


def _create_draft_variant(
    session,
    *,
    draft_state: DraftVariantState = DraftVariantState.PENDING_REVIEW,
) -> DraftVariant:
    source_id = next(_DRAFT_SOURCE_COUNTER)
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"draft-source-{source_id}",
            source_url=f"https://example.com/posts/draft/{source_id}",
            title=f"Draft source {source_id}",
            summary=f"Draft source summary {source_id}",
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
    repository = DraftVariantRepository(session)
    draft = repository.add(
        DraftVariant(
            content_brief=brief,
            channel="x",
            variant_index=0,
            body="Draft text",
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


def _create_publish_job(
    session,
    *,
    draft_state: DraftVariantState = DraftVariantState.APPROVED,
) -> PublishJob:
    draft = _create_draft_variant(session, draft_state=draft_state)
    return PublishJobRepository(session).add(
        PublishJob(
            draft_variant=draft,
            channel="x",
            scheduled_for=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        )
    )
