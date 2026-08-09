"""Read-only queries for the manual review queue."""

from __future__ import annotations

from app.storage import DraftVariantState, ReviewActionRepository, session_scope
from app.storage.repositories import DraftVariantRepository
from app.workflows.review_models import (
    DraftNotFoundError,
    PendingReviewDraft,
    PendingReviewDraftsResult,
    ReviewDraftDetailResult,
)
from app.workflows.review_persistence import _dispose_engine, _resolve_session_factory


def get_review_draft_detail(
    draft_id: int,
    *,
    database_url: str | None = None,
    session_factory=None,
) -> ReviewDraftDetailResult:
    """Return one draft with linked detail, audit history, and sibling variants."""

    owned_engine, resolved_session_factory = _resolve_session_factory(
        database_url=database_url,
        session_factory=session_factory,
    )
    try:
        with session_scope(resolved_session_factory) as session:
            drafts = DraftVariantRepository(session)
            draft = drafts.get_detail(draft_id)
            if draft is None:
                raise DraftNotFoundError(f"draft {draft_id} was not found")

            review_actions = tuple(ReviewActionRepository(session).list_for_draft(draft_id))
            sibling_variants = tuple(
                sibling
                for sibling in drafts.list_by_content_brief_and_channel(
                    draft.content_brief_id,
                    draft.channel,
                )
                if sibling.id != draft.id
            )
            return ReviewDraftDetailResult(
                draft=draft,
                review_actions=review_actions,
                sibling_variants=sibling_variants,
            )
    finally:
        _dispose_engine(owned_engine)


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
