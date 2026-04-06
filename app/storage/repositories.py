"""Repository classes for database-backed storage operations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
import hashlib
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.storage.models import (
    ArticleEnrichment,
    ContentBrief,
    DraftVariant,
    DraftVariantState,
    PublishJob,
    PublishJobState,
    PublishLog,
    PipelineRun,
    PipelineRunStage,
    ReviewAction,
    ReviewActionType,
    SourceItem,
    SourceItemRecentFingerprintClaim,
    SourceItemState,
    StageExecutionStatus,
)


class InvalidStateTransitionError(ValueError):
    """Raised when a state transition violates the domain workflow."""


class ManualApprovalRequiredError(ValueError):
    """Raised when publishing is attempted before manual approval."""


def build_publish_job_idempotency_key(
    *,
    draft_variant_id: int,
    channel: str,
    scheduled_for: datetime,
) -> str:
    """Build a stable idempotency key for a draft/channel/slot combination."""

    normalized_scheduled_for = scheduled_for.astimezone(timezone.utc)
    raw_key = f"{draft_variant_id}:{channel.strip()}:{normalized_scheduled_for.isoformat()}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class SourceItemRepository:
    """Persistence operations for source items."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, item: SourceItem) -> SourceItem:
        self.session.add(item)
        self.session.flush()
        return item

    def get_by_source_identity(self, source_key: str, external_id: str) -> SourceItem | None:
        statement = select(SourceItem).where(
            SourceItem.source_key == source_key,
            SourceItem.external_id == external_id,
        )
        return self.session.scalar(statement)

    def get_by_canonical_url(self, canonical_url: str) -> SourceItem | None:
        statement = select(SourceItem).where(SourceItem.canonical_url == canonical_url)
        return self.session.scalar(statement)

    def get_by_normalized_title_hash(self, normalized_title_hash: str) -> SourceItem | None:
        statement = select(SourceItem).where(
            SourceItem.normalized_title_hash == normalized_title_hash
        )
        return self.session.scalar(statement)

    def get_recent_by_dedupe_fingerprint(
        self,
        dedupe_fingerprint: str,
        *,
        created_since: datetime,
    ) -> SourceItem | None:
        statement = (
            select(SourceItem)
            .where(
                SourceItem.dedupe_fingerprint == dedupe_fingerprint,
                SourceItem.created_at >= created_since,
            )
            .order_by(SourceItem.created_at.desc(), SourceItem.id.desc())
        )
        return self.session.scalar(statement)

    def get_or_create(self, item: SourceItem) -> tuple[SourceItem, bool]:
        existing = self.get_by_source_identity(item.source_key, item.external_id)
        if existing is not None:
            return existing, False

        self.session.add(item)
        self.session.flush()
        return item, True

    def get(self, item_id: int) -> SourceItem | None:
        return self.session.get(SourceItem, item_id)

    def list_by_state(self, state: SourceItemState) -> list[SourceItem]:
        statement = select(SourceItem).where(SourceItem.state == state).order_by(SourceItem.id)
        return list(self.session.scalars(statement))

    def list(self) -> list[SourceItem]:
        return list(self.session.scalars(select(SourceItem).order_by(SourceItem.id)))

    def list_by_ids(self, item_ids: Sequence[int]) -> list[SourceItem]:
        if not item_ids:
            return []
        statement = select(SourceItem).where(SourceItem.id.in_(tuple(item_ids))).order_by(SourceItem.id)
        return list(self.session.scalars(statement))

    def delete(self, item: SourceItem) -> None:
        self.session.delete(item)


