"""Repository classes for database-backed storage operations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import (
    ContentBrief,
    DraftVariant,
    DraftVariantState,
    PublishJob,
    PublishJobState,
    PublishLog,
    SourceItem,
)


class InvalidStateTransitionError(ValueError):
    """Raised when a state transition violates the domain workflow."""


class SourceItemRepository:
    """Persistence operations for source items."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, item: SourceItem) -> SourceItem:
        self.session.add(item)
        self.session.flush()
        return item

    def get(self, item_id: int) -> SourceItem | None:
        return self.session.get(SourceItem, item_id)

    def list(self) -> list[SourceItem]:
        return list(self.session.scalars(select(SourceItem).order_by(SourceItem.id)))

    def delete(self, item: SourceItem) -> None:
        self.session.delete(item)


class ContentBriefRepository:
    """Persistence operations for content briefs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, brief: ContentBrief) -> ContentBrief:
        self.session.add(brief)
        self.session.flush()
        return brief

    def get(self, brief_id: int) -> ContentBrief | None:
        return self.session.get(ContentBrief, brief_id)

    def list(self) -> list[ContentBrief]:
        return list(self.session.scalars(select(ContentBrief).order_by(ContentBrief.id)))

    def delete(self, brief: ContentBrief) -> None:
        self.session.delete(brief)


class DraftVariantRepository:
    """Persistence and workflow operations for draft variants."""

    _allowed_transitions: dict[DraftVariantState, tuple[DraftVariantState, ...]] = {
        DraftVariantState.PENDING_REVIEW: (
            DraftVariantState.APPROVED,
            DraftVariantState.REJECTED,
        ),
        DraftVariantState.APPROVED: (),
        DraftVariantState.REJECTED: (),
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, draft: DraftVariant) -> DraftVariant:
        self.session.add(draft)
        self.session.flush()
        return draft

    def get(self, draft_id: int) -> DraftVariant | None:
        return self.session.get(DraftVariant, draft_id)

    def list(self) -> list[DraftVariant]:
        return list(self.session.scalars(select(DraftVariant).order_by(DraftVariant.id)))

    def delete(self, draft: DraftVariant) -> None:
        self.session.delete(draft)

    def transition_state(
        self,
        draft: DraftVariant,
        new_state: DraftVariantState,
        *,
        rejection_reason: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> DraftVariant:
        self._validate_transition(draft.state, new_state)
        draft.state = new_state
        draft.reviewed_at = reviewed_at or datetime.now(timezone.utc)
        draft.rejection_reason = rejection_reason if new_state is DraftVariantState.REJECTED else None
        self.session.flush()
        return draft

    def _validate_transition(
        self, current_state: DraftVariantState, new_state: DraftVariantState
    ) -> None:
        allowed = self._allowed_transitions[current_state]
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"cannot transition DraftVariant from {current_state.value!r} to {new_state.value!r}"
            )


class PublishJobRepository:
    """Persistence and workflow operations for publish jobs."""

    _allowed_transitions: dict[PublishJobState, tuple[PublishJobState, ...]] = {
        PublishJobState.SCHEDULED: (
            PublishJobState.PUBLISHING,
            PublishJobState.FAILED,
            PublishJobState.CANCELLED,
        ),
        PublishJobState.PUBLISHING: (
            PublishJobState.PUBLISHED,
            PublishJobState.FAILED,
        ),
        PublishJobState.PUBLISHED: (),
        PublishJobState.FAILED: (),
        PublishJobState.CANCELLED: (),
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, job: PublishJob) -> PublishJob:
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: int) -> PublishJob | None:
        return self.session.get(PublishJob, job_id)

    def list(self) -> list[PublishJob]:
        return list(self.session.scalars(select(PublishJob).order_by(PublishJob.id)))

    def delete(self, job: PublishJob) -> None:
        self.session.delete(job)

    def transition_state(
        self,
        job: PublishJob,
        new_state: PublishJobState,
        *,
        external_post_id: str | None = None,
        last_error: str | None = None,
        occurred_at: datetime | None = None,
    ) -> PublishJob:
        self._validate_transition(job.state, new_state)

        event_time = occurred_at or datetime.now(timezone.utc)
        if new_state is PublishJobState.PUBLISHING:
            job.attempt_count += 1
            job.last_error = None
        elif new_state is PublishJobState.PUBLISHED:
            job.external_post_id = external_post_id
            job.published_at = event_time
            job.last_error = None
        elif new_state is PublishJobState.FAILED:
            job.last_error = last_error

        job.state = new_state
        self.session.flush()
        return job

    def _validate_transition(self, current_state: PublishJobState, new_state: PublishJobState) -> None:
        allowed = self._allowed_transitions[current_state]
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"cannot transition PublishJob from {current_state.value!r} to {new_state.value!r}"
            )


class PublishLogRepository:
    """Persistence operations for publish logs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, log: PublishLog) -> PublishLog:
        self.session.add(log)
        self.session.flush()
        return log

    def get(self, log_id: int) -> PublishLog | None:
        return self.session.get(PublishLog, log_id)

    def list(self) -> list[PublishLog]:
        return list(self.session.scalars(select(PublishLog).order_by(PublishLog.id)))

    def delete(self, log: PublishLog) -> None:
        self.session.delete(log)

    def list_for_job(self, publish_job_id: int) -> Sequence[PublishLog]:
        statement = select(PublishLog).where(PublishLog.publish_job_id == publish_job_id).order_by(
            PublishLog.created_at,
            PublishLog.id,
        )
        return list(self.session.scalars(statement))

    def record(
        self,
        publish_job: PublishJob,
        *,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> PublishLog:
        log = PublishLog(
            publish_job=publish_job,
            event_type=event_type.strip(),
            message=message,
            payload=payload,
        )
        self.session.add(log)
        self.session.flush()
        return log
