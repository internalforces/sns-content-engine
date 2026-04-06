"""Registry for resolving source connectors by config type."""

from __future__ import annotations

from app.config.schemas import (
    GdeltSourceConfig,
    ManualCsvSourceConfig,
    RssSourceConfig,
    SitemapSourceConfig,
    SourceConfig,
)
from app.connectors.sources.gdelt import GdeltSourceConnector
from app.connectors.sources.manual_csv import ManualCsvSourceConnector
from app.connectors.sources.rss import RssSourceConnector
from app.connectors.sources.sitemap import SitemapSourceConnector


class SourceConnectorRegistry:
    """Resolve concrete source connectors from validated source config types."""

    def __init__(
        self,
        *,
        rss_connector: RssSourceConnector | None = None,
        sitemap_connector: SitemapSourceConnector | None = None,
        manual_csv_connector: ManualCsvSourceConnector | None = None,
        gdelt_connector: GdeltSourceConnector | None = None,
    ) -> None:
        self._rss_connector = rss_connector or RssSourceConnector()
        self._sitemap_connector = sitemap_connector or SitemapSourceConnector()
        self._manual_csv_connector = manual_csv_connector or ManualCsvSourceConnector()
        self._gdelt_connector = gdelt_connector or GdeltSourceConnector()

    def get_connector(self, source_config: SourceConfig):
        """Return the connector for the given source config."""

        if isinstance(source_config, RssSourceConfig):
            return self._rss_connector
        if isinstance(source_config, SitemapSourceConfig):
            return self._sitemap_connector
        if isinstance(source_config, ManualCsvSourceConfig):
            return self._manual_csv_connector
        if isinstance(source_config, GdeltSourceConfig):
            return self._gdelt_connector
        raise TypeError(f"unsupported source config type: {type(source_config)!r}")
