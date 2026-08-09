"""Validation and serialization helpers for review and manual-publish transitions."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.storage import DraftVariantState, PublishJob, PublishJobState
from app.workflows.review_models import (
    DraftReviewStateError,
    DraftScheduleError,
    ManualPublishError,
    ManualPublishStateError,
    ReviewQueueError,
)

_MANUAL_PUBLISH_CHANNELS = frozenset({"ghost", "linkedin", "threads"})

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


def _require_manual_publish_handoff(
    publish_job: PublishJob,
    *,
    action: str,
) -> None:
    if publish_job.channel not in _MANUAL_PUBLISH_CHANNELS:
        raise ManualPublishError(
            f"publish job {publish_job.id} channel {publish_job.channel!r} "
            "does not support manual publish outcome recording"
        )
    if publish_job.scheduled_for is not None:
        raise ManualPublishError(f"publish job {publish_job.id} is not a manual publish handoff")
    _require_publish_job_state(
        publish_job.id,
        publish_job.state,
        PublishJobState.SCHEDULED,
        action=action,
    )


def _require_publish_job_state(
    publish_job_id: int,
    current_state: PublishJobState,
    expected_state: PublishJobState,
    *,
    action: str,
) -> None:
    if current_state is expected_state:
        return
    raise ManualPublishStateError(
        f"publish job {publish_job_id} cannot {action} from state {current_state.value!r}; "
        f"expected {expected_state.value!r}"
    )


def _require_publish_job_content_brief(publish_job: PublishJob):
    draft = publish_job.draft_variant
    if draft is None:
        raise ReviewQueueError(f"publish job {publish_job.id} is missing its draft variant")

    content_brief = draft.content_brief
    if content_brief is None:
        raise ReviewQueueError(f"publish job {publish_job.id} is missing its content brief")
    return content_brief


def _build_manual_publish_log_payload(
    publish_job: PublishJob,
    *,
    operator: str,
    status: str,
    external_post_id: str | None = None,
    last_error: str | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    content_brief = _require_publish_job_content_brief(publish_job)
    return {
        "status": status,
        "account_key": content_brief.account_key,
        "channel": publish_job.channel,
        "draft_variant_id": publish_job.draft_variant_id,
        "handoff_mode": "manual_upload",
        "operator": operator,
        "attempt_count": publish_job.attempt_count,
        "external_post_id": external_post_id,
        "last_error": last_error,
        "reason": reason,
    }


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


def _build_manual_publish_job_idempotency_key(
    *,
    draft_variant_id: int,
    channel: str,
    created_at: datetime,
) -> str:
    raw_key = f"{draft_variant_id}:{channel.strip()}:manual_handoff:{created_at.isoformat()}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
