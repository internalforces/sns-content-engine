"""Tests for draft validation services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import AccountConfig
from app.services import DraftValidator
from app.storage import ContentBrief, DraftVariant, DraftVariantState


def test_draft_validator_accepts_valid_draft_body() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_draft_validator_flags_char_limit_exceeded() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=40),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"max_chars_exceeded"}


def test_draft_validator_flags_link_limit_exceeded() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "AI automation roundup https://gilgop.cloud/ai-tools https://example.com/more",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(max_links=1),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"max_links_exceeded"}


def test_draft_validator_flags_banned_phrase() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "AI automation picks with a risk-free angle https://gilgop.cloud/ai-tools",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(banned_phrases=("risk free",)),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"banned_phrase"}


def test_draft_validator_flags_recent_duplicate_draft() -> None:
    validator = DraftValidator()
    now = datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)
    recent_draft = _build_recent_draft(
        draft_id=7,
        body="Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        created_at=now - timedelta(days=1),
    )

    result = validator.validate(
        " Useful   ai automation workflows for operators https://gilgop.cloud/ai-tools ",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
        recent_drafts=(recent_draft,),
        now=now,
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"recent_duplicate"}


def test_draft_validator_ignores_rejected_and_stale_duplicates() -> None:
    validator = DraftValidator()
    now = datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)
    rejected_draft = _build_recent_draft(
        draft_id=8,
        body="Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        state=DraftVariantState.REJECTED,
        created_at=now - timedelta(days=1),
    )
    stale_draft = _build_recent_draft(
        draft_id=9,
        body="Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        created_at=now - timedelta(days=10),
    )

    result = validator.validate(
        "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
        recent_drafts=(rejected_draft, stale_draft),
        now=now,
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_draft_validator_warns_when_non_strict_topic_guard_misses() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Operator update for general readers https://gilgop.cloud/ai-tools",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(strict_topic_guard=False),
        channel="x",
    )

    assert result.is_valid is True
    assert _issue_codes(result) == {"topic_guard_failed"}
    assert {issue.severity for issue in result.issues} == {"warning"}


def test_draft_validator_errors_when_strict_topic_guard_misses() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Operator update for general readers https://gilgop.cloud/ai-tools",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(strict_topic_guard=True),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"topic_guard_failed"}
    assert {issue.severity for issue in result.issues} == {"error"}


def test_draft_validator_errors_when_finance_profile_misses_topic_guard() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Operator update for general readers https://gilgop.cloud/finance",
        content_brief=_build_content_brief(
            account_key="finance_news_daily",
            landing_url="https://gilgop.cloud/finance",
            tags=("finance", "markets"),
        ),
        account_key="finance_news_daily",
        account=_build_account_config(
            topic="Finance markets and investing",
            profile="finance_strict",
            landing_url="https://gilgop.cloud/finance",
            include_keywords=("earnings", "markets"),
            source_tags=("finance",),
        ),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"topic_guard_failed"}
    assert {issue.severity for issue in result.issues} == {"error"}


def _issue_codes(result) -> set[str]:
    return {issue.code for issue in result.issues}


def _build_account_config(
    *,
    topic: str = "AI tools and workflows",
    landing_url: str = "https://gilgop.cloud/ai-tools",
    max_chars: int = 280,
    max_links: int = 1,
    banned_phrases: tuple[str, ...] = (),
    strict_topic_guard: bool = False,
    profile: str = "standard",
    include_keywords: tuple[str, ...] = ("ai", "automation"),
    source_tags: tuple[str, ...] = ("ai", "automation"),
) -> AccountConfig:
    return AccountConfig(
        topic=topic,
        source_sets=("primary",),
        prompt_profile="default",
        landing={"fallback_url": landing_url, "rules": []},
        matching={
            "include_keywords": list(include_keywords),
            "source_tags": list(source_tags),
            "strict_topic_guard": strict_topic_guard,
        },
        validation={"profile": profile},
        channels={
            "x": {
                "schedule": {"cron": "0 9 * * *"},
                "render": {"max_chars": max_chars},
                "validation": {
                    "max_links": max_links,
                    "banned_phrases": list(banned_phrases),
                    "recent_duplicate_window_days": 7,
                },
            }
        },
    )


def _build_content_brief(
    *,
    account_key: str = "ai_tools_daily",
    landing_url: str = "https://gilgop.cloud/ai-tools",
    tags: tuple[str, ...] = ("ai", "automation"),
) -> ContentBrief:
    return ContentBrief(
        source_item_id=1,
        account_key=account_key,
        title="Useful AI workflow patterns",
        summary="A concise guide for operators.",
        key_points=[
            "Useful AI workflow patterns",
            "Tight review loops",
        ],
        landing_url=landing_url,
        tags=list(tags),
        angle="practical_how_to",
        language="en",
    )


def _build_recent_draft(
    *,
    draft_id: int,
    body: str,
    created_at: datetime,
    state: DraftVariantState = DraftVariantState.PENDING_REVIEW,
) -> DraftVariant:
    return DraftVariant(
        id=draft_id,
        content_brief_id=draft_id,
        content_brief=_build_content_brief(),
        channel="x",
        variant_index=0,
        body=body,
        state=state,
        created_at=created_at,
        updated_at=created_at,
    )
