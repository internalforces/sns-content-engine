"""Workflow helpers for the manual review queue."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.config import ConfigRegistry
from app.connectors.publishers.resolver import channel_requires_manual_publish_handoff
from app.services import DraftValidator
from app.storage import (
    DraftVariant,
    DraftVariantState,
    PublishJob,
    PublishJobRepository,
    PublishJobState,
    PublishLogRepository,
    ReviewAction,
    ReviewActionRepository,
    ReviewActionType,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)
from app.storage.repositories import DraftVariantRepository
from app.workflows.history_queries import PublishJobNotFoundError
from app.workflows.review_models import (
    DraftNotFoundError,
    DraftReviewStateError,
    DraftScheduleError,
    DraftValidationFailedError,
    ManualPublishError,
    ManualPublishOutcomeResult,
    ManualPublishStateError,
    PendingReviewDraft,
    PendingReviewDraftsResult,
    ReviewDraftDetailResult,
    ReviewDraftResult,
    ReviewerIdentityError,
    ReviewQueueError,
)
from app.workflows.review_persistence import _dispose_engine, _resolve_session_factory
from app.workflows.review_queries import get_review_draft_detail, list_pending_review_drafts
from app.workflows.review_support import (
    _build_manual_publish_job_idempotency_key,
    _build_manual_publish_log_payload,
    _parse_scheduled_for,
    _require_draft_state,
    _require_manual_publish_handoff,
    _require_publish_job_content_brief,
    _require_publish_job_state,
)


def approve_draft(
    draft_id: int,
    *,
    reviewer: str | None = None,
    config_dir: Path | str = Path("config"),
    database_url: str | None = None,
    session_factory=None,
) -> ReviewDraftResult:
    """Approve a pending draft and record the audit trail."""

    return _run_review_action(
        draft_id,
        reviewer=reviewer,
        database_url=database_url,
        session_factory=session_factory,
        handler=lambda session, draft, reviewer_name: _approve_draft(
            session,
            draft,
            reviewer_name,
            config_dir=config_dir,
        ),
    )


def reject_draft(
    draft_id: int,
    *,
    reason: str,
    reviewer: str | None = None,
    config_dir: Path | str = Path("config"),
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
    config_dir: Path | str = Path("config"),
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
    config_dir: Path | str = Path("config"),
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
            config_dir=config_dir,
            scheduled_for=normalized_scheduled_for,
        ),
    )


def complete_manual_publish_handoff(
    publish_job_id: int,
    *,
    operator: str | None = None,
    external_post_id: str | None = None,
    database_url: str | None = None,
    session_factory=None,
) -> ManualPublishOutcomeResult:
    """Record a successful manual publish outcome for a non-X handoff."""

    normalized_external_post_id = external_post_id.strip() if external_post_id else None
    return _run_manual_publish_action(
        publish_job_id,
        operator=operator,
        database_url=database_url,
        session_factory=session_factory,
        handler=lambda session, job, operator_name: _complete_manual_publish_handoff(
            session,
            job,
            operator_name,
            external_post_id=normalized_external_post_id,
        ),
    )


def fail_manual_publish_handoff(
    publish_job_id: int,
    *,
    error_message: str,
    operator: str | None = None,
    database_url: str | None = None,
    session_factory=None,
) -> ManualPublishOutcomeResult:
    """Record a failed manual publish outcome for a non-X handoff."""

    normalized_error_message = error_message.strip()
    if not normalized_error_message:
        raise ManualPublishError("manual publish failure message must not be empty")

    return _run_manual_publish_action(
        publish_job_id,
        operator=operator,
        database_url=database_url,
        session_factory=session_factory,
        handler=lambda session, job, operator_name: _fail_manual_publish_handoff(
            session,
            job,
            operator_name,
            error_message=normalized_error_message,
        ),
    )


def cancel_manual_publish_handoff(
    publish_job_id: int,
    *,
    operator: str | None = None,
    reason: str | None = None,
    database_url: str | None = None,
    session_factory=None,
) -> ManualPublishOutcomeResult:
    """Cancel an open manual publish handoff for a non-X channel."""

    normalized_reason = reason.strip() if reason is not None and reason.strip() else None
    return _run_manual_publish_action(
        publish_job_id,
        operator=operator,
        database_url=database_url,
        session_factory=session_factory,
        handler=lambda session, job, operator_name: _cancel_manual_publish_handoff(
            session,
            job,
            operator_name,
            reason=normalized_reason,
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


def _approve_draft(session, draft, reviewer: str, *, config_dir: Path | str) -> ReviewDraftResult:
    _require_draft_state(draft.id, draft.state, DraftVariantState.PENDING_REVIEW, action="approve")
    use_manual_publish_handoff = _draft_uses_manual_publish_handoff(
        draft,
        config_dir=config_dir,
    )
    _validate_draft_for_review(
        session,
        draft,
        config_dir=config_dir,
        validation_label="approval",
        enforce_policy_requirements=use_manual_publish_handoff,
    )

    drafts = DraftVariantRepository(session)
    before_state = draft.state
    before_text = draft.body
    drafts.transition_state(draft, DraftVariantState.APPROVED)
    publish_job = (
        _create_manual_publish_handoff(session, draft)
        if use_manual_publish_handoff
        else None
    )
    action = ReviewActionRepository(session).record(
        draft=draft,
        action_type=ReviewActionType.APPROVE,
        reviewer=reviewer,
        before_text=before_text,
        after_text=draft.body,
        draft_state_before=before_state,
        draft_state_after=draft.state,
        publish_job=publish_job,
    )
    return ReviewDraftResult(
        draft_id=draft.id,
        channel=draft.channel,
        reviewer=reviewer,
        action_type=ReviewActionType.APPROVE,
        draft_state=draft.state,
        action_id=action.id,
        publish_job_id=publish_job.id if publish_job is not None else None,
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
        channel=draft.channel,
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
        channel=draft.channel,
        reviewer=reviewer,
        action_type=ReviewActionType.EDIT,
        draft_state=draft.state,
        action_id=action.id,
    )


def _schedule_draft(
    session,
    draft,
    reviewer: str,
    *,
    config_dir: Path | str,
    scheduled_for: datetime,
) -> ReviewDraftResult:
    _require_draft_state(draft.id, draft.state, DraftVariantState.APPROVED, action="schedule")
    if _draft_uses_manual_publish_handoff(draft, config_dir=config_dir):
        raise DraftScheduleError(
            f"draft {draft.id} channel {draft.channel!r} uses manual publish handoff instead of scheduled publishing"
        )
    _validate_draft_for_review(
        session,
        draft,
        config_dir=config_dir,
        validation_label="schedule",
        enforce_policy_requirements=True,
    )

    publish_jobs = PublishJobRepository(session)
    if publish_jobs.has_active_job_for_draft(draft.id):
        raise DraftScheduleError(f"draft {draft.id} already has an active publish job")

    try:
        job = publish_jobs.add(
            PublishJob(
                draft_variant=draft,
                channel=draft.channel,
                scheduled_for=scheduled_for,
            )
        )
    except IntegrityError as exc:
        raise DraftScheduleError(f"draft {draft.id} already has an active publish job") from exc
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
        channel=draft.channel,
        reviewer=reviewer,
        action_type=ReviewActionType.SCHEDULE,
        draft_state=draft.state,
        action_id=action.id,
        publish_job_id=job.id,
        scheduled_for=job.scheduled_for,
    )


def _create_manual_publish_handoff(session, draft) -> PublishJob:
    content_brief = draft.content_brief
    if content_brief is None:
        raise ReviewQueueError(f"draft {draft.id} is missing its content brief")

    publish_jobs = PublishJobRepository(session)
    if publish_jobs.has_active_job_for_draft(draft.id):
        raise ReviewQueueError(f"draft {draft.id} already has an active publish job")

    handoff_created_at = datetime.now(timezone.utc)
    publish_job = publish_jobs.add(
        PublishJob(
            draft_variant=draft,
            channel=draft.channel,
            idempotency_key=_build_manual_publish_job_idempotency_key(
                draft_variant_id=draft.id,
                channel=draft.channel,
                created_at=handoff_created_at,
            ),
            created_at=handoff_created_at,
        )
    )
    PublishLogRepository(session).record(
        publish_job=publish_job,
        event_type="manual_handoff_created",
        message=(
            f"manual publish handoff created for {content_brief.account_key}/{draft.channel} "
            f"draft {draft.id}"
        ),
        payload={
            "account_key": content_brief.account_key,
            "channel": draft.channel,
            "draft_variant_id": draft.id,
            "handoff_mode": "manual_upload",
            "scheduled_for": None,
        },
    )
    return publish_job


def _draft_uses_manual_publish_handoff(draft, *, config_dir: Path | str) -> bool:
    content_brief = draft.content_brief
    if content_brief is None:
        raise ReviewQueueError(f"draft {draft.id} is missing its content brief")

    return channel_requires_manual_publish_handoff(
        config_dir=config_dir,
        account_key=content_brief.account_key,
        channel=draft.channel,
    )


def _complete_manual_publish_handoff(
    session,
    publish_job: PublishJob,
    operator: str,
    *,
    external_post_id: str | None,
) -> ManualPublishOutcomeResult:
    previous_state = publish_job.state
    _require_manual_publish_handoff(
        publish_job,
        action="record manual publish completion",
    )

    publish_jobs = PublishJobRepository(session)
    publish_jobs.transition_state(publish_job, PublishJobState.PUBLISHING)
    publish_jobs.transition_state(
        publish_job,
        PublishJobState.PUBLISHED,
        external_post_id=external_post_id,
    )

    content_brief = _require_publish_job_content_brief(publish_job)
    PublishLogRepository(session).record(
        publish_job=publish_job,
        event_type="published",
        message=(
            f"manual publish recorded as published by {operator} for "
            f"{content_brief.account_key}/{publish_job.channel} draft {publish_job.draft_variant_id}"
        ),
        payload=_build_manual_publish_log_payload(
            publish_job,
            operator=operator,
            status="published",
            external_post_id=publish_job.external_post_id,
        ),
    )
    return ManualPublishOutcomeResult(
        publish_job_id=publish_job.id,
        channel=publish_job.channel,
        operator=operator,
        previous_state=previous_state,
        publish_job_state=publish_job.state,
        external_post_id=publish_job.external_post_id,
        published_at=publish_job.published_at,
    )


def _fail_manual_publish_handoff(
    session,
    publish_job: PublishJob,
    operator: str,
    *,
    error_message: str,
) -> ManualPublishOutcomeResult:
    previous_state = publish_job.state
    _require_manual_publish_handoff(
        publish_job,
        action="record manual publish failure",
    )

    publish_jobs = PublishJobRepository(session)
    publish_jobs.transition_state(publish_job, PublishJobState.PUBLISHING)
    publish_jobs.transition_state(
        publish_job,
        PublishJobState.FAILED,
        last_error=error_message,
    )

    content_brief = _require_publish_job_content_brief(publish_job)
    PublishLogRepository(session).record(
        publish_job=publish_job,
        event_type="failed",
        message=(
            f"manual publish recorded as failed by {operator} for "
            f"{content_brief.account_key}/{publish_job.channel} draft {publish_job.draft_variant_id}: "
            f"{error_message}"
        ),
        payload=_build_manual_publish_log_payload(
            publish_job,
            operator=operator,
            status="failed",
            last_error=publish_job.last_error,
        ),
    )
    return ManualPublishOutcomeResult(
        publish_job_id=publish_job.id,
        channel=publish_job.channel,
        operator=operator,
        previous_state=previous_state,
        publish_job_state=publish_job.state,
        last_error=publish_job.last_error,
    )


def _cancel_manual_publish_handoff(
    session,
    publish_job: PublishJob,
    operator: str,
    *,
    reason: str | None,
) -> ManualPublishOutcomeResult:
    previous_state = publish_job.state
    _require_manual_publish_handoff(
        publish_job,
        action="cancel manual publish handoff",
    )

    publish_jobs = PublishJobRepository(session)
    publish_jobs.transition_state(publish_job, PublishJobState.CANCELLED)

    content_brief = _require_publish_job_content_brief(publish_job)
    PublishLogRepository(session).record(
        publish_job=publish_job,
        event_type="cancelled",
        message=(
            f"manual publish handoff cancelled by {operator} for "
            f"{content_brief.account_key}/{publish_job.channel} draft {publish_job.draft_variant_id}"
            f"{': ' + reason if reason else ''}"
        ),
        payload=_build_manual_publish_log_payload(
            publish_job,
            operator=operator,
            status="cancelled",
            reason=reason,
        ),
    )
    return ManualPublishOutcomeResult(
        publish_job_id=publish_job.id,
        channel=publish_job.channel,
        operator=operator,
        previous_state=previous_state,
        publish_job_state=publish_job.state,
    )


def _validate_draft_for_review(
    session,
    draft,
    *,
    config_dir: Path | str,
    validation_label: str,
    enforce_policy_requirements: bool = False,
) -> None:
    content_brief = draft.content_brief
    if content_brief is None:
        raise ReviewQueueError(f"draft {draft.id} is missing its content brief")

    registry = ConfigRegistry.from_directory(Path(config_dir))
    account_key = content_brief.account_key
    try:
        account = registry.get_account(account_key)
    except KeyError as exc:
        raise ReviewQueueError(
            f"draft {draft.id} references unknown account {account_key!r}"
        ) from exc

    if draft.channel not in account.channels:
        raise ReviewQueueError(
            f"draft {draft.id} references channel {draft.channel!r} missing from account {account_key!r}"
        )

    duplicate_window_days = account.channels[draft.channel].validation.recent_duplicate_window_days
    now = datetime.now(timezone.utc)
    recent_drafts = DraftVariantRepository(session).list_recent_by_account_and_channel(
        account_key,
        draft.channel,
        created_since=now - timedelta(days=duplicate_window_days),
        exclude_draft_id=draft.id,
    )
    validation = DraftValidator().validate(
        draft.body,
        content_brief=content_brief,
        account_key=account_key,
        account=account,
        channel=draft.channel,
        recent_drafts=recent_drafts,
        draft_id=draft.id,
        now=now,
        draft=draft,
        enforce_policy_requirements=enforce_policy_requirements,
    )
    if validation.is_valid:
        return

    messages = "; ".join(f"{issue.code}: {issue.message}" for issue in validation.errors)
    raise DraftValidationFailedError(f"draft {draft.id} failed {validation_label} validation: {messages}")


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

def _run_manual_publish_action(
    publish_job_id: int,
    *,
    operator: str | None,
    database_url: str | None,
    session_factory,
    handler,
) -> ManualPublishOutcomeResult:
    owned_engine, resolved_session_factory = _resolve_session_factory(
        database_url=database_url,
        session_factory=session_factory,
    )
    try:
        operator_name = resolve_reviewer_identity(operator)
        with session_scope(resolved_session_factory) as session:
            publish_job = PublishJobRepository(session).get_detail(publish_job_id)
            if publish_job is None:
                raise PublishJobNotFoundError(f"publish job {publish_job_id} was not found")
            return handler(session, publish_job, operator_name)
    finally:
        _dispose_engine(owned_engine)
