"""Duplicate detection service for normalized source items."""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain import DuplicateCheckResult, DuplicateReason, SourceItemCandidate
from app.domain.source_deduplication import window_start
from app.storage import SourceItemRecentFingerprintClaimRepository, SourceItemRepository


class SourceItemDeduper:
    """Check whether a normalized candidate should be blocked as a duplicate."""

    def __init__(
        self,
        repository: SourceItemRepository,
        *,
        fingerprint_claims: SourceItemRecentFingerprintClaimRepository | None = None,
    ) -> None:
        self.repository = repository
        self.fingerprint_claims = fingerprint_claims

    def check_duplicate(
        self,
        candidate: SourceItemCandidate,
        *,
        duplicate_window_days: int,
        now: datetime | None = None,
    ) -> DuplicateCheckResult:
        """Return the first matching duplicate reason for a candidate."""

        existing = self.repository.get_by_source_identity(
            candidate.source_id,
            candidate.external_id,
        )
        if existing is not None:
            return DuplicateCheckResult.duplicate(
                DuplicateReason.SOURCE_IDENTITY,
                matched_item_id=existing.id,
            )

        existing = self.repository.get_by_canonical_url(candidate.canonical_url)
        if existing is not None:
            return DuplicateCheckResult.duplicate(
                DuplicateReason.CANONICAL_URL,
                matched_item_id=existing.id,
            )

        existing = self.repository.get_by_normalized_title_hash(candidate.normalized_title_hash)
        if existing is not None:
            return DuplicateCheckResult.duplicate(
                DuplicateReason.NORMALIZED_TITLE_HASH,
                matched_item_id=existing.id,
            )

        if duplicate_window_days == 0:
            return DuplicateCheckResult.unique()

        current_time = _normalize_now(now)
        if self.fingerprint_claims is not None:
            self.fingerprint_claims.delete_expired(as_of=current_time)
            existing_claim = self.fingerprint_claims.get_active(
                candidate.dedupe_fingerprint,
                as_of=current_time,
            )
            if existing_claim is not None:
                return DuplicateCheckResult.duplicate(
                    DuplicateReason.RECENT_FINGERPRINT,
                    matched_item_id=existing_claim.source_item_id,
                )

        existing = self.repository.get_recent_by_dedupe_fingerprint(
            candidate.dedupe_fingerprint,
            created_since=window_start(
                now=current_time,
                duplicate_window_days=duplicate_window_days,
            ),
        )
        if existing is not None:
            return DuplicateCheckResult.duplicate(
                DuplicateReason.RECENT_FINGERPRINT,
                matched_item_id=existing.id,
            )

        return DuplicateCheckResult.unique()


def _normalize_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)
