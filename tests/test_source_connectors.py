"""Tests for source connector discovery and normalization."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import app.connectors.sources.base as source_base_module
from app.config import GdeltSourceConfig, ManualCsvSourceConfig, RssSourceConfig, SitemapSourceConfig
from app.connectors.sources import (
    GdeltSourceConnector,
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
    assert candidate.canonical_url == "https://example.com/blog/very-useful-tool"
    assert candidate.normalized_title == "very useful tool"


def test_normalizer_canonicalizes_urls_and_builds_dedupe_metadata() -> None:
    candidate = normalize_raw_source_item(
        RawSourceItem(
            source_id="ai_tools_rss",
            external_id="entry-1",
            source_url="HTTPS://user:secret@Example.com/posts/1/?utm_source=x&b=2&a=1#section",
            title="AI   Tool: Launch!",
            summary="Fast, simple workflow tips.",
        )
    )

    assert candidate.source_url == "https://example.com/posts/1?a=1&b=2"
    assert candidate.canonical_url == "https://example.com/posts/1?a=1&b=2"
    assert candidate.normalized_title == "ai tool launch"
    assert len(candidate.normalized_title_hash) == 64
    assert len(candidate.dedupe_fingerprint) == 64


def test_normalizer_extracts_source_tags_from_raw_payload() -> None:
    candidate = normalize_raw_source_item(
        RawSourceItem(
            source_id="ai_tools_manual",
            external_id="manual-1",
            source_url="https://example.com/posts/ai-agents",
            title="AI Agents",
            raw_payload={
                "tags": ["AI", "Automation"],
                "category": "Agents",
                "source_tags": "workflows, AI",
            },
        )
    )

    assert candidate.source_tags == ("ai", "automation", "agents", "workflows")


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


def test_rss_connector_extracts_category_tags_for_matching() -> None:
    feed_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>AI Tools</title>
    <item>
      <guid>tagged-1</guid>
      <link>https://example.com/posts/tagged</link>
      <title>Tagged Entry</title>
      <category>AI</category>
      <category>Automation</category>
    </item>
  </channel>
</rss>
"""
    connector = RssSourceConnector(fetch_bytes=lambda _: feed_xml)
    config = RssSourceConfig(type="rss", url="https://example.com/feed.xml")

    result = connector.discover("ai_tools_rss", config)

    assert result.failures == ()
    assert len(result.items) == 1
    assert result.items[0].source_tags == ("ai", "automation")


def test_fetch_url_bytes_sends_default_user_agent(monkeypatch) -> None:
    captured = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return b"<rss/>"

    def fake_urlopen(request, *, timeout):
        captured["user_agent"] = request.headers["User-agent"]
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(source_base_module, "urlopen", fake_urlopen)

    assert source_base_module.fetch_url_bytes("https://example.com/feed.xml") == b"<rss/>"
    assert captured["user_agent"].startswith("sns-content-engine/source-discovery")
    assert captured["timeout"] == 10.0


def test_rss_connector_filters_items_by_include_url_prefixes() -> None:
    feed_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Mixed Feed</title>
    <item>
      <guid>guide-1</guid>
      <link>https://example.com/guides/ai-workflows</link>
      <title>AI Workflows</title>
    </item>
    <item>
      <guid>seo-1</guid>
      <link>https://example.com/seo/title-generator</link>
      <title>SEO Title Generator</title>
    </item>
  </channel>
</rss>
"""
    connector = RssSourceConnector(fetch_bytes=lambda _: feed_xml)
    config = RssSourceConfig(
        type="rss",
        url="https://example.com/feed.xml",
        include_url_prefixes=("https://example.com/guides",),
    )

    result = connector.discover("ai_tools_rss", config)

    assert result.failures == ()
    assert len(result.items) == 1
    assert result.items[0].source_url == "https://example.com/guides/ai-workflows"


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


def test_sitemap_connector_filters_items_by_include_url_prefixes() -> None:
    sitemap_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/guides/ai-workflows</loc>
    <lastmod>2026-03-15</lastmod>
  </url>
  <url>
    <loc>https://example.com/seo/title-generator</loc>
    <lastmod>2026-03-16</lastmod>
  </url>
</urlset>
"""
    connector = SitemapSourceConnector(fetch_bytes=lambda _: sitemap_xml)
    config = SitemapSourceConfig(
        type="sitemap",
        url="https://example.com/sitemap.xml",
        include_url_prefixes=("https://example.com/seo",),
    )

    result = connector.discover("seo_tools_sitemap", config)

    assert result.failures == ()
    assert len(result.items) == 1
    assert result.items[0].source_url == "https://example.com/seo/title-generator"


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


def test_gdelt_connector_discovers_normalized_items_from_json() -> None:
    payload = json.dumps(
        {
            "articles": [
                {
                    "url": "https://example.com/news/launch?utm_source=gdelt",
                    "title": "Launch Update",
                    "seendate": "20260406T010203Z",
                    "domain": "example.com",
                    "language": "English",
                    "sourcecountry": "US",
                    "excerpt": "A short launch summary.",
                },
                {
                    "url": "https://example.com/news/second",
                    "title": "Second Signal",
                    "seendate": "20260406T020304Z",
                },
            ]
        }
    ).encode("utf-8")
    requested_urls: list[str] = []

    connector = GdeltSourceConnector(
        fetch_bytes=lambda url: requested_urls.append(url) or payload,
    )
    config = GdeltSourceConfig(type="gdelt", query="domain:news")

    result = connector.discover("gdelt_latest", config)

    assert requested_urls == [
        "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Anews&mode=ArtList&format=json&maxrecords=50&sort=DateDesc&timespan=1day"
    ]
    assert result.failures == ()
    assert len(result.items) == 2
    assert result.items[0].source_id == "gdelt_latest"
    assert result.items[0].source_url == "https://example.com/news/launch"
    assert result.items[0].summary == "A short launch summary."
    assert result.items[0].published_at == datetime(2026, 4, 6, 1, 2, 3, tzinfo=timezone.utc)
    assert result.items[0].raw_payload["kind"] == "gdelt"
    assert result.items[0].raw_payload["query"] == "domain:news"
    assert result.items[1].title == "Second Signal"


def test_gdelt_connector_reports_invalid_json_as_parse_failure() -> None:
    connector = GdeltSourceConnector(fetch_bytes=lambda _: b"{not-json")
    config = GdeltSourceConfig(type="gdelt", query="domain:news")

    result = connector.discover("gdelt_latest", config)

    assert result.items == ()
    assert len(result.failures) == 1
    assert result.failures[0].source_id == "gdelt_latest"
    assert result.failures[0].stage == "parse"
    assert "invalid GDELT JSON" in result.failures[0].message


def test_gdelt_connector_allows_empty_article_lists() -> None:
    connector = GdeltSourceConnector(fetch_bytes=lambda _: b'{"articles": []}')
    config = GdeltSourceConfig(type="gdelt", query="domain:news")

    result = connector.discover("gdelt_latest", config)

    assert result.items == ()
    assert result.failures == ()


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
