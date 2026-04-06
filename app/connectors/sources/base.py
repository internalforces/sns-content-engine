"""Base interfaces and helpers for source connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from app.config.schemas import (
    GdeltSourceConfig,
    ManualCsvSourceConfig,
    RssSourceConfig,
    SitemapSourceConfig,
)
from app.domain.source_ingestion import SourceConnectorResult

SourceConfigT = TypeVar(
    "SourceConfigT",
    RssSourceConfig,
    SitemapSourceConfig,
    ManualCsvSourceConfig,
    GdeltSourceConfig,
)
BytesFetcher = Callable[[str], bytes]


class SourceConnectorError(RuntimeError):
    """Base exception for connector discovery failures."""

    stage = "discover"


class SourceFetchError(SourceConnectorError):
    """Raised when remote source content cannot be fetched."""

    stage = "fetch"


class SourceReadError(SourceConnectorError):
    """Raised when a local source file cannot be read."""

    stage = "read"


class SourceParseError(SourceConnectorError):
    """Raised when source content cannot be parsed."""

    stage = "parse"


class SourceConnector(ABC):
    """Abstract source connector contract."""

    @abstractmethod
    def discover(self, source_id: str, config: SourceConfigT) -> SourceConnectorResult:
        """Discover normalized source item candidates for one source."""


def fetch_url_bytes(url: str, *, timeout_seconds: float = 10.0) -> bytes:
    """Fetch remote bytes content with a conservative timeout."""

    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            return response.read()
    except HTTPError as exc:
        raise SourceFetchError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise SourceFetchError(f"could not fetch {url}: {reason}") from exc
    except OSError as exc:
        raise SourceFetchError(f"could not fetch {url}: {exc}") from exc
