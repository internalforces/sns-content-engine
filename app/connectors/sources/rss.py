"""RSS source connector."""

from __future__ import annotations

from collections.abc import Iterable
from xml.etree import ElementTree

from app.config.schemas import RssSourceConfig
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


class RssSourceConnector(SourceConnector):
    """Discover items from an RSS or Atom feed."""

    def __init__(self, *, fetch_bytes: BytesFetcher | None = None) -> None:
        self._fetch_bytes = fetch_bytes or fetch_url_bytes

    def discover(self, source_id: str, config: RssSourceConfig) -> SourceConnectorResult:
        try:
            xml_bytes = self._fetch(str(config.url))
            root = ElementTree.fromstring(xml_bytes)
        except SourceConnectorError as exc:
            return _failure_result(source_id, exc.stage, str(exc))
        except ElementTree.ParseError as exc:
            return _failure_result(source_id, SourceParseError.stage, f"invalid feed XML: {exc}")

        try:
            if _local_name(root.tag) == "rss":
                return self._discover_rss_items(source_id, root, config=config)
            if _local_name(root.tag) == "feed":
                return self._discover_atom_entries(source_id, root, config=config)
        except SourceParseError as exc:
            return _failure_result(source_id, exc.stage, str(exc))

        return _failure_result(
            source_id,
            SourceParseError.stage,
            f"unsupported feed root element '{_local_name(root.tag)}'",
        )

    def _fetch(self, url: str) -> bytes:
        try:
            return self._fetch_bytes(url)
        except SourceConnectorError:
            raise
        except OSError as exc:
            raise SourceFetchError(f"could not fetch {url}: {exc}") from exc

    def _discover_rss_items(
        self,
        source_id: str,
        root: ElementTree.Element,
        *,
        config: RssSourceConfig,
    ) -> SourceConnectorResult:
        channel = _find_child_named(root, "channel")
        if channel is None:
            raise SourceParseError("RSS feed is missing channel")

        items = []
        failures = []
        for index, item in enumerate(_children_named(channel, "item"), start=1):
            categories = _child_texts(item, "category")
            raw_item = RawSourceItem(
                source_id=source_id,
                external_id=_child_text(item, "guid") or _child_text(item, "link"),
                source_url=_child_text(item, "link"),
                title=_child_text(item, "title"),
                summary=_child_text(item, "description"),
                published_at=_child_text(item, "pubDate"),
                raw_payload={
                    "kind": "rss",
                    "guid": _child_text(item, "guid"),
                    "link": _child_text(item, "link"),
                    "categories": categories,
                },
            )
            _append_normalized_item(
                raw_item,
                item_key=f"item {index}",
                items=items,
                failures=failures,
                include_url_prefixes=config.include_url_prefixes,
            )

        return SourceConnectorResult(items=tuple(items), failures=tuple(failures))

    def _discover_atom_entries(
        self,
        source_id: str,
        root: ElementTree.Element,
        *,
        config: RssSourceConfig,
    ) -> SourceConnectorResult:
        items = []
        failures = []
        for index, entry in enumerate(_children_named(root, "entry"), start=1):
            link = _atom_entry_link(entry)
            categories = _atom_category_terms(entry)
            raw_item = RawSourceItem(
                source_id=source_id,
                external_id=_child_text(entry, "id") or link,
                source_url=link,
                title=_child_text(entry, "title"),
                summary=_child_text(entry, "summary") or _child_text(entry, "content"),
                published_at=_child_text(entry, "published") or _child_text(entry, "updated"),
                raw_payload={
                    "kind": "atom",
                    "id": _child_text(entry, "id"),
                    "link": link,
                    "categories": categories,
                },
            )
            _append_normalized_item(
                raw_item,
                item_key=f"entry {index}",
                items=items,
                failures=failures,
                include_url_prefixes=config.include_url_prefixes,
            )

        return SourceConnectorResult(items=tuple(items), failures=tuple(failures))


def _append_normalized_item(
    raw_item: RawSourceItem,
    *,
    item_key: str,
    items: list,
    failures: list[SourceDiscoveryFailure],
    include_url_prefixes,
) -> None:
    try:
        normalized_item = normalize_raw_source_item(raw_item)
        if not source_url_matches_prefixes(
            normalized_item.source_url,
            include_url_prefixes,
        ):
            return
        items.append(normalized_item)
    except SourceNormalizationError as exc:
        failures.append(
            SourceDiscoveryFailure(
                source_id=raw_item.source_id,
                stage="normalize",
                item_key=item_key,
                message=str(exc),
            )
        )


def _failure_result(source_id: str, stage: str, message: str) -> SourceConnectorResult:
    return SourceConnectorResult(
        failures=(SourceDiscoveryFailure(source_id=source_id, stage=stage, message=message),)
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _children_named(element: ElementTree.Element, name: str) -> Iterable[ElementTree.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _find_child_named(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    for child in element:
        if _local_name(child.tag) == name:
            return child
    return None


def _child_text(element: ElementTree.Element, name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) != name:
            continue
        if child.text is None:
            return None
        normalized = child.text.strip()
        return normalized or None
    return None


def _child_texts(element: ElementTree.Element, name: str) -> tuple[str, ...]:
    values: list[str] = []
    for child in element:
        if _local_name(child.tag) != name or child.text is None:
            continue
        normalized = child.text.strip()
        if normalized:
            values.append(normalized)
    return tuple(values)


def _atom_entry_link(entry: ElementTree.Element) -> str | None:
    alternate_href: str | None = None
    first_href: str | None = None
    for child in entry:
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip() or None
        if href is None:
            continue
        first_href = first_href or href
        if child.attrib.get("rel", "alternate") == "alternate":
            alternate_href = href
            break
    return alternate_href or first_href


def _atom_category_terms(entry: ElementTree.Element) -> tuple[str, ...]:
    values: list[str] = []
    for child in entry:
        if _local_name(child.tag) != "category":
            continue
        term = child.attrib.get("term", "").strip()
        if term:
            values.append(term)
    return tuple(values)
