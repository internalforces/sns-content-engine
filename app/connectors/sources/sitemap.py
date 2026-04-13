"""XML sitemap source connector."""

from __future__ import annotations

from urllib.parse import urlsplit
from xml.etree import ElementTree

from app.config.schemas import SitemapSourceConfig
from app.connectors.sources.base import (
    BytesFetcher,
    SourceConnector,
    SourceConnectorError,
    SourceFetchError,
    SourceParseError,
    fetch_url_bytes,
)
from app.connectors.sources.normalizer import normalize_raw_source_item, source_url_matches_prefixes
from app.domain.source_ingestion import (
    RawSourceItem,
    SourceConnectorResult,
    SourceDiscoveryFailure,
    SourceNormalizationError,
)


class SitemapSourceConnector(SourceConnector):
    """Discover items from a sitemap urlset or sitemap index."""

    def __init__(
        self,
        *,
        fetch_bytes: BytesFetcher | None = None,
        max_sitemap_depth: int = 4,
    ) -> None:
        if max_sitemap_depth < 0:
            raise ValueError("max_sitemap_depth must be >= 0")
        self._fetch_bytes = fetch_bytes or fetch_url_bytes
        self._max_sitemap_depth = max_sitemap_depth

    def discover(self, source_id: str, config: SitemapSourceConfig) -> SourceConnectorResult:
        root_url = str(config.url)
        root_origin = _url_origin(root_url)
        if root_origin is None:
            return _failure_result(
                source_id,
                SourceParseError.stage,
                f"invalid sitemap origin: {root_url}",
            )

        return self._discover_url(
            source_id,
            root_url,
            config=config,
            root_origin=root_origin,
            visited=set(),
            depth=0,
        )

    def _discover_url(
        self,
        source_id: str,
        sitemap_url: str,
        *,
        config: SitemapSourceConfig,
        root_origin: tuple[str, str, int],
        visited: set[str],
        depth: int,
    ) -> SourceConnectorResult:
        if depth > self._max_sitemap_depth:
            return _failure_result(
                source_id,
                SourceParseError.stage,
                f"nested sitemap depth exceeded limit {self._max_sitemap_depth}: {sitemap_url}",
            )

        sitemap_origin = _url_origin(sitemap_url)
        if sitemap_origin is None:
            return _failure_result(
                source_id,
                SourceParseError.stage,
                f"nested sitemap must be an absolute HTTP(S) URL: {sitemap_url}",
            )
        if depth > 0 and sitemap_origin != root_origin:
            return _failure_result(
                source_id,
                SourceParseError.stage,
                f"nested sitemap origin must match configured origin: {sitemap_url}",
            )

        if sitemap_url in visited:
            return _failure_result(
                source_id,
                "parse",
                f"recursive sitemap reference detected for {sitemap_url}",
            )
        visited.add(sitemap_url)

        try:
            xml_bytes = self._fetch(sitemap_url)
            root = ElementTree.fromstring(xml_bytes)
        except SourceConnectorError as exc:
            return _failure_result(source_id, exc.stage, str(exc))
        except ElementTree.ParseError as exc:
            return _failure_result(source_id, SourceParseError.stage, f"invalid sitemap XML: {exc}")

        root_name = _local_name(root.tag)
        if root_name == "urlset":
            return self._discover_urlset(
                source_id,
                root,
                config=config,
                document_url=sitemap_url,
            )
        if root_name == "sitemapindex":
            return self._discover_sitemap_index(
                source_id,
                root,
                config=config,
                root_origin=root_origin,
                visited=visited,
                depth=depth,
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
        config: SitemapSourceConfig,
        root_origin: tuple[str, str, int],
        visited: set[str],
        depth: int,
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

            nested_result = self._discover_url(
                source_id,
                nested_url,
                config=config,
                root_origin=root_origin,
                visited=visited,
                depth=depth + 1,
            )
            items.extend(nested_result.items)
            failures.extend(nested_result.failures)

        return SourceConnectorResult(items=tuple(items), failures=tuple(failures))

    def _discover_urlset(
        self,
        source_id: str,
        root: ElementTree.Element,
        *,
        config: SitemapSourceConfig,
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
                normalized_item = normalize_raw_source_item(raw_item)
                if not source_url_matches_prefixes(
                    normalized_item.source_url,
                    config.include_url_prefixes,
                ):
                    continue
                items.append(normalized_item)
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

    def _fetch(self, url: str) -> bytes:
        try:
            return self._fetch_bytes(url)
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


def _url_origin(url: str) -> tuple[str, str, int] | None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        return None

    if parsed.port is not None:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        port = 80

    return parsed.scheme.lower(), parsed.hostname.lower(), port


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
