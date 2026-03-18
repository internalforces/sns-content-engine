"""Tests for deterministic finance summary regeneration."""

from __future__ import annotations

import pytest

from app.services import SummaryRegenerationError, SummaryRegenerator


def test_summary_regenerator_builds_summary_and_key_points_from_article_text() -> None:
    article_text = (
        "Stocks moved higher after the central bank kept rates steady and repeated a cautious tone. "
        "Bond yields eased as investors focused on inflation progress and lending conditions. "
        "Analysts said bank commentary and revenue guidance would shape the next trading sessions. "
        "Portfolio managers also watched Treasury moves and credit spreads for broader risk signals."
    )

    result = SummaryRegenerator().regenerate(
        title="Central bank update lifts markets",
        article_text=article_text,
        rss_description="RSS text should not be the primary summary.",
    )

    assert result.method == "deterministic_finance"
    assert result.summary.startswith("Central bank update lifts markets:")
    assert len(result.key_points) >= 3
    assert "rates steady" in result.key_points[0].casefold() or "markets" in result.key_points[0].casefold()


def test_summary_regenerator_uses_rss_description_only_as_last_resort_point() -> None:
    article_text = (
        "Inflation data surprised economists and pushed bond markets to reprice the near-term path. "
        "Currency traders adjusted expectations after the policy statement and press conference."
    )

    result = SummaryRegenerator(minimum_word_count=15, max_key_points=3).regenerate(
        title="Inflation print resets policy outlook",
        article_text=article_text,
        rss_description="Fallback context from RSS description.",
    )

    assert len(result.key_points) == 3
    assert result.key_points[-1] == "Fallback context from RSS description"


def test_summary_regenerator_rejects_short_content() -> None:
    with pytest.raises(SummaryRegenerationError) as exc_info:
        SummaryRegenerator().regenerate(
            title="Tiny update",
            article_text="Too short for safe regeneration.",
        )

    assert exc_info.value.code == "content_too_short"
    assert exc_info.value.message == "기사 내용이 너무 짧아 요약하지 않았어요"


def test_summary_regenerator_removes_investment_advice_phrasing() -> None:
    article_text = (
        "Analysts did not issue a strong buy call, but markets reacted to improving demand and revenue visibility. "
        "Management said margins could stabilize if logistics costs continue to ease. "
        "Investors watched bank funding markets and policy signals for confirmation."
    )

    result = SummaryRegenerator(minimum_word_count=15).regenerate(
        title="Demand recovery steadies outlook",
        article_text=article_text,
    )

    assert "strong buy" not in result.summary.casefold()
    assert all("strong buy" not in point.casefold() for point in result.key_points)
