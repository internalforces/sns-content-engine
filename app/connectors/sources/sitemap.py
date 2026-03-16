"""XML sitemap source connector."""

from __future__ import annotations

from xml.etree import ElementTree

from app.config.schemas import SitemapSourceConfig
from app.connectors.sources.base import (
    SourceConnector,
    SourceConnectorError,
    SourceFetchError,
    SourceParseError,
    TextFetcher,
    fetch_url_text,
)
from app.connectors.sources.normalizer import normalize_raw_source_item
from app.domain.source_ingestion import (
    RawSourceItem,
    SourceConnectorResult,
    SourceDiscoveryFailure,
    SourceNormalizationError,
)


class SitemapSourceConnector(SourceConnector):
    """Discover items from a sitemap urlset or sitemap index."""

    def __init__(self, *, fetch_text: TextFetcher | None = None) -> None:
        self._fetch_text = fetch_text or fetch_url_text

    def discover(self, source_id: str, config: SitemapSourceConfig) -> SourceConnectorResult:
        return self._discover_url(source_id, str(config.url), visited=set())

    def _discover_url(
        self, source_id: str, sitemap_url: str, *, visited: set[str]
    ) -> SourceConnectorResult:
        if sitemap_url in visited:
            return _failure_result(
                source_id,
                "parse",
                f"recursive sitemap reference detected for {sitemap_url}",
            )
        visited.add(sitemap_url)

        try:
            xml_text = self._fetch(sitemap_url)
            root = ElementTree.fromstring(xml_text)
        except SourceConnectorError as exc:
            return _failure_result(source_id, exc.stage, str(exc))
        except ElementTree.ParseError as exc:
            return _failure_result(source_id, SourceParseError.stage, f"invalid sitemap XML: {exc}")

        root_name = _local_name(root.tag)
        if root_name == "urlset":
            return self._discover_urlset(source_id, root, document_url=sitemap_url)
        if root_name == "sitemapindex":
            return self._discover_sitemap_index(
                source_id,
                root,
                visited=visited,
            )

        return _failure_result(
            source_id,
            SourceParseError.stage,
            f"unsupported sitemap root element '{root_name}'",
        )

    def _discover_sitemap_index(
        self,
        source_id: str,
        root: ElementTree.Element,
        *,
        visited: set[str],
    ) -> SourceConnectorResult:
        items = []
        failures = []

        for index, sitemap in enumerate(_children_named(root, "sitemap"), start=1):
            nested_url = _child_text(sitemap, "loc")
            if nested_url is None:
                failures.append(
                    SourceDiscoveryFailure(
                        source_id=source_id,
                        stage="parse",
                        item_key=f"sitemap {index}",
                        message="nested sitemap is missing loc",
                    )
                )
                continue

            nested_result = self._discover_url(source_id, nested_url, visited=visited)
            items.extend(nested_result.items)
            failures.extend(nested_result.failures)

        return SourceConnectorResult(items=tuple(items), failures=tuple(failures))

    def _discover_urlset(
        self,
        source_id: str,
        root: ElementTree.Element,
        *,
        document_url: str,
    ) -> SourceConnectorResult:
        items = []
        failures = []

        for index, url_element in enumerate(_children_named(root, "url"), start=1):
            loc = _child_text(url_element, "loc")
            raw_item = RawSourceItem(
                source_id=source_id,
                external_id=loc,
                source_url=loc,
                title=None,
                summary=None,
                published_at=_child_text(url_element, "lastmod"),
                raw_payload={
                    "kind": "sitemap",
                    "document_url": document_url,
                    "loc": loc,
                    "lastmod": _child_text(url_element, "lastmod"),
                },
            )
            try:
                items.append(normalize_raw_source_item(raw_item))
            except SourceNormalizationError as exc:
                failures.append(
                    SourceDiscoveryFailure(
                        source_id=source_id,
                        stage="normalize",
                        item_key=f"url {index}",
                        message=str(exc),
                    )
                )

        return SourceConnectorResult(items=tuple(items), failures=tuple(failures))

    def _fetch(self, url: str) -> str:
        try:
            return self._fetch_text(url)
        except SourceConnectorError:
            raise
        except OSError as exc:
            raise SourceFetchError(f"could not fetch {url}: {exc}") from exc


def _failure_result(source_id: str, stage: str, message: str) -> SourceConnectorResult:
    return SourceConnectorResult(
        failures=(SourceDiscoveryFailure(source_id=source_id, stage=stage, message=message),)
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _children_named(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _child_text(element: ElementTree.Element, name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) != name:
            continue
        if child.text is None:
            return None
        normalized = child.text.strip()
        return normalized or None
    return None
