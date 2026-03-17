"""Domain helpers for source normalization and duplicate detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_QUERY_PARAM_NAMES = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
}
_TRACKING_QUERY_PARAM_PREFIXES = ("utm_",)
_MULTISPACE_RE = re.compile(r"\s+")
_DUPLICATE_SLASH_RE = re.compile(r"/{2,}")
_TITLE_TOKEN_RE = re.compile(r"[^\w\s]")


class DuplicateReason(str, Enum):
    """Stable duplicate reason codes surfaced by the ingestion workflow."""

    SOURCE_IDENTITY = "source_identity"
    CANONICAL_URL = "canonical_url"
    NORMALIZED_TITLE_HASH = "normalized_title_hash"
    RECENT_FINGERPRINT = "recent_fingerprint"


@dataclass(frozen=True, slots=True)
class DuplicateCheckResult:
    """Result of checking whether a candidate matches a stored duplicate."""

    is_duplicate: bool
    reason: DuplicateReason | None = None
    matched_item_id: int | None = None

    @classmethod
    def unique(cls) -> "DuplicateCheckResult":
        """Return a result representing a non-duplicate candidate."""

        return cls(is_duplicate=False)

    @classmethod
    def duplicate(
        cls,
        reason: DuplicateReason,
        *,
        matched_item_id: int | None,
    ) -> "DuplicateCheckResult":
        """Return a result representing a duplicate candidate."""

        return cls(
            is_duplicate=True,
            reason=reason,
            matched_item_id=matched_item_id,
        )


def canonicalize_url(url: str) -> str:
    """Return a deterministic canonical URL for duplicate comparisons."""

    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("source_url must be an absolute HTTP(S) URL")

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo = f"{userinfo}:{parsed.password}"
        userinfo = f"{userinfo}@"

    default_port = 443 if scheme == "https" else 80
    port = parsed.port
    netloc = f"{userinfo}{hostname}"
    if port is not None and port != default_port:
        netloc = f"{netloc}:{port}"

    path = _DUPLICATE_SLASH_RE.sub("/", parsed.path or "/")
    path = path.rstrip("/") or "/"

    filtered_query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        normalized_key = key.strip().lower()
        if normalized_key in _TRACKING_QUERY_PARAM_NAMES:
            continue
        if normalized_key.startswith(_TRACKING_QUERY_PARAM_PREFIXES):
            continue
        filtered_query_items.append((key, value))
    filtered_query_items.sort()
    query = urlencode(filtered_query_items, doseq=True)

    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_title_text(value: str) -> str:
    """Normalize a title into a lowercase comparable form."""

    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.casefold()
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = _TITLE_TOKEN_RE.sub(" ", normalized)
    normalized = _MULTISPACE_RE.sub(" ", normalized).strip()
    if not normalized:
        raise ValueError("title must not be empty")
    return normalized


def hash_normalized_text(value: str) -> str:
    """Return a stable SHA-256 digest for dedupe fields."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_normalized_title_hash(title: str) -> str:
    """Return a normalized title hash for duplicate comparisons."""

    return hash_normalized_text(normalize_title_text(title))


def build_dedupe_fingerprint(*, title: str, summary: str | None) -> str:
    """Return a lightweight fingerprint based on normalized textual content."""

    normalized_title = normalize_title_text(title)
    normalized_summary = _normalize_fingerprint_text(summary)
    fingerprint_basis = normalized_summary or normalized_title
    return hash_normalized_text(fingerprint_basis)


def window_start(*, now: datetime, duplicate_window_days: int) -> datetime:
    """Compute the lower timestamp bound for recent fingerprint checks."""

    if duplicate_window_days < 0:
        raise ValueError("duplicate_window_days must be >= 0")
    return now - timedelta(days=duplicate_window_days)


def _normalize_fingerprint_text(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = _TITLE_TOKEN_RE.sub(" ", normalized)
    normalized = _MULTISPACE_RE.sub(" ", normalized).strip()
    return normalized
