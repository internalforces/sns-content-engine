"""Shared domain models for the sns-content-engine."""

from app.domain.account_matching import AccountMatchCandidate, select_top_account_candidates
from app.domain.content_brief import ContentBriefAngle, ContentBriefData
from app.domain.landing_resolution import LandingDecision
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
    extract_source_tags,
)

__all__ = [
    "AccountMatchCandidate",
    "ContentBriefAngle",
    "ContentBriefData",
    "DuplicateCheckResult",
    "DuplicateReason",
    "LandingDecision",
    "RawSourceItem",
    "SourceConnectorResult",
    "SourceDiscoveryFailure",
    "SourceItemCandidate",
    "SourceNormalizationError",
    "build_dedupe_fingerprint",
    "build_normalized_title_hash",
    "canonicalize_url",
    "extract_source_tags",
    "normalize_title_text",
    "select_top_account_candidates",
]
