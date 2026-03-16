"""Shared models for source ingestion and normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


class SourceNormalizationError(ValueError):
    """Raised when a raw source item cannot be normalized safely."""


@dataclass(frozen=True, slots=True)
class RawSourceItem:
    """Connector-specific source item data before normalization."""

    source_id: str
    external_id: str | None
    source_url: str | None
    title: str | None = None
    summary: str | None = None
    published_at: datetime | str | None = None
    raw_payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceItemCandidate:
    """Normalized source item candidate for downstream ingestion stages."""

    source_id: str
    external_id: str
    source_url: str
    title: str
    summary: str | None = None
    published_at: datetime | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceDiscoveryFailure:
    """Captured source discovery failure with stable metadata."""

    source_id: str
    stage: str
    message: str
    item_key: str | None = None

    def format_for_cli(self) -> str:
        """Render a compact message for CLI output."""

        prefix = f"{self.source_id} [{self.stage}]"
        if self.item_key:
            return f"{prefix} {self.item_key}: {self.message}"
        return f"{prefix} {self.message}"


@dataclass(frozen=True, slots=True)
class SourceConnectorResult:
    """Connector discovery result with normalized items and captured failures."""

    items: tuple[SourceItemCandidate, ...] = ()
    failures: tuple[SourceDiscoveryFailure, ...] = ()
