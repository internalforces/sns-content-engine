"""Pre-save source ingestion workflow with duplicate blocking."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.config import ConfigRegistry
from app.connectors.sources import SourceConnectorRegistry
from app.domain import DuplicateReason, SourceDiscoveryFailure, SourceItemCandidate
from app.services import SourceItemDeduper
from app.storage import (
    SourcePolicyMode,
    SourceItemRecentFingerprintClaim,
    SourceItemRecentFingerprintClaimRepository,
    SourceItem,
    SourceItemRepository,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)
from app.workflows.discover_sources import _discover_sources_from_registry


@dataclass(frozen=True, slots=True)
class SourceIngestOutcome:
    """Outcome of attempting to persist one discovered source item candidate."""

    candidate: SourceItemCandidate
    status: str
    source_item_id: int | None = None
    duplicate_reason: DuplicateReason | None = None
    matched_item_id: int | None = None


@dataclass(frozen=True, slots=True)
class IngestSourcesResult:
    """Aggregated ingestion result for one workflow run."""

    outcomes: tuple[SourceIngestOutcome, ...]
    failures: tuple[SourceDiscoveryFailure, ...]
    processed_sources: tuple[str, ...]

    @property
    def discovered_count(self) -> int:
        """Return the number of discovered candidates processed for persistence."""

        return len(self.outcomes)

    @property
    def saved_count(self) -> int:
        """Return the number of new source items persisted."""

        return sum(outcome.status == "saved" for outcome in self.outcomes)

    @property
    def duplicate_count(self) -> int:
        """Return the number of candidates blocked as duplicates."""

        return sum(outcome.status == "duplicate" for outcome in self.outcomes)

    @property
    def failure_count(self) -> int:
        """Return the number of discovery failures captured during the run."""

        return len(self.failures)

    def duplicate_counts_by_reason(self) -> dict[str, int]:
        """Return duplicate counts grouped by reason."""

        counts = Counter(
            outcome.duplicate_reason.value
            for outcome in self.outcomes
            if outcome.duplicate_reason is not None
        )
        return dict(sorted(counts.items()))


def ingest_sources(
    config_dir: Path | str = Path("config"),
    *,
    connector_registry: SourceConnectorRegistry | None = None,
    database_url: str | None = None,
    session_factory=None,
    now: datetime | None = None,
) -> IngestSourcesResult:
    """Discover source items and persist only non-duplicates."""

    registry = ConfigRegistry.from_directory(Path(config_dir))
    connectors = connector_registry or SourceConnectorRegistry()
    discovery_result = _discover_sources_from_registry(registry, connectors)

    owned_engine = None
    if session_factory is None:
        owned_engine = create_database_engine(database_url)
        ensure_database_schema_is_current(owned_engine)
        session_factory = create_session_factory(owned_engine)
    else:
        bound_engine = _resolve_bound_engine(session_factory)
        if bound_engine is not None:
            ensure_database_schema_is_current(bound_engine)

    try:
        with session_scope(session_factory) as session:
            repository = SourceItemRepository(session)
            fingerprint_claims = SourceItemRecentFingerprintClaimRepository(session)
            deduper = SourceItemDeduper(
                repository,
                fingerprint_claims=fingerprint_claims,
            )
            outcomes = []
            current_time = _normalize_now(now)

            for candidate in discovery_result.items:
                source_config = registry.get_source(candidate.source_id)
                try:
                    with session.begin_nested():
                        duplicate_check = deduper.check_duplicate(
                            candidate,
                            duplicate_window_days=source_config.duplicate_window_days,
                            now=current_time,
                        )
                        if duplicate_check.is_duplicate:
                            outcomes.append(
                                SourceIngestOutcome(
                                    candidate=candidate,
                                    status="duplicate",
                                    duplicate_reason=duplicate_check.reason,
                                    matched_item_id=duplicate_check.matched_item_id,
                                )
                            )
                            continue

                        claim = _reserve_recent_fingerprint_claim(
                            fingerprint_claims,
                            candidate,
                            duplicate_window_days=source_config.duplicate_window_days,
                            now=current_time,
                        )
                        source_item = repository.add(
                            _candidate_to_source_item(
                                candidate,
                                policy_mode=source_config.policy_mode,
                                allow_full_text_fetch=source_config.allow_full_text_fetch,
                                allow_llm_rewrite=source_config.allow_llm_rewrite,
                                require_attribution=source_config.require_attribution,
                            )
                        )
                        if claim is not None:
                            claim.source_item = source_item
                            session.flush()

                        outcomes.append(
                            SourceIngestOutcome(
                                candidate=candidate,
                                status="saved",
                                source_item_id=source_item.id,
                            )
                        )
                except IntegrityError:
                    duplicate_check = deduper.check_duplicate(
                        candidate,
                        duplicate_window_days=source_config.duplicate_window_days,
                        now=current_time,
                    )
                    if not duplicate_check.is_duplicate:
                        raise
                    outcomes.append(
                        SourceIngestOutcome(
                            candidate=candidate,
                            status="duplicate",
                            duplicate_reason=duplicate_check.reason,
                            matched_item_id=duplicate_check.matched_item_id,
                        )
                    )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return IngestSourcesResult(
        outcomes=tuple(outcomes),
        failures=discovery_result.failures,
        processed_sources=discovery_result.processed_sources,
    )


def _candidate_to_source_item(
    candidate: SourceItemCandidate,
    *,
    policy_mode: str,
    allow_full_text_fetch: bool,
    allow_llm_rewrite: bool,
    require_attribution: bool,
) -> SourceItem:
    return SourceItem(
        source_key=candidate.source_id,
        external_id=candidate.external_id,
        source_url=candidate.source_url,
        title=candidate.title,
        summary=candidate.summary,
        published_at=candidate.published_at,
        raw_payload=candidate.raw_payload,
        policy_mode=SourcePolicyMode(policy_mode),
        allow_full_text_fetch=allow_full_text_fetch,
        allow_llm_rewrite=allow_llm_rewrite,
        require_attribution=require_attribution,
    )


def _reserve_recent_fingerprint_claim(
    repository: SourceItemRecentFingerprintClaimRepository,
    candidate: SourceItemCandidate,
    *,
    duplicate_window_days: int,
    now: datetime,
) -> SourceItemRecentFingerprintClaim | None:
    if duplicate_window_days == 0:
        return None

    return repository.add(
        SourceItemRecentFingerprintClaim(
            dedupe_fingerprint=candidate.dedupe_fingerprint,
            expires_at=now + timedelta(days=duplicate_window_days),
        )
    )


def _normalize_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _resolve_bound_engine(session_factory):
    return getattr(session_factory, "kw", {}).get("bind")
