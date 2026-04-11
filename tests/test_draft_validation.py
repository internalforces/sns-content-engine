"""Tests for draft validation services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import AccountConfig
from app.services import DraftValidator
from app.storage import (
    ArticleEnrichment,
    ContentBrief,
    DraftVariant,
    DraftVariantState,
    SourceItem,
    SourcePolicyMode,
)


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


def test_draft_validator_errors_when_schedule_requires_attribution_but_body_omits_it() -> None:
    validator = DraftValidator()
    content_brief = _build_content_brief(
        require_attribution=True,
        source_name="AI Tools Daily",
    )

    result = validator.validate(
        "Useful AI automation workflows for operators https://example.com/articles/1",
        content_brief=content_brief,
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
        draft=_build_draft_variant(
            body="Useful AI automation workflows for operators https://example.com/articles/1",
            source_name="AI Tools Daily",
        ),
        enforce_policy_requirements=True,
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"required_attribution_missing"}


def test_draft_validator_errors_when_schedule_provenance_is_missing() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
        draft=_build_draft_variant(
            source_name=None,
            source_policy_mode=None,
            source_url=None,
            article_url=None,
        ),
        enforce_policy_requirements=True,
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"review_provenance_missing"}


def test_draft_validator_errors_when_restricted_source_full_text_reuse_is_scheduled() -> None:
    validator = DraftValidator()
    content_brief = _build_content_brief(
        source_policy_mode=SourcePolicyMode.RESTRICTED,
        article_text="Fetched article text from a restricted source.",
    )

    result = validator.validate(
        "Useful AI automation workflows for operators https://example.com/articles/1",
        content_brief=content_brief,
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
        draft=_build_draft_variant(
            source_policy_mode=SourcePolicyMode.RESTRICTED,
        ),
        enforce_policy_requirements=True,
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"restricted_source_full_text_reuse"}


def test_draft_validator_accepts_policy_compliant_schedule_requirements() -> None:
    validator = DraftValidator()
    content_brief = _build_content_brief(
        require_attribution=True,
        source_name="AI Tools Daily",
    )

    result = validator.validate(
        "Useful AI automation workflows from AI Tools Daily https://example.com/articles/1",
        content_brief=content_brief,
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
        draft=_build_draft_variant(
            body="Useful AI automation workflows from AI Tools Daily https://example.com/articles/1",
            source_name="AI Tools Daily",
        ),
        enforce_policy_requirements=True,
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_draft_validator_warns_when_high_risk_finance_topic_is_detected() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Markets update points to a slower inflation print https://gilgop.cloud/finance",
        content_brief=_build_content_brief(
            account_key="finance_news_daily",
            title="Markets react to inflation slowdown",
            summary="Investors are parsing a fresh inflation update.",
            landing_url="https://gilgop.cloud/finance",
            tags=("finance", "markets"),
        ),
        account_key="finance_news_daily",
        account=_build_account_config(
            topic="Finance markets and investing",
            landing_url="https://gilgop.cloud/finance",
            include_keywords=("markets", "inflation"),
            source_tags=("finance",),
        ),
        channel="x",
    )

    assert result.is_valid is True
    assert _issue_codes(result) == {"high_risk_domain"}
    assert {issue.severity for issue in result.issues} == {"warning"}


def test_draft_validator_errors_on_high_risk_finance_claim_language() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Buy now before the next move in markets https://gilgop.cloud/finance",
        content_brief=_build_content_brief(
            account_key="finance_news_daily",
            title="Markets react to inflation slowdown",
            summary="Investors are parsing a fresh inflation update.",
            landing_url="https://gilgop.cloud/finance",
            tags=("finance", "markets"),
        ),
        account_key="finance_news_daily",
        account=_build_account_config(
            topic="Finance markets and investing",
            landing_url="https://gilgop.cloud/finance",
            include_keywords=("markets", "inflation"),
            source_tags=("finance",),
        ),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"high_risk_domain", "high_risk_claim_language"}
    assert {issue.severity for issue in result.errors} == {"error"}


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


def test_draft_validator_flags_missing_expected_landing_url() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Useful AI automation workflows for operators",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"landing_url_missing"}


def test_draft_validator_flags_landing_url_mismatch() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Useful AI automation workflows for operators https://example.com/seo-tool",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"landing_url_mismatch"}


def test_draft_validator_flags_disallowed_landing_prefix() -> None:
    validator = DraftValidator()
    landing_url = "https://odtoolbase.com/tools/seo-audit"

    result = validator.validate(
        f"Useful AI automation workflows for operators {landing_url}",
        content_brief=_build_content_brief(landing_url=landing_url),
        account_key="ai_tools_daily",
        account=_build_account_config(
            landing_url="https://odtoolbase.com/guides",
            allowed_url_prefixes=("https://odtoolbase.com/guides",),
        ),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"landing_url_disallowed"}


def test_draft_validator_flags_unreachable_landing_url_when_required() -> None:
    validator = DraftValidator()
    landing_url = "https://odtoolbase.com/guides/ai-agent-workflows-small-teams"

    result = validator.validate(
        f"Useful AI automation workflows for operators {landing_url}",
        content_brief=_build_content_brief(landing_url=landing_url),
        account_key="ai_tools_daily",
        account=_build_account_config(
            landing_url="https://odtoolbase.com/guides",
            require_live_url=True,
            allowed_url_prefixes=("https://odtoolbase.com/guides",),
        ),
        channel="x",
        landing_url_status_fetcher=lambda _: (_ for _ in ()).throw(OSError("HTTP 404")),
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"landing_url_unreachable"}


def test_draft_validator_accepts_live_landing_url_when_required() -> None:
    validator = DraftValidator()
    landing_url = "https://odtoolbase.com/guides/ai-agent-workflows-small-teams"

    result = validator.validate(
        f"Useful AI automation workflows for operators {landing_url}",
        content_brief=_build_content_brief(landing_url=landing_url),
        account_key="ai_tools_daily",
        account=_build_account_config(
            landing_url="https://odtoolbase.com/guides",
            require_live_url=True,
            allowed_url_prefixes=("https://odtoolbase.com/guides",),
        ),
        channel="x",
        landing_url_status_fetcher=lambda _: 200,
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_draft_validator_accepts_expected_article_url_when_available() -> None:
    validator = DraftValidator()
    content_brief = _build_content_brief(source_name="AI Tools Daily")

    result = validator.validate(
        "Useful AI automation workflows for operators https://example.com/articles/1",
        content_brief=content_brief,
        account_key="ai_tools_daily",
        account=_build_account_config(
            landing_url="https://gilgop.cloud/ai-tools",
            allowed_url_prefixes=("https://gilgop.cloud/ai-tools",),
        ),
        channel="x",
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_draft_validator_flags_mismatched_article_url_when_available() -> None:
    validator = DraftValidator()
    content_brief = _build_content_brief(source_name="AI Tools Daily")

    result = validator.validate(
        "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        content_brief=content_brief,
        account_key="ai_tools_daily",
        account=_build_account_config(
            landing_url="https://gilgop.cloud/ai-tools",
            allowed_url_prefixes=("https://gilgop.cloud/ai-tools",),
        ),
        channel="x",
    )

    assert result.is_valid is False
    assert _issue_codes(result) == {"landing_url_mismatch"}


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
    assert _issue_codes(result) == {"topic_guard_failed", "high_risk_domain"}
    assert {issue.severity for issue in result.errors} == {"error"}


def test_draft_validator_keeps_neutral_topics_free_of_domain_sensitivity_flags() -> None:
    validator = DraftValidator()

    result = validator.validate(
        "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(),
        channel="x",
    )

    assert "high_risk_domain" not in _issue_codes(result)
    assert "high_risk_claim_language" not in _issue_codes(result)


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
    require_live_url: bool = False,
    allowed_url_prefixes: tuple[str, ...] = (),
) -> AccountConfig:
    return AccountConfig(
        topic=topic,
        source_sets=("primary",),
        prompt_profile="default",
        landing={
            "fallback_url": landing_url,
            "rules": [],
            "validation": {
                "require_live_url": require_live_url,
                "allowed_url_prefixes": list(allowed_url_prefixes),
            },
        },
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
    title: str = "Useful AI workflow patterns",
    summary: str = "A concise guide for operators.",
    landing_url: str = "https://gilgop.cloud/ai-tools",
    tags: tuple[str, ...] = ("ai", "automation"),
    source_policy_mode: SourcePolicyMode = SourcePolicyMode.REUSABLE,
    require_attribution: bool = False,
    source_name: str | None = None,
    article_text: str | None = None,
) -> ContentBrief:
    source_item = SourceItem(
        id=1,
        source_key="ai_tools_rss",
        external_id="source-1",
        source_url="https://example.com/articles/1",
        title=title,
        summary=summary,
        policy_mode=source_policy_mode,
        require_attribution=require_attribution,
        published_at=datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc),
    )
    if source_name is not None or article_text is not None:
        source_item.article_enrichment = ArticleEnrichment(
            article_url="https://example.com/articles/1",
            source_name=source_name,
            article_text=article_text,
            fetched_at=datetime(2026, 3, 17, 12, 5, tzinfo=timezone.utc) if article_text else None,
            extracted_at=datetime(2026, 3, 17, 12, 6, tzinfo=timezone.utc) if article_text else None,
            regenerated_summary="Restricted source summary"
            if article_text
            else None,
        )

    return ContentBrief(
        source_item_id=1,
        source_item=source_item,
        account_key=account_key,
        title=title,
        summary=summary,
        key_points=[
            title,
            "Tight review loops",
        ],
        landing_url=landing_url,
        tags=list(tags),
        angle="practical_how_to",
        language="en",
    )


def _build_draft_variant(
    *,
    body: str = "Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
    source_name: str | None = "AI Tools Daily",
    source_url: str | None = "https://example.com/articles/1",
    article_url: str | None = "https://example.com/articles/1",
    source_policy_mode: SourcePolicyMode | None = SourcePolicyMode.REUSABLE,
) -> DraftVariant:
    created_at = datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)
    return DraftVariant(
        id=101,
        content_brief_id=1,
        channel="x",
        variant_index=0,
        body=body,
        source_name=source_name,
        source_url=source_url,
        article_url=article_url,
        source_policy_mode=source_policy_mode,
        state=DraftVariantState.PENDING_REVIEW,
        created_at=created_at,
        updated_at=created_at,
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
