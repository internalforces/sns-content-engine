"""Tests for the manual review queue workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from textwrap import dedent

import pytest

from app.storage import (
    ArticleEnrichment,
    ContentBrief,
    ContentBriefRepository,
    DraftVariant,
    DraftVariantRepository,
    DraftVariantState,
    PublishJobRepository,
    ReviewActionRepository,
    ReviewActionType,
    SourceItem,
    SourcePolicyMode,
    SourceItemRepository,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.workflows import (
    DraftReviewStateError,
    DraftScheduleError,
    DraftValidationFailedError,
    approve_draft,
    edit_draft,
    list_pending_review_drafts,
    reject_draft,
    schedule_draft,
)
from app.workflows.review_queue import get_review_draft_detail

_DRAFT_SOURCE_COUNTER = count()
_VALID_DRAFT_BODY = "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools"


@pytest.fixture
def session_factory(tmp_path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'review-queue.db'}")
    create_all_tables(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    _write_project_config(tmp_path)
    return tmp_path


def test_list_pending_review_drafts_returns_only_pending(session_factory) -> None:
    with session_scope(session_factory) as session:
        pending_draft = _create_draft_variant(session)
        _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        _create_draft_variant(session, draft_state=DraftVariantState.REJECTED)

    result = list_pending_review_drafts(session_factory=session_factory)

    assert result.pending_count == 1
    assert len(result.drafts) == 1
    assert result.drafts[0].draft_id == pending_draft.id
    assert result.drafts[0].account_key == "ai_tools_daily"
    assert result.drafts[0].channel == "x"
    assert result.drafts[0].title == "Brief for draft"


def test_get_review_draft_detail_returns_audit_history_and_sibling_variants(
    session_factory, config_dir
) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session, body=_VALID_DRAFT_BODY)
        draft_id = draft.id

    updated_body = "Updated AI automation operator draft body https://gilgop.cloud/ai-tools"
    edit_draft(
        draft_id,
        body=updated_body,
        reviewer="editor-a",
        config_dir=config_dir,
        session_factory=session_factory,
    )
    approve_draft(
        draft_id,
        reviewer="editor-b",
        config_dir=config_dir,
        session_factory=session_factory,
    )

    with session_scope(session_factory) as session:
        repository = DraftVariantRepository(session)
        stored_draft = repository.get(draft_id)
        assert stored_draft is not None
        repository.add(
            DraftVariant(
                content_brief_id=stored_draft.content_brief_id,
                channel="x",
                variant_index=2,
                body="Variant two for side-by-side comparison",
            )
        )
        repository.add(
            DraftVariant(
                content_brief_id=stored_draft.content_brief_id,
                channel="x",
                variant_index=1,
                body="Variant one for side-by-side comparison",
            )
        )
        repository.add(
            DraftVariant(
                content_brief_id=stored_draft.content_brief_id,
                channel="linkedin",
                variant_index=0,
                body="Different channel comparison variant",
            )
        )

    detail = get_review_draft_detail(draft_id, session_factory=session_factory)

    assert detail.draft.id == draft_id
    assert [action.action_type for action in detail.review_actions] == [
        ReviewActionType.EDIT,
        ReviewActionType.APPROVE,
    ]
    assert detail.review_actions[0].before_text == _VALID_DRAFT_BODY
    assert detail.review_actions[0].after_text == updated_body
    assert [variant.variant_index for variant in detail.sibling_variants] == [1, 2]
    assert [variant.channel for variant in detail.sibling_variants] == ["x", "x"]


def test_approve_draft_updates_state_and_records_review_action(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session)
        draft_id = draft.id

    result = approve_draft(
        draft_id,
        reviewer="editor-a",
        config_dir=config_dir,
        session_factory=session_factory,
    )

    assert result.draft_id == draft_id
    assert result.reviewer == "editor-a"
    assert result.action_type is ReviewActionType.APPROVE
    assert result.draft_state is DraftVariantState.APPROVED

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft_id)
        assert stored_draft is not None
        actions = ReviewActionRepository(session).list_for_draft(draft_id)

    assert stored_draft.state is DraftVariantState.APPROVED
    assert stored_draft.reviewed_at is not None
    assert len(actions) == 1
    assert actions[0].action_type is ReviewActionType.APPROVE
    assert actions[0].before_text == _VALID_DRAFT_BODY
    assert actions[0].after_text == _VALID_DRAFT_BODY
    assert actions[0].draft_state_before is DraftVariantState.PENDING_REVIEW
    assert actions[0].draft_state_after is DraftVariantState.APPROVED


def test_reject_draft_updates_state_and_records_reason(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session)
        draft_id = draft.id

    result = reject_draft(
        draft_id,
        reason="Off topic for this account",
        reviewer="editor-b",
        config_dir=config_dir,
        session_factory=session_factory,
    )

    assert result.action_type is ReviewActionType.REJECT
    assert result.draft_state is DraftVariantState.REJECTED

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft_id)
        assert stored_draft is not None
        actions = ReviewActionRepository(session).list_for_draft(draft_id)

    assert stored_draft.state is DraftVariantState.REJECTED
    assert stored_draft.rejection_reason == "Off topic for this account"
    assert len(actions) == 1
    assert actions[0].rejection_reason == "Off topic for this account"


def test_edit_draft_uses_environment_reviewer_fallback(session_factory, config_dir, monkeypatch) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session)
        draft_id = draft.id

    monkeypatch.setenv("USER", "ops-reviewer")
    result = edit_draft(
        draft_id,
        body="Updated draft body https://gilgop.cloud/ai-tools",
        config_dir=config_dir,
        session_factory=session_factory,
    )

    assert result.reviewer == "ops-reviewer"
    assert result.action_type is ReviewActionType.EDIT
    assert result.draft_state is DraftVariantState.PENDING_REVIEW

    with session_scope(session_factory) as session:
        stored_draft = DraftVariantRepository(session).get(draft_id)
        assert stored_draft is not None
        actions = ReviewActionRepository(session).list_for_draft(draft_id)

    assert stored_draft.body == "Updated draft body https://gilgop.cloud/ai-tools"
    assert stored_draft.reviewed_at is None
    assert len(actions) == 1
    assert actions[0].before_text == _VALID_DRAFT_BODY
    assert actions[0].after_text == "Updated draft body https://gilgop.cloud/ai-tools"
    assert actions[0].draft_state_before is DraftVariantState.PENDING_REVIEW
    assert actions[0].draft_state_after is DraftVariantState.PENDING_REVIEW


def test_schedule_draft_creates_publish_job_and_review_action(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        draft_id = draft.id

    result = schedule_draft(
        draft_id,
        scheduled_for="2026-03-18T09:00:00+09:00",
        reviewer="scheduler-a",
        config_dir=config_dir,
        session_factory=session_factory,
    )

    assert result.action_type is ReviewActionType.SCHEDULE
    assert result.publish_job_id is not None
    assert result.scheduled_for == datetime(2026, 3, 18, 0, 0, tzinfo=timezone.utc)

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session).list()
        actions = ReviewActionRepository(session).list_for_draft(draft_id)

    assert len(jobs) == 1
    assert jobs[0].draft_variant_id == draft_id
    assert jobs[0].scheduled_for == datetime(2026, 3, 18, 0, 0, tzinfo=timezone.utc)
    assert len(actions) == 1
    assert actions[0].publish_job_id == jobs[0].id
    assert actions[0].scheduled_for == datetime(2026, 3, 18, 0, 0, tzinfo=timezone.utc)
    assert actions[0].draft_state_before is DraftVariantState.APPROVED
    assert actions[0].draft_state_after is DraftVariantState.APPROVED


def test_schedule_draft_rejects_missing_required_attribution(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            require_attribution=True,
            body=_VALID_DRAFT_BODY,
        )

    with pytest.raises(DraftValidationFailedError, match="required_attribution_missing"):
        schedule_draft(
            draft.id,
            scheduled_for="2026-03-18T09:00:00+09:00",
            reviewer="scheduler-a",
            config_dir=config_dir,
            session_factory=session_factory,
        )


def test_schedule_draft_rejects_restricted_source_full_text_reuse(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            body="Useful AI automation workflows from AI Tools Daily https://gilgop.cloud/ai-tools",
            policy_mode=SourcePolicyMode.RESTRICTED,
            article_text="Fetched article text from a restricted source.",
        )

    with pytest.raises(DraftValidationFailedError, match="restricted_source_full_text_reuse"):
        schedule_draft(
            draft.id,
            scheduled_for="2026-03-18T09:00:00+09:00",
            reviewer="scheduler-a",
            config_dir=config_dir,
            session_factory=session_factory,
        )


def test_schedule_draft_rejects_missing_review_provenance(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            include_provenance=False,
        )

    with pytest.raises(DraftValidationFailedError, match="review_provenance_missing"):
        schedule_draft(
            draft.id,
            scheduled_for="2026-03-18T09:00:00+09:00",
            reviewer="scheduler-a",
            config_dir=config_dir,
            session_factory=session_factory,
        )


def test_approve_draft_rejects_invalid_body_against_config_rules(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session)
        draft_id = draft.id

    edit_draft(
        draft_id,
        body="Operator update for general readers https://gilgop.cloud/ai-tools",
        reviewer="editor-a",
        config_dir=config_dir,
        session_factory=session_factory,
    )

    with pytest.raises(DraftValidationFailedError, match="topic_guard_failed"):
        approve_draft(
            draft_id,
            reviewer="editor-a",
            config_dir=config_dir,
            session_factory=session_factory,
        )


@pytest.mark.parametrize(
    ("operation", "draft_state", "kwargs", "match"),
    [
        (approve_draft, DraftVariantState.APPROVED, {}, "expected 'pending_review'"),
        (reject_draft, DraftVariantState.REJECTED, {"reason": "Already rejected"}, "expected 'pending_review'"),
        (
            edit_draft,
            DraftVariantState.APPROVED,
            {"body": "Updated body"},
            "expected 'pending_review'",
        ),
        (
            schedule_draft,
            DraftVariantState.PENDING_REVIEW,
            {"scheduled_for": "2026-03-18T09:00:00+00:00"},
            "expected 'approved'",
        ),
    ],
)
def test_review_queue_rejects_invalid_state_operations(
    session_factory,
    config_dir,
    operation,
    draft_state,
    kwargs,
    match,
) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session, draft_state=draft_state)
        draft_id = draft.id

    with pytest.raises(DraftReviewStateError, match=match):
        operation(
            draft_id,
            reviewer="editor-a",
            config_dir=config_dir,
            session_factory=session_factory,
            **kwargs,
        )


def test_schedule_draft_rejects_duplicate_active_jobs(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        draft_id = draft.id

    schedule_draft(
        draft_id,
        scheduled_for="2026-03-18T09:00:00+00:00",
        reviewer="scheduler-a",
        config_dir=config_dir,
        session_factory=session_factory,
    )

    with pytest.raises(DraftScheduleError, match="already has an active publish job"):
        schedule_draft(
            draft_id,
            scheduled_for="2026-03-18T10:00:00+00:00",
            reviewer="scheduler-a",
            config_dir=config_dir,
            session_factory=session_factory,
        )


def test_schedule_draft_rejects_naive_datetimes(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)

    with pytest.raises(DraftScheduleError, match="timezone offset"):
        schedule_draft(
            draft.id,
            scheduled_for="2026-03-18T09:00:00",
            reviewer="scheduler-a",
            config_dir=config_dir,
            session_factory=session_factory,
        )


def _create_draft_variant(
    session,
    *,
    draft_state: DraftVariantState = DraftVariantState.PENDING_REVIEW,
    body: str = _VALID_DRAFT_BODY,
    policy_mode: SourcePolicyMode = SourcePolicyMode.REUSABLE,
    require_attribution: bool = False,
    source_name: str | None = "AI Tools Daily",
    source_url: str | None = None,
    article_url: str | None = None,
    source_published_at: datetime | None = None,
    article_text: str | None = None,
    include_provenance: bool = True,
) -> DraftVariant:
    source_id = next(_DRAFT_SOURCE_COUNTER)
    resolved_source_url = source_url or f"https://example.com/review-draft/{source_id}"
    resolved_article_url = article_url or resolved_source_url
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"review-draft-{source_id}",
            source_url=resolved_source_url,
            title=f"Review draft {source_id}",
            summary="Brief summary",
            policy_mode=policy_mode,
            require_attribution=require_attribution,
            published_at=source_published_at or datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc),
        )
    )
    if article_text is not None:
        source_item.article_enrichment = ArticleEnrichment(
            article_url=resolved_article_url,
            source_name=source_name,
            article_text=article_text,
            fetched_at=datetime(2026, 3, 17, 12, 5, tzinfo=timezone.utc),
            extracted_at=datetime(2026, 3, 17, 12, 6, tzinfo=timezone.utc),
            regenerated_summary="Restricted source summary",
        )
    brief = ContentBriefRepository(session).add(
        ContentBrief(
            source_item=source_item,
            account_key="ai_tools_daily",
            title="Brief for draft",
            summary="Brief summary",
            key_points=["Brief for draft"],
            landing_url="https://gilgop.cloud/ai-tools",
            tags=["ai"],
            angle="topic_takeaway",
            language="en",
        )
    )
    repository = DraftVariantRepository(session)
    draft = repository.add(
        DraftVariant(
            content_brief=brief,
            channel="x",
            variant_index=0,
            body=body,
            source_name=source_name if include_provenance else None,
            source_url=resolved_source_url if include_provenance else None,
            article_url=resolved_article_url if include_provenance else None,
            source_published_at=source_item.published_at if include_provenance else None,
            source_policy_mode=policy_mode if include_provenance else None,
        )
    )
    if draft_state is DraftVariantState.APPROVED:
        repository.transition_state(draft, DraftVariantState.APPROVED)
    elif draft_state is DraftVariantState.REJECTED:
        repository.transition_state(
            draft,
            DraftVariantState.REJECTED,
            rejection_reason="Rejected during test setup",
        )
    return draft


def _write_project_config(path: Path) -> None:
    _write_file(
        path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            matching:
              include_keywords:
                - ai
                - automation
              source_tags:
                - ai
                - automation
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
                validation:
                  max_links: 1
                  banned_phrases: []
                  recent_duplicate_window_days: 7
        """,
    )
    _write_file(
        path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: "System for {{ account_key }} on {{ channel }}"
            user_template: "Write about {{ title }} and use {{ landing_url }}"
        """,
    )
    _write_file(
        path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """,
    )


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
