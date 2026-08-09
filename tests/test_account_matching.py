"""Tests for deterministic account matching."""

from __future__ import annotations

from pathlib import Path

from app.config import AccountConfig, ConfigRegistry
from app.domain import AccountMatchCandidate, SourceItemCandidate, select_top_account_candidates
from app.services import AccountMatcher
from app.services.topic_matching import topic_keywords

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_matcher_selects_expected_top_account_for_ai_finance_and_seo_items() -> None:
    matcher = AccountMatcher(_sample_accounts())

    ai_item = _build_candidate(
        title="New AI agent automates customer support",
        summary="Automation workflow for small teams",
        source_tags=("ai", "automation"),
    )
    finance_item = _build_candidate(
        title="Stock market earnings outlook for tech investors",
        summary="Finance desks track macro and investing moves",
        source_tags=("finance", "markets"),
    )
    seo_item = _build_candidate(
        title="SEO tool improves search ranking with backlink audits",
        summary="Search optimization workflow for growth teams",
        source_tags=("seo", "search"),
    )

    assert _top_account_keys(matcher.match_source_item(ai_item)) == ("ai_tools_daily",)
    assert _top_account_keys(matcher.match_source_item(finance_item)) == (
        "finance_news_daily",
    )
    assert _top_account_keys(matcher.match_source_item(seo_item)) == ("seo_tools_daily",)


def test_matcher_can_return_multiple_positive_account_candidates() -> None:
    matcher = AccountMatcher(_sample_accounts())
    item = _build_candidate(
        title="AI SEO agent improves search ranking automation",
        summary="Search optimization playbook for AI-first teams",
        source_tags=("ai", "seo", "search"),
    )

    candidates = matcher.match_source_item(item)
    positive_accounts = tuple(candidate.account_key for candidate in candidates if candidate.eligible)

    assert positive_accounts == (
        "seo_tools_daily",
        "ai_tools_daily",
    )
    assert _top_account_keys(candidates) == ("seo_tools_daily",)


def test_matcher_blocks_generic_keyword_hits_when_strict_topic_guard_fails() -> None:
    matcher = AccountMatcher(
        {
            "ai_tools_daily": _build_account(
                topic="AI tools and workflows",
                include_keywords=("automation",),
                strict_topic_guard=True,
            )
        }
    )
    item = _build_candidate(
        title="Finance automation checklist for operators",
        summary="A process guide for treasury teams",
        source_tags=("finance",),
    )

    candidate = matcher.match_source_item(item)[0]

    assert candidate.eligible is False
    assert candidate.score == 0
    assert candidate.include_keyword_hits == ("automation",)
    assert candidate.blocked_by_topic_guard is True


def test_matcher_uses_exclude_keywords_to_zero_out_a_candidate() -> None:
    matcher = AccountMatcher(
        {
            "ai_tools_daily": _build_account(
                topic="AI tools and workflows",
                include_keywords=("ai", "agent"),
                exclude_keywords=("stock",),
                source_tags=("ai",),
                strict_topic_guard=True,
            )
        }
    )
    item = _build_candidate(
        title="AI agent shares stock picks for retail traders",
        summary="A fast-moving experiment in public markets",
        source_tags=("ai",),
    )

    candidate = matcher.match_source_item(item)[0]

    assert candidate.eligible is False
    assert candidate.score == 0
    assert candidate.include_keyword_hits == ("ai", "agent")
    assert candidate.exclude_keyword_hits == ("stock",)
    assert candidate.source_tag_hits == ("ai",)
    assert candidate.blocked_by_exclude_keywords is True


def test_matcher_normalizes_configured_source_tags_before_matching() -> None:
    matcher = AccountMatcher(
        {
            "ai_tools_daily": _build_account(
                topic="AI tools and workflows",
                source_tags=("ai-tools", "openai_api"),
            )
        }
    )
    item = _build_candidate(
        title="Platform update",
        summary="Release notes for builders",
        source_tags=("AI Tools", "OpenAI API"),
    )

    candidate = matcher.match_source_item(item)[0]

    assert candidate.eligible is True
    assert candidate.source_tag_hits == ("ai tools", "openai api")


