"""Tests for source connector discovery and normalization."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.config import ManualCsvSourceConfig, RssSourceConfig, SitemapSourceConfig
from app.connectors.sources import (
    ManualCsvSourceConnector,
    RssSourceConnector,
    SitemapSourceConnector,
    normalize_raw_source_item,
)
from app.domain import RawSourceItem

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "sources"


def test_normalizer_derives_missing_fields_from_url() -> None:
    candidate = normalize_raw_source_item(
        RawSourceItem(
            source_id="ai_tools_sitemap",
            external_id=None,
            source_url="https://example.com/blog/very-useful-tool",
            title=None,
        )
    )

    assert candidate.external_id == "https://example.com/blog/very-useful-tool"
    assert candidate.title == "Very Useful Tool"


def test_rss_connector_discovers_normalized_items_from_fixture() -> None:
    feed_xml = (FIXTURES_DIR / "sample_feed.xml").read_bytes()
    connector = RssSourceConnector(fetch_bytes=lambda _: feed_xml)
    config = RssSourceConfig(type="rss", url="https://example.com/feed.xml")

    result = connector.discover("ai_tools_rss", config)

    assert result.failures == ()
    assert len(result.items) == 2
    assert result.items[0].source_id == "ai_tools_rss"
    assert result.items[0].external_id == "entry-1"
    assert result.items[0].source_url == "https://example.com/posts/1"
    assert result.items[0].summary == "Short summary"
    assert result.items[0].published_at == datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc)
    assert result.items[1].external_id == "https://example.com/posts/2"


def test_sitemap_connector_discovers_normalized_items_from_fixture() -> None:
    sitemap_xml = (FIXTURES_DIR / "sample_sitemap.xml").read_bytes()
    connector = SitemapSourceConnector(fetch_bytes=lambda _: sitemap_xml)
    config = SitemapSourceConfig(type="sitemap", url="https://example.com/sitemap.xml")

    result = connector.discover("ai_tools_sitemap", config)

    assert result.failures == ()
    assert len(result.items) == 2
    assert result.items[0].title == "First Post"
    assert result.items[0].published_at == datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    assert result.items[1].title == "Second Post"


def test_manual_csv_connector_discovers_items_from_fixture_file() -> None:
    connector = ManualCsvSourceConnector()
    config = ManualCsvSourceConfig(type="manual_csv", path=FIXTURES_DIR / "sample_manual.csv")

    result = connector.discover("ai_tools_manual", config)

    assert result.failures == ()
    assert len(result.items) == 2
    assert result.items[0].external_id == "csv-1"
    assert result.items[0].published_at == datetime(2026, 3, 16, 9, 30, tzinfo=timezone.utc)
    assert result.items[1].external_id == "https://example.com/manual/second-entry"
    assert result.items[1].title == "Second Entry"


def test_rss_connector_captures_fetch_failures_safely() -> None:
    connector = RssSourceConnector(fetch_bytes=lambda _: (_ for _ in ()).throw(OSError("offline")))
    config = RssSourceConfig(type="rss", url="https://example.com/feed.xml")

    result = connector.discover("ai_tools_rss", config)

    assert result.items == ()
    assert len(result.failures) == 1
    assert result.failures[0].source_id == "ai_tools_rss"
    assert result.failures[0].stage == "fetch"
    assert "offline" in result.failures[0].message


def test_rss_connector_handles_namespaced_rss_feeds() -> None:
    namespaced_feed = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns="https://example.com/rss">
  <channel>
    <title>Namespaced Feed</title>
    <item>
      <guid>ns-1</guid>
      <link>https://example.com/posts/namespaced</link>
      <title>Namespaced Entry</title>
    </item>
  </channel>
</rss>
"""
    connector = RssSourceConnector(fetch_bytes=lambda _: namespaced_feed)
    config = RssSourceConfig(type="rss", url="https://example.com/namespaced-feed.xml")

    result = connector.discover("ai_tools_rss", config)

    assert result.failures == ()
    assert len(result.items) == 1
    assert result.items[0].external_id == "ns-1"
    assert result.items[0].title == "Namespaced Entry"


def test_rss_connector_respects_xml_declared_encodings() -> None:
    iso_feed = """<?xml version="1.0" encoding="ISO-8859-1"?>
<rss version="2.0">
  <channel>
    <title>AI Tools</title>
    <item>
      <guid>latin-1</guid>
      <link>https://example.com/posts/cafe</link>
      <title>Caf\xe9 Tool</title>
    </item>
  </channel>
</rss>
""".encode("iso-8859-1")
    connector = RssSourceConnector(fetch_bytes=lambda _: iso_feed)
    config = RssSourceConfig(type="rss", url="https://example.com/latin-feed.xml")

    result = connector.discover("ai_tools_rss", config)

    assert result.failures == ()
    assert len(result.items) == 1
    assert result.items[0].title == "Caf\xe9 Tool"


def test_sitemap_connector_rejects_cross_origin_nested_sitemaps() -> None:
    root_url = "https://example.com/sitemap.xml"
    fetched_urls: list[str] = []
    root_index = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://evil.example.com/child.xml</loc>
  </sitemap>
</sitemapindex>
"""

    def fake_fetch(url: str) -> bytes:
        fetched_urls.append(url)
        return root_index

    connector = SitemapSourceConnector(fetch_bytes=fake_fetch)
    config = SitemapSourceConfig(type="sitemap", url=root_url)

    result = connector.discover("ai_tools_sitemap", config)

    assert fetched_urls == [root_url]
    assert result.items == ()
    assert len(result.failures) == 1
    assert result.failures[0].stage == "parse"
    assert "origin must match configured origin" in result.failures[0].message


def test_sitemap_connector_limits_nested_sitemap_depth() -> None:
    root_url = "https://example.com/sitemap.xml"
    fetched_urls: list[str] = []
    root_index = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/child.xml</loc>
  </sitemap>
</sitemapindex>
"""

    def fake_fetch(url: str) -> bytes:
        fetched_urls.append(url)
        if url == root_url:
            return root_index
        raise AssertionError(f"unexpected fetch: {url}")

    connector = SitemapSourceConnector(fetch_bytes=fake_fetch, max_sitemap_depth=0)
    config = SitemapSourceConfig(type="sitemap", url=root_url)

    result = connector.discover("ai_tools_sitemap", config)

    assert fetched_urls == [root_url]
    assert result.items == ()
    assert len(result.failures) == 1
    assert result.failures[0].stage == "parse"
    assert "depth exceeded limit 0" in result.failures[0].message
