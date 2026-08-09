"""Errors and immutable result contracts for manual review workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.storage import (
    DraftVariant,
    DraftVariantState,
    PublishJobState,
    ReviewAction,
    ReviewActionType,
)


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


class DraftValidationFailedError(ReviewQueueError):
    """Raised when a draft fails the approval/publish validator."""


class ManualPublishError(ReviewQueueError):
    """Raised when a manual publish handoff update is invalid."""


class ManualPublishStateError(ManualPublishError):
    """Raised when a manual publish outcome is attempted from the wrong state."""


_MANUAL_PUBLISH_CHANNELS = frozenset({"ghost", "linkedin", "threads"})


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
    channel: str | None = None
    publish_job_id: int | None = None
    scheduled_for: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReviewDraftDetailResult:
    """Serialized draft detail with related audit history and sibling variants."""

    draft: DraftVariant
    review_actions: tuple[ReviewAction, ...]
    sibling_variants: tuple[DraftVariant, ...]


@dataclass(frozen=True, slots=True)
class ManualPublishOutcomeResult:
    """Outcome of a manual publish handoff update."""

    publish_job_id: int
    channel: str
    operator: str
    previous_state: PublishJobState
    publish_job_state: PublishJobState
    external_post_id: str | None = None
    last_error: str | None = None
    published_at: datetime | None = None