def test_matcher_ignores_audience_words_from_account_topic() -> None:
    matcher = AccountMatcher(
        {
            "japan_global_news": _build_account(
                topic="Japan news for global readers",
            )
        }
    )

    generic_item = _build_candidate(
        title="World Cup cash boost draws global broadcast interest",
        summary="Readers can expect more funding around the tournament.",
    )
    japan_item = _build_candidate(
        title="Japan wage policy update reaches employers",
        summary="Officials in Tokyo are watching sustained pay hikes.",
    )

    generic_candidate = matcher.match_source_item(generic_item)[0]
    japan_candidate = matcher.match_source_item(japan_item)[0]

    assert topic_keywords("Japan news for global readers") == ("japan",)
    assert generic_candidate.eligible is False
    assert generic_candidate.score == 0
    assert japan_candidate.eligible is True
    assert japan_candidate.topic_keyword_hits == ("japan",)


def test_country_news_matching_keeps_korea_domestic_source_tags_without_international_noise() -> None:
    registry = ConfigRegistry.from_directory(PROJECT_ROOT / "config/global_country_news")
    account = registry.get_account("korea_global_news")
    matcher = AccountMatcher({"korea_global_news": account})

    domestic_item = _build_candidate(
        title="Court upholds sentence in public-interest case",
        summary="The ruling is pending further review.",
        source_tags=("domestic",),
    )
    international_item = _build_candidate(
        title="UAE to withdraw from OPEC May 1",
        summary="Energy ministers are watching the move.",
        source_tags=("international",),
    )

    domestic_candidate = matcher.match_source_item(domestic_item)[0]
    international_candidate = matcher.match_source_item(international_item)[0]

    assert domestic_candidate.eligible is True
    assert domestic_candidate.source_tag_hits == ("domestic",)
    assert international_candidate.eligible is False
    assert international_candidate.score == 0


def test_top_candidate_selector_returns_all_tied_eligible_candidates() -> None:
    candidates = (
        AccountMatchCandidate(account_key="ai_tools_daily", score=20, eligible=True),
        AccountMatchCandidate(account_key="finance_news_daily", score=20, eligible=True),
        AccountMatchCandidate(account_key="seo_tools_daily", score=12, eligible=True),
    )

    assert _top_account_keys(candidates) == (
        "ai_tools_daily",
        "finance_news_daily",
    )


def _sample_accounts() -> dict[str, AccountConfig]:
    return {
        "ai_tools_daily": _build_account(
            topic="AI tools and workflows",
            include_keywords=("ai", "agent", "automation"),
            exclude_keywords=("earnings", "stock"),
            source_tags=("ai", "automation"),
            strict_topic_guard=True,
        ),
        "finance_news_daily": _build_account(
            topic="Finance markets and investing",
            include_keywords=("earnings", "stock market", "investing"),
            exclude_keywords=("seo", "backlink"),
            source_tags=("finance", "markets"),
            strict_topic_guard=True,
        ),
        "seo_tools_daily": _build_account(
            topic="SEO tools and search optimization",
            include_keywords=("seo", "search ranking", "backlink"),
            exclude_keywords=("earnings", "stocks"),
            source_tags=("seo", "search"),
            strict_topic_guard=True,
        ),
    }


def _build_account(
    *,
    topic: str,
    include_keywords: tuple[str, ...] = (),
    exclude_keywords: tuple[str, ...] = (),
    source_tags: tuple[str, ...] = (),
    strict_topic_guard: bool = False,
) -> AccountConfig:
    return AccountConfig.model_validate(
        {
            "topic": topic,
            "source_sets": ["shared_primary"],
            "prompt_profile": "default_profile",
            "landing": {
                "fallback_url": "https://gilgop.cloud/example",
                "rules": [],
            },
            "matching": {
                "include_keywords": list(include_keywords),
                "exclude_keywords": list(exclude_keywords),
                "source_tags": list(source_tags),
                "strict_topic_guard": strict_topic_guard,
            },
            "channels": {
                "x": {
                    "schedule": {"cron": "0 9 * * *"},
                    "render": {"max_chars": 280},
                }
            },
        }
    )


def _build_candidate(
    *,
    title: str,
    summary: str,
    source_tags: tuple[str, ...] = (),
) -> SourceItemCandidate:
    slug = title.casefold().replace(" ", "-")
    raw_payload = {"tags": list(source_tags)} if source_tags else {}

    return SourceItemCandidate(
        source_id="shared_feed",
        external_id=slug,
        source_url=f"https://example.com/posts/{slug}",
        title=title,
        summary=summary,
        raw_payload=raw_payload,
    )


def _top_account_keys(
    candidates: tuple[AccountMatchCandidate, ...],
) -> tuple[str, ...]:
    return tuple(candidate.account_key for candidate in select_top_account_candidates(candidates))
