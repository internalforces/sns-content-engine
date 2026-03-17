"""Shared models for source ingestion and normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Mapping

from app.domain.source_deduplication import (
    build_dedupe_fingerprint,
    build_normalized_title_hash,
    canonicalize_url,
    normalize_title_text,
)


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
    canonical_url: str = field(init=False)
    normalized_title: str = field(init=False)
    normalized_title_hash: str = field(init=False)
    dedupe_fingerprint: str = field(init=False)
    source_tags: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Derive deterministic duplicate-check fields from the candidate payload."""

        try:
            canonical_url = canonicalize_url(self.source_url)
            normalized_title = normalize_title_text(self.title)
        except ValueError as exc:
            raise SourceNormalizationError(str(exc)) from exc

        object.__setattr__(self, "canonical_url", canonical_url)
        object.__setattr__(self, "normalized_title", normalized_title)
        object.__setattr__(
            self,
            "normalized_title_hash",
            build_normalized_title_hash(self.title),
        )
        object.__setattr__(
            self,
            "dedupe_fingerprint",
            build_dedupe_fingerprint(title=self.title, summary=self.summary),
        )
        object.__setattr__(
            self,
            "source_tags",
            _extract_source_tags(self.raw_payload),
        )


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


_SOURCE_TAG_KEYS = (
    "tag",
    "tags",
    "category",
    "categories",
    "source_tag",
    "source_tags",
)
_TAG_SPLIT_RE = re.compile(r"[,;|]")


def _extract_source_tags(raw_payload: Mapping[str, Any]) -> tuple[str, ...]:
    collected_tags: list[str] = []
    seen: set[str] = set()

    for key in _SOURCE_TAG_KEYS:
        if key not in raw_payload:
            continue

        for tag in _coerce_source_tags(raw_payload[key]):
            if tag in seen:
                continue
            seen.add(tag)
            collected_tags.append(tag)

    return tuple(collected_tags)


def _coerce_source_tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        return _normalize_tag_sequence(_TAG_SPLIT_RE.split(value))

    if isinstance(value, Mapping):
        return ()

    if isinstance(value, (list, tuple, set, frozenset)):
        tags: list[str] = []
        for item in value:
            tags.extend(_coerce_source_tags(item))
        return tuple(tags)

    return ()


def _normalize_tag_sequence(values: list[str]) -> tuple[str, ...]:
    normalized_tags: list[str] = []

    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        normalized_tags.append(normalize_title_text(normalized))

    return tuple(normalized_tags)
