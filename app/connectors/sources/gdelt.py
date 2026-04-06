"""GDELT document API source connector."""

from __future__ import annotations

import json
from json import JSONDecodeError
from urllib.parse import urlencode

from app.config.schemas import GdeltSourceConfig
from app.connectors.sources.base import (
    BytesFetcher,
    SourceConnector,
    SourceConnectorError,
    SourceFetchError,
    SourceParseError,
    fetch_url_bytes,
)
from app.connectors.sources.normalizer import normalize_raw_source_item
from app.domain.source_ingestion import (
    RawSourceItem,
    SourceConnectorResult,
    SourceDiscoveryFailure,
    SourceNormalizationError,
)

_GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltSourceConnector(SourceConnector):
    """Discover recent articles from the GDELT DOC API."""

    def __init__(
        self,
        *,
        fetch_bytes: BytesFetcher | None = None,
        api_url: str = _GDELT_DOC_API_URL,
    ) -> None:
        self._fetch_bytes = fetch_bytes or fetch_url_bytes
        self._api_url = api_url

    def discover(self, source_id: str, config: GdeltSourceConfig) -> SourceConnectorResult:
        request_url = _build_request_url(self._api_url, config.query)

        try:
            payload = self._fetch(request_url)
            data = json.loads(payload)
        except SourceConnectorError as exc:
            return _failure_result(source_id, exc.stage, str(exc))
        except (JSONDecodeError, UnicodeDecodeError) as exc:
            return _failure_result(source_id, SourceParseError.stage, f"invalid GDELT JSON: {exc}")

        if not isinstance(data, dict):
            return _failure_result(
                source_id,
                SourceParseError.stage,
                "GDELT response must be a JSON object",
            )

        articles = data.get("articles")
        if articles is None:
            return _failure_result(
                source_id,
                SourceParseError.stage,
                "GDELT response must include an 'articles' list",
            )
        if not isinstance(articles, list):
            return _failure_result(
                source_id,
                SourceParseError.stage,
                "GDELT response field 'articles' must be a list",
            )

        items = []
        failures = []

        for index, article in enumerate(articles, start=1):
            if not isinstance(article, dict):
                failures.append(
                    SourceDiscoveryFailure(
                        source_id=source_id,
                        stage="parse",
                        item_key=f"article {index}",
                        message="article payload must be a JSON object",
                    )
                )
                continue

            raw_item = RawSourceItem(
                source_id=source_id,
                external_id=_article_text(article, "url"),
                source_url=_article_text(article, "url"),
                title=_article_text(article, "title"),
                summary=(
                    _article_text(article, "excerpt")
                    or _article_text(article, "summary")
                    or _article_text(article, "description")
                ),
                published_at=_article_text(article, "seendate") or _article_text(article, "date"),
                raw_payload={
                    "kind": "gdelt",
                    "query": config.query,
                    **article,
                },
            )

            try:
                items.append(normalize_raw_source_item(raw_item))
            except SourceNormalizationError as exc:
                failures.append(
                    SourceDiscoveryFailure(
                        source_id=source_id,
                        stage="normalize",
                        item_key=f"article {index}",
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


def _build_request_url(api_url: str, query: str) -> str:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": "50",
        "sort": "DateDesc",
        "timespan": "1day",
    }
    return f"{api_url}?{urlencode(params)}"


def _article_text(article: dict[str, object], key: str) -> str | None:
    value = article.get(key)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _failure_result(source_id: str, stage: str, message: str) -> SourceConnectorResult:
    return SourceConnectorResult(
        failures=(SourceDiscoveryFailure(source_id=source_id, stage=stage, message=message),)
    )
