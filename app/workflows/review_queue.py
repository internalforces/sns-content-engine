"""Workflow helpers for the manual review queue."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from app.storage import (
    DraftVariantState,
    PublishJob,
    PublishJobRepository,
    ReviewActionRepository,
    ReviewActionType,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)
from app.storage.repositories import DraftVariantRepository


class ReviewQueueError(ValueError):
    """Base error for manual review workflow failures."""


class DraftNotFoundError(ReviewQueueError):
    """Raised when a referenced draft does not exist."""


class ReviewerIdentityError(ReviewQueueError):
    """Raised when no reviewer identity can be resolved."""


class DraftReviewStateError(ReviewQueueError):
    """Raised when a review action is attempted from the wrong state."""


class DraftScheduleError(ReviewQueueError):
    """Raised when scheduling validation fails."""


@dataclass(frozen=True, slots=True)
class PendingReviewDraft:
    """Serialized draft row for review queue listing."""

    draft_id: int
    account_key: str
    channel: str
    variant_index: int
    created_at: datetime
    title: str
    body: str


@dataclass(frozen=True, slots=True)
class PendingReviewDraftsResult:
    """Aggregated pending review queue result."""

    drafts: tuple[PendingReviewDraft, ...]

    @property
    def pending_count(self) -> int:
        """Return the number of drafts awaiting review."""

        return len(self.drafts)


@dataclass(frozen=True, slots=True)
class ReviewDraftResult:
    """Outcome of a review queue mutation."""

    draft_id: int
    reviewer: str
    action_type: ReviewActionType
    draft_state: DraftVariantState
    action_id: int
    publish_job_id: int | None = None
    scheduled_for: datetime | None = None


def list_pending_review_drafts(
    *,
    database_url: str | None = None,
    session_factory=None,
) -> PendingReviewDraftsResult:
    """Return pending drafts in review order."""

    owned_engine, resolved_session_factory = _resolve_session_factory(
        database_url=database_url,
        session_factory=session_factory,
    )
    try:
        with session_scope(resolved_session_factory) as session:
            drafts = DraftVariantRepository(session).list_by_state(DraftVariantState.PENDING_REVIEW)
            items = tuple(
                PendingReviewDraft(
                    draft_id=draft.id,
                    account_key=draft.content_brief.account_key,
                    channel=draft.channel,
                    variant_index=draft.variant_index,
                    created_at=draft.created_at,
                    title=draft.content_brief.title,
                    body=draft.body,
                )
                for draft in drafts
            )
    finally:
        _dispose_engine(owned_engine)

    return PendingReviewDraftsResult(drafts=items)


def approve_draft(
    draft_id: int,
    *,
    reviewer: str | None = None,
    database_url: str | None = None,
    session_factory=None,
) -> ReviewDraftResult:
    """Approve a pending draft and record the audit trail."""

    return _run_review_action(
        draft_id,
        reviewer=reviewer,
        database_url=database_url,
        session_factory=session_factory,
        handler=_approve_draft,
    )


def reject_draft(
    draft_id: int,
    *,
    reason: str,
    reviewer: str | None = None,
    database_url: str | None = None,
    session_factory=None,
) -> ReviewDraftResult:
    """Reject a pending draft and record the audit trail."""

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ReviewQueueError("rejection reason must not be empty")

    return _run_review_action(
        draft_id,
        reviewer=reviewer,
        database_url=database_url,
        session_factory=session_factory,
        handler=lambda session, draft, reviewer_name: _reject_draft(
            session,
            draft,
            reviewer_name,
            reason=normalized_reason,
        ),
    )


def edit_draft(
    draft_id: int,
    *,
    body: str,
    reviewer: str | None = None,
    database_url: str | None = None,
    session_factory=None,
) -> ReviewDraftResult:
    """Edit a pending draft body and record the audit trail."""

    normalized_body = body.strip()
    if not normalized_body:
        raise ReviewQueueError("edited draft body must not be empty")

    return _run_review_action(
        draft_id,
        reviewer=reviewer,
        database_url=database_url,
        session_factory=session_factory,
        handler=lambda session, draft, reviewer_name: _edit_draft(
            session,
            draft,
            reviewer_name,
            body=normalized_body,
        ),
    )


def schedule_draft(
    draft_id: int,
    *,
    scheduled_for: str | datetime,
    reviewer: str | None = None,
    database_url: str | None = None,
    session_factory=None,
) -> ReviewDraftResult:
    """Create a publish job for an approved draft."""

    normalized_scheduled_for = _parse_scheduled_for(scheduled_for)
    return _run_review_action(
        draft_id,
        reviewer=reviewer,
        database_url=database_url,
        session_factory=session_factory,
        handler=lambda session, draft, reviewer_name: _schedule_draft(
            session,
            draft,
            reviewer_name,
            scheduled_for=normalized_scheduled_for,
        ),
    )


def resolve_reviewer_identity(reviewer: str | None = None) -> str:
    """Resolve the reviewer name from explicit input or the local environment."""

    if reviewer is not None and reviewer.strip():
        return reviewer.strip()

    for env_name in ("USER", "USERNAME"):
        env_value = os.environ.get(env_name, "").strip()
        if env_value:
            return env_value

    raise ReviewerIdentityError("reviewer identity is required; pass --reviewer or set USER/USERNAME")


def _approve_draft(session, draft, reviewer: str) -> ReviewDraftResult:
    _require_draft_state(draft.id, draft.state, DraftVariantState.PENDING_REVIEW, action="approve")

    drafts = DraftVariantRepository(session)
    before_state = draft.state
    before_text = draft.body
    drafts.transition_state(draft, DraftVariantState.APPROVED)
    action = ReviewActionRepository(session).record(
        draft=draft,
        action_type=ReviewActionType.APPROVE,
        reviewer=reviewer,
        before_text=before_text,
        after_text=draft.body,
        draft_state_before=before_state,
        draft_state_after=draft.state,
    )
    return ReviewDraftResult(
        draft_id=draft.id,
        reviewer=reviewer,
        action_type=ReviewActionType.APPROVE,
        draft_state=draft.state,
        action_id=action.id,
    )


def _reject_draft(session, draft, reviewer: str, *, reason: str) -> ReviewDraftResult:
    _require_draft_state(draft.id, draft.state, DraftVariantState.PENDING_REVIEW, action="reject")

    drafts = DraftVariantRepository(session)
    before_state = draft.state
    before_text = draft.body
    drafts.transition_state(
        draft,
        DraftVariantState.REJECTED,
        rejection_reason=reason,
    )
    action = ReviewActionRepository(session).record(
        draft=draft,
        action_type=ReviewActionType.REJECT,
        reviewer=reviewer,
        before_text=before_text,
        after_text=draft.body,
        draft_state_before=before_state,
        draft_state_after=draft.state,
        rejection_reason=reason,
    )
    return ReviewDraftResult(
        draft_id=draft.id,
        reviewer=reviewer,
        action_type=ReviewActionType.REJECT,
        draft_state=draft.state,
        action_id=action.id,
    )


def _edit_draft(session, draft, reviewer: str, *, body: str) -> ReviewDraftResult:
    _require_draft_state(draft.id, draft.state, DraftVariantState.PENDING_REVIEW, action="edit")

    before_text = draft.body
    draft.body = body
    session.flush()
    action = ReviewActionRepository(session).record(
        draft=draft,
        action_type=ReviewActionType.EDIT,
        reviewer=reviewer,
        before_text=before_text,
        after_text=draft.body,
        draft_state_before=draft.state,
        draft_state_after=draft.state,
    )
    return ReviewDraftResult(
        draft_id=draft.id,
        reviewer=reviewer,
        action_type=ReviewActionType.EDIT,
        draft_state=draft.state,
        action_id=action.id,
    )


def _schedule_draft(session, draft, reviewer: str, *, scheduled_for: datetime) -> ReviewDraftResult:
    _require_draft_state(draft.id, draft.state, DraftVariantState.APPROVED, action="schedule")

    publish_jobs = PublishJobRepository(session)
    if publish_jobs.has_active_job_for_draft(draft.id):
        raise DraftScheduleError(f"draft {draft.id} already has an active publish job")

    job = publish_jobs.add(
        PublishJob(
            draft_variant=draft,
            channel=draft.channel,
            scheduled_for=scheduled_for,
        )
    )
    action = ReviewActionRepository(session).record(
        draft=draft,
        action_type=ReviewActionType.SCHEDULE,
        reviewer=reviewer,
        before_text=draft.body,
        after_text=draft.body,
        draft_state_before=draft.state,
        draft_state_after=draft.state,
        scheduled_for=job.scheduled_for,
        publish_job=job,
    )
    return ReviewDraftResult(
        draft_id=draft.id,
        reviewer=reviewer,
        action_type=ReviewActionType.SCHEDULE,
        draft_state=draft.state,
        action_id=action.id,
        publish_job_id=job.id,
        scheduled_for=job.scheduled_for,
    )


def _run_review_action(
    draft_id: int,
    *,
    reviewer: str | None,
    database_url: str | None,
    session_factory,
    handler,
) -> ReviewDraftResult:
    owned_engine, resolved_session_factory = _resolve_session_factory(
        database_url=database_url,
        session_factory=session_factory,
    )
    try:
        reviewer_name = resolve_reviewer_identity(reviewer)
        with session_scope(resolved_session_factory) as session:
            draft = DraftVariantRepository(session).get(draft_id)
            if draft is None:
                raise DraftNotFoundError(f"draft {draft_id} was not found")
            return handler(session, draft, reviewer_name)
    finally:
        _dispose_engine(owned_engine)


def _require_draft_state(
    draft_id: int,
    current_state: DraftVariantState,
    expected_state: DraftVariantState,
    *,
    action: str,
) -> None:
    if current_state is expected_state:
        return
    action_labels = {
        "approve": "approved",
        "reject": "rejected",
        "edit": "edited",
        "schedule": "scheduled",
    }
    action_label = action_labels.get(action, action)
    raise DraftReviewStateError(
        f"draft {draft_id} cannot be {action_label} from state {current_state.value!r}; "
        f"expected {expected_state.value!r}"
    )


def _parse_scheduled_for(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        scheduled_for = value
    else:
        raw_value = value.strip()
        if not raw_value:
            raise DraftScheduleError("scheduled_for must not be empty")
        try:
            scheduled_for = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise DraftScheduleError(
                "scheduled_for must be a valid ISO 8601 datetime"
            ) from exc

    if scheduled_for.tzinfo is None:
        raise DraftScheduleError("scheduled_for must include a timezone offset")

    return scheduled_for.astimezone(timezone.utc)


def _resolve_session_factory(*, database_url: str | None, session_factory):
    owned_engine = None
    if session_factory is None:
        owned_engine = create_database_engine(database_url)
        ensure_database_schema_is_current(owned_engine)
        return owned_engine, create_session_factory(owned_engine)

    bound_engine = getattr(session_factory, "kw", {}).get("bind")
    if bound_engine is not None:
        ensure_database_schema_is_current(bound_engine)
    return owned_engine, session_factory


def _dispose_engine(engine) -> None:
    if engine is not None:
        engine.dispose()
