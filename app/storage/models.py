"""SQLAlchemy ORM models for the MVP database layer."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

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


class SourceItem(Base):
    """Normalized source content awaiting downstream processing."""

    __tablename__ = "source_items"
    __table_args__ = (
        UniqueConstraint(
            "source_key",
            "external_id",
            name="uq_source_items_source_key_external_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
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


class ContentBrief(Base):
    """Platform-neutral content brief derived from a source item."""

    __tablename__ = "content_briefs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_item_id: Mapped[int] = mapped_column(
        ForeignKey("source_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    landing_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
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

    id: Mapped[int] = mapped_column(primary_key=True)
    content_brief_id: Mapped[int] = mapped_column(
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    variant_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    body: Mapped[str] = mapped_column(Text, nullable=False)
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


class PublishJob(Base):
    """Scheduled publishing intent for an approved draft variant."""

    __tablename__ = "publish_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_variant_id: Mapped[int] = mapped_column(
        ForeignKey("draft_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
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
