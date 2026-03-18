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
