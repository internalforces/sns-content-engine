"""Tests for the lightweight HTML article extractor."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services import ArticleExtractError, ArticleExtractor


def test_article_extractor_prefers_article_body_and_meta_fields() -> None:
    html = """
    <html>
      <head>
        <title>Fed update moves markets</title>
        <meta property="og:site_name" content="Finance Example" />
        <meta property="article:published_time" content="2026-03-18T09:00:00Z" />
      </head>
      <body>
        <article>
          <p>Stocks moved higher after the central bank signaled a cautious path.</p>
          <p>Bond yields eased while traders focused on inflation and credit conditions.</p>
          <p>Analysts said liquidity and policy timing still matter for the next quarter.</p>
          <p>Markets also watched large bank commentary for clues on loan demand.</p>
        </article>
      </body>
    </html>
    """

    result = ArticleExtractor(minimum_word_count=15).extract(html)

    assert result.title == "Fed update moves markets"
    assert result.source_name == "Finance Example"
    assert result.published_at == datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc)
    assert "central bank signaled a cautious path" in result.article_text
    assert result.metadata["og:site_name"] == "Finance Example"


def test_article_extractor_falls_back_to_main_content() -> None:
    html = """
    <html>
      <body>
        <main>
          <p>Revenue growth slowed in the consumer segment after a strong holiday quarter.</p>
          <p>Management said margin pressure came from logistics, promotions, and inventory cleanup.</p>
          <p>Investors focused on guidance, capital spending, and regional demand trends.</p>
        </main>
      </body>
    </html>
    """

    result = ArticleExtractor().extract(html)

    assert "Revenue growth slowed" in result.article_text
    assert result.title is None
    assert result.source_name is None


def test_article_extractor_supports_source_specific_selectors_and_exclusions() -> None:
    html = """
    <html>
      <head>
        <title>Market structure update</title>
      </head>
      <body>
        <div class="layout-shell">
          <div class="article-body">
            <p>Market liquidity improved after dealers adjusted inventories across rates and credit desks.</p>
            <div class="inline-promo">
              <p>Subscribe now for premium alerts and shopping offers.</p>
            </div>
            <p>Traders said funding pressure eased while macro expectations stayed firmly in focus.</p>
            <p>Analysts still watched bank commentary, earnings quality, and regional demand trends.</p>
          </div>
          <div class="related-links">
            <p>Read more gift guides and weekend lifestyle picks.</p>
          </div>
        </div>
      </body>
    </html>
    """

    result = ArticleExtractor(
        minimum_word_count=20,
        preferred_selectors=(".article-body",),
        excluded_selectors=(".inline-promo",),
    ).extract(html)

    assert result.title == "Market structure update"
    assert "Market liquidity improved" in result.article_text
    assert "Subscribe now for premium alerts" not in result.article_text
    assert "weekend lifestyle picks" not in result.article_text


def test_article_extractor_reports_missing_body_text() -> None:
    html = "<html><body><div></div></body></html>"

    with pytest.raises(ArticleExtractError) as exc_info:
        ArticleExtractor().extract(html)

    assert exc_info.value.code == "extract_failed"
    assert exc_info.value.message == "기사 본문을 읽지 못했어요"


def test_article_extractor_reports_short_content() -> None:
    html = "<html><body><article><p>Too short for finance summary.</p></article></body></html>"

    with pytest.raises(ArticleExtractError) as exc_info:
        ArticleExtractor(minimum_word_count=8).extract(html)

    assert exc_info.value.code == "content_too_short"
    assert exc_info.value.message == "기사 내용이 너무 짧아 요약하지 않았어요"
