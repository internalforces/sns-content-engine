"""Tests for the source discovery workflow."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from app.connectors.sources import (
    GdeltSourceConnector,
    ManualCsvSourceConnector,
    RssSourceConnector,
    SitemapSourceConnector,
    SourceFetchError,
    SourceConnectorRegistry,
)
from app.workflows.discover_sources import discover_sources

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "sources"


def test_discover_sources_aggregates_items_and_failures_from_all_sources(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "accounts.yaml",
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
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        tmp_path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: "system"
            user_template: "user"
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        f"""
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml
          ai_tools_sitemap:
            type: sitemap
            url: https://example.com/sitemap.xml
          ai_tools_manual:
            type: manual_csv
            path: {FIXTURES_DIR / "sample_manual.csv"}

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
              - ai_tools_sitemap
              - ai_tools_manual
        """,
    )

    feed_xml = (FIXTURES_DIR / "sample_feed.xml").read_bytes()
    connector_registry = SourceConnectorRegistry(
        rss_connector=RssSourceConnector(fetch_bytes=lambda _: feed_xml),
        sitemap_connector=SitemapSourceConnector(
            fetch_bytes=lambda _: (_ for _ in ()).throw(OSError("sitemap timeout"))
        ),
        manual_csv_connector=ManualCsvSourceConnector(),
    )

    result = discover_sources(tmp_path, connector_registry=connector_registry)

    assert result.processed_sources == (
        "ai_tools_manual",
        "ai_tools_rss",
        "ai_tools_sitemap",
    )
    assert result.item_count == 4
    assert result.failure_count == 1
    assert result.counts_by_source() == {
        "ai_tools_manual": 2,
        "ai_tools_rss": 2,
    }
    assert result.failures[0].source_id == "ai_tools_sitemap"
    assert result.failures[0].stage == "fetch"
    assert "sitemap timeout" in result.failures[0].message


def test_discover_sources_captures_declared_connector_errors(tmp_path: Path) -> None:
    _write_minimal_config(tmp_path)

    class FailingConnector:
        def discover(self, source_id: str, source_config) -> None:
            raise SourceFetchError(f"{source_id} offline")

    class FakeRegistry:
        def get_connector(self, source_config):
            return FailingConnector()

    result = discover_sources(tmp_path, connector_registry=FakeRegistry())

    assert result.item_count == 0
    assert result.failure_count == 1
    assert result.failures[0].source_id == "ai_tools_rss"
    assert result.failures[0].stage == "fetch"
    assert result.failures[0].message == "ai_tools_rss offline"


def test_discover_sources_runs_gdelt_connector_from_registry(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_discovery
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        tmp_path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: "system"
            user_template: "user"
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_gdelt:
            type: gdelt
            query: "domain:news"

        source_sets:
          ai_tools_discovery:
            sources:
              - ai_tools_gdelt
        """,
    )

    connector_registry = SourceConnectorRegistry(
        gdelt_connector=GdeltSourceConnector(
            fetch_bytes=lambda _: b"""
            {"articles": [{"url": "https://example.com/news/launch", "title": "Launch", "seendate": "20260406T010203Z"}]}
            """
        ),
    )

    result = discover_sources(tmp_path, connector_registry=connector_registry)

    assert result.processed_sources == ("ai_tools_gdelt",)
    assert result.item_count == 1
    assert result.failure_count == 0
    assert result.counts_by_source() == {"ai_tools_gdelt": 1}
    assert result.items[0].title == "Launch"


def test_discover_sources_propagates_unexpected_connector_errors(tmp_path: Path) -> None:
    _write_minimal_config(tmp_path)

    class BuggyConnector:
        def discover(self, source_id: str, source_config) -> None:
            raise RuntimeError("boom")

    class FakeRegistry:
        def get_connector(self, source_config):
            return BuggyConnector()

    with pytest.raises(RuntimeError, match="boom"):
        discover_sources(tmp_path, connector_registry=FakeRegistry())


def _write_minimal_config(path: Path) -> None:
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
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: "system"
            user_template: "user"
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
