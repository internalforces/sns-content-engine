"""SQLAlchemy ORM models for the MVP database layer."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import TypeDecorator

from app.domain import (
    build_dedupe_fingerprint,
    build_normalized_title_hash,
    canonicalize_url,
    normalize_title_text,
)
from app.storage.database import Base


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _normalize_utc_datetime(value: datetime) -> datetime:
    """Normalize a datetime value to an aware UTC timestamp."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UtcDateTime(TypeDecorator[datetime]):
    """Persist datetimes in UTC and reattach timezone info on SQLite reads."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return _normalize_utc_datetime(value)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return _normalize_utc_datetime(value)


class SourceItemState(str, Enum):
    """Lifecycle states for ingested source items."""

    INGESTED = "ingested"
    BRIEF_CREATED = "brief_created"
    REJECTED = "rejected"


class SourcePolicyMode(str, Enum):
    """Stored source-policy mode captured from config at ingest time."""

    DISCOVERY_ONLY = "discovery_only"
    REUSABLE = "reusable"
    RESTRICTED = "restricted"


class PipelineStage(str, Enum):
    """Tracked pipeline stages for article enrichment and local run history."""

    RSS_DISCOVERED = "rss_discovered"
    SAVED = "saved"
    HTML_FETCH = "html_fetch"
    ARTICLE_EXTRACT = "article_extract"
    SUMMARY_REGENERATE = "summary_regenerate"
    BRIEF_BUILD = "brief_build"
    DRAFT_GENERATE = "draft_generate"
    PENDING_REVIEW = "pending_review"


class StageExecutionStatus(str, Enum):
    """Execution status for one tracked pipeline stage."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineRunStatus(str, Enum):
    """Lifecycle status for a local pipeline execution."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class DraftVariantState(str, Enum):
    """Lifecycle states for generated draft variants."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PublishJobState(str, Enum):
    """Lifecycle states for publish jobs."""

    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewActionType(str, Enum):
    """Audit action types for manual review operations."""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    SCHEDULE = "schedule"


