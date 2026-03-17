"""Source discovery workflow."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.config import ConfigRegistry
from app.connectors.sources import SourceConnectorError, SourceConnectorRegistry
from app.domain import SourceDiscoveryFailure, SourceItemCandidate


@dataclass(frozen=True, slots=True)
class DiscoverSourcesResult:
    """Aggregated source discovery output for one workflow run."""

    items: tuple[SourceItemCandidate, ...]
    failures: tuple[SourceDiscoveryFailure, ...]
    processed_sources: tuple[str, ...]

    @property
    def item_count(self) -> int:
        """Return the number of discovered item candidates."""

        return len(self.items)

    @property
    def failure_count(self) -> int:
        """Return the number of captured failures."""

        return len(self.failures)

    def counts_by_source(self) -> dict[str, int]:
        """Return discovered item counts grouped by source id."""

        counts = Counter(item.source_id for item in self.items)
        return dict(sorted(counts.items()))


def discover_sources(
    config_dir: Path | str = Path("config"),
    *,
    connector_registry: SourceConnectorRegistry | None = None,
) -> DiscoverSourcesResult:
    """Run source discovery for all configured sources."""

    registry = ConfigRegistry.from_directory(Path(config_dir))
    connectors = connector_registry or SourceConnectorRegistry()
    return _discover_sources_from_registry(registry, connectors)


def _discover_sources_from_registry(
    registry: ConfigRegistry,
    connector_registry: SourceConnectorRegistry,
) -> DiscoverSourcesResult:
    """Run source discovery using a preloaded registry."""

    items = []
    failures = []
    processed_sources = []

    for source_id in sorted(registry.sources):
        source_config = registry.get_source(source_id)
        processed_sources.append(source_id)
        connector = connector_registry.get_connector(source_config)

        try:
            result = connector.discover(source_id, source_config)
        except SourceConnectorError as exc:
            failures.append(
                SourceDiscoveryFailure(
                    source_id=source_id,
                    stage=exc.stage,
                    message=str(exc),
                )
            )
            continue

        items.extend(result.items)
        failures.extend(result.failures)

    return DiscoverSourcesResult(
        items=tuple(items),
        failures=tuple(failures),
        processed_sources=tuple(processed_sources),
    )
