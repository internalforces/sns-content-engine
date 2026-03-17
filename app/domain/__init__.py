"""Shared domain models for the sns-content-engine."""

from app.domain.source_deduplication import (
    DuplicateCheckResult,
    DuplicateReason,
    build_dedupe_fingerprint,
    build_normalized_title_hash,
    canonicalize_url,
    normalize_title_text,
)
from app.domain.source_ingestion import (
    RawSourceItem,
    SourceConnectorResult,
    SourceDiscoveryFailure,
    SourceItemCandidate,
    SourceNormalizationError,
)

__all__ = [
    "DuplicateCheckResult",
    "DuplicateReason",
    "RawSourceItem",
    "SourceConnectorResult",
    "SourceDiscoveryFailure",
    "SourceItemCandidate",
    "SourceNormalizationError",
    "build_dedupe_fingerprint",
    "build_normalized_title_hash",
    "canonicalize_url",
    "normalize_title_text",
]
