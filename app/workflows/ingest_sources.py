"""Pre-save source ingestion workflow with duplicate blocking."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.config import ConfigRegistry
from app.connectors.sources import SourceConnectorRegistry
from app.domain import DuplicateReason, SourceDiscoveryFailure, SourceItemCandidate
from app.services import SourceItemDeduper
from app.storage import (
    SourceItem,
    SourceItemRepository,
    create_database_engine,
    create_session_factory,
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
        session_factory = create_session_factory(owned_engine)

    try:
        with session_scope(session_factory) as session:
            repository = SourceItemRepository(session)
            deduper = SourceItemDeduper(repository)
            outcomes = []

            for candidate in discovery_result.items:
                source_config = registry.get_source(candidate.source_id)
                duplicate_check = deduper.check_duplicate(
                    candidate,
                    duplicate_window_days=source_config.duplicate_window_days,
                    now=now,
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

                source_item = repository.add(_candidate_to_source_item(candidate))
                outcomes.append(
                    SourceIngestOutcome(
                        candidate=candidate,
                        status="saved",
                        source_item_id=source_item.id,
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


def _candidate_to_source_item(candidate: SourceItemCandidate) -> SourceItem:
    return SourceItem(
        source_key=candidate.source_id,
        external_id=candidate.external_id,
        source_url=candidate.source_url,
        title=candidate.title,
        summary=candidate.summary,
        published_at=candidate.published_at,
        raw_payload=candidate.raw_payload,
    )