class SourceItemRecentFingerprintClaimRepository:
    """Persistence helpers for active recent fingerprint claims."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, claim: SourceItemRecentFingerprintClaim) -> SourceItemRecentFingerprintClaim:
        self.session.add(claim)
        self.session.flush()
        return claim

    def get_active(
        self,
        dedupe_fingerprint: str,
        *,
        as_of: datetime,
    ) -> SourceItemRecentFingerprintClaim | None:
        statement = (
            select(SourceItemRecentFingerprintClaim)
            .where(
                SourceItemRecentFingerprintClaim.dedupe_fingerprint == dedupe_fingerprint,
                SourceItemRecentFingerprintClaim.expires_at > as_of,
            )
            .order_by(SourceItemRecentFingerprintClaim.expires_at.desc())
        )
        return self.session.scalar(statement)

    def delete_expired(self, *, as_of: datetime) -> int:
        statement = select(SourceItemRecentFingerprintClaim).where(
            SourceItemRecentFingerprintClaim.expires_at <= as_of
        )
        expired_claims = list(self.session.scalars(statement))
        for claim in expired_claims:
            self.session.delete(claim)
        self.session.flush()
        return len(expired_claims)


class ArticleEnrichmentRepository:
    """Persistence operations for article enrichment rows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, enrichment: ArticleEnrichment) -> ArticleEnrichment:
        self.session.add(enrichment)
        self.session.flush()
        return enrichment

    def get(self, enrichment_id: int) -> ArticleEnrichment | None:
        return self.session.get(ArticleEnrichment, enrichment_id)

    def get_by_source_item_id(self, source_item_id: int) -> ArticleEnrichment | None:
        statement = select(ArticleEnrichment).where(
            ArticleEnrichment.source_item_id == source_item_id
        )
        return self.session.scalar(statement)

    def get_or_create(
        self,
        enrichment: ArticleEnrichment,
    ) -> tuple[ArticleEnrichment, bool]:
        source_item_id = enrichment.source_item_id
        if source_item_id is None and enrichment.source_item is not None:
            source_item_id = enrichment.source_item.id
        if source_item_id is None:
            raise ValueError("article enrichment must reference a persisted source item")

        existing = self.get_by_source_item_id(source_item_id)
        if existing is not None:
            return existing, False

        enrichment.source_item_id = source_item_id
        try:
            with self.session.begin_nested():
                self.session.add(enrichment)
                self.session.flush()
        except IntegrityError:
            existing = self.get_by_source_item_id(source_item_id)
            if existing is None:
                raise
            return existing, False
        return enrichment, True

    def list(self) -> list[ArticleEnrichment]:
        statement = select(ArticleEnrichment).order_by(ArticleEnrichment.id)
        return list(self.session.scalars(statement))

    def list_failed(self, *, limit: int = 50) -> list[ArticleEnrichment]:
        statement = (
            select(ArticleEnrichment)
            .where(ArticleEnrichment.failure_code.is_not(None))
            .order_by(ArticleEnrichment.updated_at.desc(), ArticleEnrichment.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_policy_skipped(self, *, limit: int = 50) -> list[ArticleEnrichment]:
        statement = (
            select(ArticleEnrichment)
            .where(
                ArticleEnrichment.policy_decision_reason.is_not(None),
                or_(
                    ArticleEnrichment.html_fetch_status == StageExecutionStatus.SKIPPED,
                    ArticleEnrichment.summary_regenerate_status == StageExecutionStatus.SKIPPED,
                ),
            )
            .order_by(ArticleEnrichment.updated_at.desc(), ArticleEnrichment.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def delete(self, enrichment: ArticleEnrichment) -> None:
        self.session.delete(enrichment)


class PipelineRunRepository:
    """Persistence operations for local pipeline run summaries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, pipeline_run: PipelineRun) -> PipelineRun:
        self.session.add(pipeline_run)
        self.session.flush()
        return pipeline_run

    def get(self, pipeline_run_id: int) -> PipelineRun | None:
        return self.session.get(PipelineRun, pipeline_run_id)

    def list(self) -> list[PipelineRun]:
        statement = select(PipelineRun).order_by(PipelineRun.started_at.desc(), PipelineRun.id.desc())
        return list(self.session.scalars(statement))

    def list_recent(self, *, limit: int = 20) -> list[PipelineRun]:
        statement = (
            select(PipelineRun)
            .order_by(PipelineRun.started_at.desc(), PipelineRun.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def delete(self, pipeline_run: PipelineRun) -> None:
        self.session.delete(pipeline_run)


class PipelineRunStageRepository:
    """Persistence operations for per-stage pipeline run summaries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, stage_run: PipelineRunStage) -> PipelineRunStage:
        self.session.add(stage_run)
        self.session.flush()
        return stage_run

    def get(self, pipeline_run_stage_id: int) -> PipelineRunStage | None:
        return self.session.get(PipelineRunStage, pipeline_run_stage_id)

    def get_by_run_and_stage(
        self,
        pipeline_run_id: int,
        stage,
    ) -> PipelineRunStage | None:
        statement = select(PipelineRunStage).where(
            PipelineRunStage.pipeline_run_id == pipeline_run_id,
            PipelineRunStage.stage == stage,
        )
        return self.session.scalar(statement)

    def get_or_create(
        self,
        stage_run: PipelineRunStage,
    ) -> tuple[PipelineRunStage, bool]:
        pipeline_run_id = stage_run.pipeline_run_id
        if pipeline_run_id is None and stage_run.pipeline_run is not None:
            pipeline_run_id = stage_run.pipeline_run.id
        if pipeline_run_id is None:
            raise ValueError("pipeline run stage must reference a persisted pipeline run")

        existing = self.get_by_run_and_stage(pipeline_run_id, stage_run.stage)
        if existing is not None:
            return existing, False

        stage_run.pipeline_run_id = pipeline_run_id
        try:
            with self.session.begin_nested():
                self.session.add(stage_run)
                self.session.flush()
        except IntegrityError:
            existing = self.get_by_run_and_stage(pipeline_run_id, stage_run.stage)
            if existing is None:
                raise
            return existing, False
        return stage_run, True

    def list_for_run(self, pipeline_run_id: int) -> list[PipelineRunStage]:
        statement = (
            select(PipelineRunStage)
            .where(PipelineRunStage.pipeline_run_id == pipeline_run_id)
            .order_by(PipelineRunStage.id)
        )
        return list(self.session.scalars(statement))

    def delete(self, stage_run: PipelineRunStage) -> None:
        self.session.delete(stage_run)


class ContentBriefRepository:
    """Persistence operations for content briefs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, brief: ContentBrief) -> ContentBrief:
        self.session.add(brief)
        self.session.flush()
        return brief

    def get_by_source_item_and_account(
        self,
        source_item_id: int,
        account_key: str,
    ) -> ContentBrief | None:
        statement = select(ContentBrief).where(
            ContentBrief.source_item_id == source_item_id,
            ContentBrief.account_key == account_key,
        )
        return self.session.scalar(statement)

    def get_or_create(self, brief: ContentBrief) -> tuple[ContentBrief, bool]:
        source_item_id = brief.source_item_id
        if source_item_id is None and brief.source_item is not None:
            source_item_id = brief.source_item.id
        if source_item_id is None:
            raise ValueError("content brief must reference a persisted source item")

        existing = self.get_by_source_item_and_account(source_item_id, brief.account_key)
        if existing is not None:
            return existing, False

        brief.source_item_id = source_item_id
        try:
            with self.session.begin_nested():
                self.session.add(brief)
                self.session.flush()
        except IntegrityError:
            existing = self.get_by_source_item_and_account(source_item_id, brief.account_key)
            if existing is None:
                raise
            return existing, False
        return brief, True

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

    def get_by_identity(
        self,
        content_brief_id: int,
        channel: str,
        variant_index: int,
    ) -> DraftVariant | None:
        statement = select(DraftVariant).where(
            DraftVariant.content_brief_id == content_brief_id,
            DraftVariant.channel == channel,
            DraftVariant.variant_index == variant_index,
        )
        return self.session.scalar(statement)

    def list(self) -> list[DraftVariant]:
        return list(self.session.scalars(select(DraftVariant).order_by(DraftVariant.id)))

    def list_by_state(self, state: DraftVariantState) -> list[DraftVariant]:
        statement = select(DraftVariant).where(DraftVariant.state == state).order_by(DraftVariant.id)
        return list(self.session.scalars(statement))

    def list_by_content_brief_and_channel(
        self,
        content_brief_id: int,
        channel: str,
    ) -> list[DraftVariant]:
        statement = (
            select(DraftVariant)
            .where(
                DraftVariant.content_brief_id == content_brief_id,
                DraftVariant.channel == channel,
            )
            .order_by(DraftVariant.variant_index, DraftVariant.id)
        )
        return list(self.session.scalars(statement))

    def list_recent_by_account_and_channel(
        self,
        account_key: str,
        channel: str,
        *,
        created_since: datetime,
        exclude_draft_id: int | None = None,
    ) -> list[DraftVariant]:
        statement = (
            select(DraftVariant)
            .join(DraftVariant.content_brief)
            .where(
                ContentBrief.account_key == account_key,
                DraftVariant.channel == channel,
                DraftVariant.state != DraftVariantState.REJECTED,
                DraftVariant.created_at >= created_since,
            )
            .order_by(DraftVariant.created_at.desc(), DraftVariant.id.desc())
        )
        if exclude_draft_id is not None:
            statement = statement.where(DraftVariant.id != exclude_draft_id)
        return list(self.session.scalars(statement))

    def get_or_create(self, draft: DraftVariant) -> tuple[DraftVariant, bool]:
        content_brief_id = draft.content_brief_id
        if content_brief_id is None and draft.content_brief is not None:
            content_brief_id = draft.content_brief.id
        if content_brief_id is None:
            raise ValueError("draft variant must reference a persisted content brief")

        existing = self.get_by_identity(content_brief_id, draft.channel, draft.variant_index)
        if existing is not None:
            return existing, False

        draft.content_brief_id = content_brief_id
        try:
            with self.session.begin_nested():
                self.session.add(draft)
                self.session.flush()
        except IntegrityError:
            existing = self.get_by_identity(content_brief_id, draft.channel, draft.variant_index)
            if existing is None:
                raise
            return existing, False
        return draft, True

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

    _active_states = (
        PublishJobState.SCHEDULED,
        PublishJobState.PUBLISHING,
        PublishJobState.PUBLISHED,
    )
    _backfill_blocking_states = _active_states + (PublishJobState.FAILED,)
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
        self._ensure_draft_is_approved(job)
        self._ensure_idempotency_key(job)
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: int) -> PublishJob | None:
        return self.session.get(PublishJob, job_id)

    def list(self) -> list[PublishJob]:
        return list(self.session.scalars(select(PublishJob).order_by(PublishJob.id)))

    def list_due_scheduled(self, *, as_of: datetime) -> list[PublishJob]:
        statement = (
            select(PublishJob)
            .where(
                PublishJob.state == PublishJobState.SCHEDULED,
                PublishJob.scheduled_for.is_not(None),
                PublishJob.scheduled_for <= as_of,
            )
            .order_by(PublishJob.scheduled_for, PublishJob.id)
        )
        return list(self.session.scalars(statement))

    def list_active_for_account_channel(self, account_key: str, channel: str) -> list[PublishJob]:
        statement = (
            select(PublishJob)
            .join(PublishJob.draft_variant)
            .join(DraftVariant.content_brief)
            .where(
                ContentBrief.account_key == account_key,
                PublishJob.channel == channel,
                PublishJob.state.in_(self._active_states),
            )
            .order_by(
                PublishJob.scheduled_for.is_(None),
                PublishJob.scheduled_for,
                PublishJob.id,
            )
        )
        return list(self.session.scalars(statement))

    def list_approved_without_active_job(
        self,
        account_key: str,
        channel: str,
    ) -> list[DraftVariant]:
        blocking_job_exists = (
            select(PublishJob.id)
            .where(
                PublishJob.draft_variant_id == DraftVariant.id,
                PublishJob.state.in_(self._backfill_blocking_states),
            )
            .exists()
        )
        statement = (
            select(DraftVariant)
            .join(DraftVariant.content_brief)
            .where(
                ContentBrief.account_key == account_key,
                DraftVariant.channel == channel,
                DraftVariant.state == DraftVariantState.APPROVED,
                ~blocking_job_exists,
            )
            .order_by(
                func.coalesce(DraftVariant.reviewed_at, DraftVariant.created_at),
                DraftVariant.created_at,
                DraftVariant.id,
            )
        )
        return list(self.session.scalars(statement))

    def claim_due_job(
        self,
        job_id: int,
        *,
        as_of: datetime,
        claimed_at: datetime | None = None,
    ) -> PublishJob | None:
        event_time = claimed_at or datetime.now(timezone.utc)
        statement = (
            update(PublishJob)
            .where(
                PublishJob.id == job_id,
                PublishJob.state == PublishJobState.SCHEDULED,
                PublishJob.scheduled_for.is_not(None),
                PublishJob.scheduled_for <= as_of,
            )
            .values(
                state=PublishJobState.PUBLISHING,
                attempt_count=PublishJob.attempt_count + 1,
                last_error=None,
                updated_at=event_time,
            )
        )
        result = self.session.execute(statement)
        if result.rowcount != 1:
            return None

        self.session.expire_all()
        return self.get(job_id)

    def has_active_job_for_draft(self, draft_variant_id: int) -> bool:
        statement = select(PublishJob.id).where(
            PublishJob.draft_variant_id == draft_variant_id,
            PublishJob.state.in_(self._active_states),
        )
        return self.session.scalar(statement) is not None

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
        if new_state in (PublishJobState.PUBLISHING, PublishJobState.PUBLISHED):
            self._ensure_draft_is_approved(job)

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

    def _ensure_draft_is_approved(self, job: PublishJob) -> None:
        draft = job.draft_variant
        if draft is None:
            if job.draft_variant_id is None:
                raise ManualApprovalRequiredError("publish jobs require a linked draft variant")
            draft = self.session.get(DraftVariant, job.draft_variant_id)

        if draft is None or draft.state is not DraftVariantState.APPROVED:
            raise ManualApprovalRequiredError(
                "publish jobs require an approved draft variant before scheduling or publishing"
            )

    def ensure_publishable(self, job: PublishJob) -> None:
        self._ensure_draft_is_approved(job)

    def _ensure_idempotency_key(self, job: PublishJob) -> None:
        existing_key = job.idempotency_key.strip() if getattr(job, "idempotency_key", "") else ""
        if existing_key:
            job.idempotency_key = existing_key
            return

        if job.scheduled_for is None:
            raise ValueError("publish jobs require scheduled_for to derive an idempotency key")

        draft_variant_id = job.draft_variant_id
        if draft_variant_id is None and job.draft_variant is not None:
            draft_variant_id = job.draft_variant.id
        if draft_variant_id is None:
            raise ValueError("publish jobs require a persisted draft variant to derive an idempotency key")

        job.idempotency_key = build_publish_job_idempotency_key(
            draft_variant_id=draft_variant_id,
            channel=job.channel,
            scheduled_for=job.scheduled_for,
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


class ReviewActionRepository:
    """Persistence operations for manual review audit rows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, action: ReviewAction) -> ReviewAction:
        self.session.add(action)
        self.session.flush()
        return action

    def get(self, action_id: int) -> ReviewAction | None:
        return self.session.get(ReviewAction, action_id)

    def list(self) -> list[ReviewAction]:
        return list(self.session.scalars(select(ReviewAction).order_by(ReviewAction.id)))

    def list_for_draft(self, draft_variant_id: int) -> Sequence[ReviewAction]:
        statement = select(ReviewAction).where(ReviewAction.draft_variant_id == draft_variant_id).order_by(
            ReviewAction.created_at,
            ReviewAction.id,
        )
        return list(self.session.scalars(statement))

    def record(
        self,
        *,
        draft: DraftVariant,
        action_type: ReviewActionType,
        reviewer: str,
        before_text: str,
        after_text: str,
        draft_state_before: DraftVariantState,
        draft_state_after: DraftVariantState,
        rejection_reason: str | None = None,
        scheduled_for: datetime | None = None,
        publish_job: PublishJob | None = None,
    ) -> ReviewAction:
        action = ReviewAction(
            draft_variant=draft,
            action_type=action_type,
            reviewer=reviewer.strip(),
            before_text=before_text,
            after_text=after_text,
            draft_state_before=draft_state_before,
            draft_state_after=draft_state_after,
            rejection_reason=rejection_reason,
            scheduled_for=scheduled_for,
            publish_job=publish_job,
        )
        self.session.add(action)
        self.session.flush()
        return action