class SourceItem(Base):
    """Normalized source content awaiting downstream processing."""

    __tablename__ = "source_items"
    __table_args__ = (
        UniqueConstraint(
            "source_key",
            "external_id",
            name="uq_source_items_source_key_external_id",
        ),
        UniqueConstraint(
            "canonical_url",
            name="uq_source_items_canonical_url",
        ),
        UniqueConstraint(
            "normalized_title_hash",
            name="uq_source_items_normalized_title_hash",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedupe_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    policy_mode: Mapped[SourcePolicyMode] = mapped_column(
        SqlEnum(SourcePolicyMode, native_enum=False, length=32),
        default=SourcePolicyMode.REUSABLE,
        nullable=False,
    )
    allow_full_text_fetch: Mapped[bool] = mapped_column(default=True, nullable=False)
    allow_llm_rewrite: Mapped[bool] = mapped_column(default=True, nullable=False)
    require_attribution: Mapped[bool] = mapped_column(default=False, nullable=False)
    state: Mapped[SourceItemState] = mapped_column(
        SqlEnum(SourceItemState, native_enum=False, length=32),
        default=SourceItemState.INGESTED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    content_briefs: Mapped[list["ContentBrief"]] = relationship(
        back_populates="source_item",
        cascade="all, delete-orphan",
    )
    recent_fingerprint_claim: Mapped["SourceItemRecentFingerprintClaim | None"] = relationship(
        back_populates="source_item",
        cascade="all, delete-orphan",
        uselist=False,
    )
    article_enrichment: Mapped["ArticleEnrichment | None"] = relationship(
        back_populates="source_item",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @validates("source_url", "title", "summary")
    def _populate_dedupe_fields(self, key: str, value: str | None) -> str | None:
        if key == "source_url":
            if value is None:
                raise ValueError("source_url must not be empty")
            canonical_url = canonicalize_url(value)
            self.canonical_url = canonical_url
            return canonical_url

        if key == "title":
            if value is None:
                raise ValueError("title must not be empty")
            self.normalized_title = normalize_title_text(value)
            self.normalized_title_hash = build_normalized_title_hash(value)

        title = value if key == "title" else getattr(self, "title", None)
        summary = value if key == "summary" else getattr(self, "summary", None)
        if title:
            self.dedupe_fingerprint = build_dedupe_fingerprint(title=title, summary=summary)

        return value


class SourceItemRecentFingerprintClaim(Base):
    """Active recent-window fingerprint claim used to serialize dedupe decisions."""

    __tablename__ = "source_item_recent_fingerprint_claims"
    __table_args__ = (
        UniqueConstraint(
            "dedupe_fingerprint",
            name="uq_source_item_recent_fingerprint_claims_dedupe_fingerprint",
        ),
        UniqueConstraint(
            "source_item_id",
            name="uq_source_item_recent_fingerprint_claims_source_item_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dedupe_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)

    source_item: Mapped[SourceItem | None] = relationship(back_populates="recent_fingerprint_claim")


class ArticleEnrichment(Base):
    """Persisted article-level enrichment data for a discovered source item."""

    __tablename__ = "article_enrichments"
    __table_args__ = (
        UniqueConstraint(
            "source_item_id",
            name="uq_article_enrichments_source_item_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_item_id: Mapped[int] = mapped_column(
        ForeignKey("source_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    article_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    fetched_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    summarized_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    article_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    regenerated_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    regenerated_key_points: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    company_names: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tickers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    markets: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rss_discovered_status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.SUCCEEDED,
        nullable=False,
    )
    saved_status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.SUCCEEDED,
        nullable=False,
    )
    html_fetch_status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.PENDING,
        nullable=False,
    )
    article_extract_status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.PENDING,
        nullable=False,
    )
    summary_regenerate_status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.PENDING,
        nullable=False,
    )
    brief_build_status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.PENDING,
        nullable=False,
    )
    draft_generate_status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.PENDING,
        nullable=False,
    )
    review_status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.PENDING,
        nullable=False,
    )
    policy_decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_stage: Mapped[PipelineStage] = mapped_column(
        SqlEnum(PipelineStage, native_enum=False, length=32),
        default=PipelineStage.SAVED,
        nullable=False,
    )
    failure_stage: Mapped[PipelineStage | None] = mapped_column(
        SqlEnum(PipelineStage, native_enum=False, length=32),
        nullable=True,
    )
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    source_item: Mapped[SourceItem] = relationship(back_populates="article_enrichment")


class PipelineRun(Base):
    """Stored execution summary for one local one-shot pipeline run."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    trigger_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="manual_local")
    status: Mapped[PipelineRunStatus] = mapped_column(
        SqlEnum(PipelineRunStatus, native_enum=False, length=32),
        default=PipelineRunStatus.RUNNING,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discovered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enriched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summarized_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    brief_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    draft_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latest_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    stage_runs: Mapped[list["PipelineRunStage"]] = relationship(
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )


class PipelineRunStage(Base):
    """Per-stage execution summary attached to a pipeline run."""

    __tablename__ = "pipeline_run_stages"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_run_id",
            "stage",
            name="uq_pipeline_run_stages_pipeline_run_id_stage",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[PipelineStage] = mapped_column(
        SqlEnum(PipelineStage, native_enum=False, length=32),
        nullable=False,
    )
    status: Mapped[StageExecutionStatus] = mapped_column(
        SqlEnum(StageExecutionStatus, native_enum=False, length=32),
        default=StageExecutionStatus.PENDING,
        nullable=False,
    )
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    latest_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latest_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    pipeline_run: Mapped[PipelineRun] = relationship(back_populates="stage_runs")


class ContentBrief(Base):
    """Platform-neutral content brief derived from a source item."""

    __tablename__ = "content_briefs"
    __table_args__ = (
        UniqueConstraint(
            "source_item_id",
            "account_key",
            name="uq_content_briefs_source_item_id_account_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_item_id: Mapped[int] = mapped_column(
        ForeignKey("source_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    landing_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    angle: Mapped[str] = mapped_column(String(64), default="topic_takeaway", nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    source_item: Mapped[SourceItem] = relationship(back_populates="content_briefs")
    draft_variants: Mapped[list["DraftVariant"]] = relationship(
        back_populates="content_brief",
        cascade="all, delete-orphan",
    )


class DraftVariant(Base):
    """Channel-specific draft output awaiting review."""

    __tablename__ = "draft_variants"
    __table_args__ = (
        UniqueConstraint(
            "content_brief_id",
            "channel",
            "variant_index",
            name="uq_draft_variants_content_brief_id_channel_variant_index",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    content_brief_id: Mapped[int] = mapped_column(
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    variant_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    article_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    source_policy_mode: Mapped[SourcePolicyMode | None] = mapped_column(
        SqlEnum(SourcePolicyMode, native_enum=False, length=32),
        nullable=True,
    )
    state: Mapped[DraftVariantState] = mapped_column(
        SqlEnum(DraftVariantState, native_enum=False, length=32),
        default=DraftVariantState.PENDING_REVIEW,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    content_brief: Mapped[ContentBrief] = relationship(back_populates="draft_variants")
    publish_jobs: Mapped[list["PublishJob"]] = relationship(
        back_populates="draft_variant",
        cascade="all, delete-orphan",
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        back_populates="draft_variant",
        cascade="all, delete-orphan",
    )


class PublishJob(Base):
    """Scheduled publishing intent for an approved draft variant."""

    __tablename__ = "publish_jobs"
    __table_args__ = (
        Index(
            "uq_publish_jobs_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "uq_publish_jobs_active_draft_variant_id",
            "draft_variant_id",
            unique=True,
            sqlite_where=text("state IN ('SCHEDULED', 'PUBLISHING', 'PUBLISHED')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_variant_id: Mapped[int] = mapped_column(
        ForeignKey("draft_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    state: Mapped[PublishJobState] = mapped_column(
        SqlEnum(PublishJobState, native_enum=False, length=32),
        default=PublishJobState.SCHEDULED,
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    draft_variant: Mapped[DraftVariant] = relationship(back_populates="publish_jobs")
    publish_logs: Mapped[list["PublishLog"]] = relationship(
        back_populates="publish_job",
        cascade="all, delete-orphan",
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(back_populates="publish_job")


class ReviewAction(Base):
    """Stored audit trail for manual review queue activity."""

    __tablename__ = "review_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_variant_id: Mapped[int] = mapped_column(
        ForeignKey("draft_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[ReviewActionType] = mapped_column(
        SqlEnum(ReviewActionType, native_enum=False, length=32),
        nullable=False,
    )
    reviewer: Mapped[str] = mapped_column(String(255), nullable=False)
    before_text: Mapped[str] = mapped_column(Text, nullable=False)
    after_text: Mapped[str] = mapped_column(Text, nullable=False)
    draft_state_before: Mapped[DraftVariantState] = mapped_column(
        SqlEnum(DraftVariantState, native_enum=False, length=32),
        nullable=False,
    )
    draft_state_after: Mapped[DraftVariantState] = mapped_column(
        SqlEnum(DraftVariantState, native_enum=False, length=32),
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    publish_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("publish_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)

    draft_variant: Mapped[DraftVariant] = relationship(back_populates="review_actions")
    publish_job: Mapped[PublishJob | None] = relationship(back_populates="review_actions")


class PublishLog(Base):
    """Audit trail for publish job activity."""

    __tablename__ = "publish_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    publish_job_id: Mapped[int] = mapped_column(
        ForeignKey("publish_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, nullable=False)

    publish_job: Mapped[PublishJob] = relationship(back_populates="publish_logs")
