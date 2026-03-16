"""Source connectors for ingestion workflows."""

from app.connectors.sources.base import (
    SourceConnector,
    SourceConnectorError,
    SourceFetchError,
    SourceParseError,
    SourceReadError,
    fetch_url_text,
)
from app.connectors.sources.manual_csv import ManualCsvSourceConnector
from app.connectors.sources.normalizer import normalize_raw_source_item
from app.connectors.sources.registry import SourceConnectorRegistry
from app.connectors.sources.rss import RssSourceConnector
from app.connectors.sources.sitemap import SitemapSourceConnector

__all__ = [
    "ManualCsvSourceConnector",
    "RssSourceConnector",
    "SitemapSourceConnector",
    "SourceConnector",
    "SourceConnectorError",
    "SourceConnectorRegistry",
    "SourceFetchError",
    "SourceParseError",
    "SourceReadError",
    "fetch_url_text",
    "normalize_raw_source_item",
]
