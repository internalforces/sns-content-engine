"""Normalization helpers for connector output."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from app.domain import canonicalize_url
from app.domain.source_ingestion import RawSourceItem, SourceItemCandidate, SourceNormalizationError


def normalize_raw_source_item(raw_item: RawSourceItem) -> SourceItemCandidate:
    """Normalize raw connector output into the shared source item shape."""

    source_id = _normalize_non_empty(raw_item.source_id, label="source_id")
    source_url = _normalize_source_url(raw_item.source_url)
    external_id = _normalize_optional_text(raw_item.external_id) or source_url
    title = _normalize_optional_text(raw_item.title) or _derive_title_from_url(source_url)
    summary = _normalize_optional_text(raw_item.summary)
    published_at = _normalize_published_at(raw_item.published_at)
    raw_payload = dict(raw_item.raw_payload)

    return SourceItemCandidate(
        source_id=source_id,
        external_id=external_id,
        source_url=source_url,
        title=title,
        summary=summary,
        published_at=published_at,
        raw_payload=raw_payload,
    )


def source_url_matches_prefixes(
    source_url: str,
    include_url_prefixes,
) -> bool:
    """Return whether a normalized source URL should be kept for this source config."""

    if not include_url_prefixes:
        return True

    normalized_source_url = canonicalize_url(source_url)
    for prefix in include_url_prefixes:
        normalized_prefix = canonicalize_url(str(prefix))
        if (
            normalized_source_url == normalized_prefix
            or normalized_source_url.startswith(f"{normalized_prefix}/")
            or normalized_source_url.startswith(f"{normalized_prefix}?")
        ):
            return True
    return False


def _normalize_source_url(value: str | None) -> str:
    normalized = _normalize_non_empty(value, label="source_url")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SourceNormalizationError("source_url must be an absolute HTTP(S) URL")
    return canonicalize_url(normalized)


def _normalize_published_at(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return _coerce_utc(value)

    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None

    parsed = _parse_iso_datetime(normalized)
    if parsed is None:
        parsed = _parse_rfc2822_datetime(normalized)
    if parsed is None:
        raise SourceNormalizationError(
            "published_at must be an ISO 8601 or RFC 2822 datetime string"
        )
    return _coerce_utc(parsed)


def _parse_iso_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_rfc2822_datetime(value: str) -> datetime | None:
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _derive_title_from_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    path = parsed.path.rstrip("/")
    slug = path.rsplit("/", maxsplit=1)[-1] if path else ""
    normalized_slug = slug.replace("-", " ").replace("_", " ").strip()
    if normalized_slug:
        return normalized_slug.title()
    return source_url


def _normalize_non_empty(value: str | None, *, label: str) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise SourceNormalizationError(f"{label} must not be empty")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized
