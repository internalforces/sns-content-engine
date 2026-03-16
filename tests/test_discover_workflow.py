"""Tests for the source discovery workflow."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from app.connectors.sources import (
    ManualCsvSourceConnector,
    RssSourceConnector,
    SitemapSourceConnector,
    SourceConnectorRegistry,
)
from app.workflows import discover_sources

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

    feed_xml = (FIXTURES_DIR / "sample_feed.xml").read_text(encoding="utf-8")
    connector_registry = SourceConnectorRegistry(
        rss_connector=RssSourceConnector(fetch_text=lambda _: feed_xml),
        sitemap_connector=SitemapSourceConnector(
            fetch_text=lambda _: (_ for _ in ()).throw(OSError("sitemap timeout"))
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


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
