"""Manual CSV source connector."""

from __future__ import annotations

import csv

from app.config.schemas import ManualCsvSourceConfig
from app.connectors.sources.base import SourceConnector, SourceParseError, SourceReadError
from app.connectors.sources.normalizer import normalize_raw_source_item
from app.domain.source_ingestion import (
    RawSourceItem,
    SourceConnectorResult,
    SourceDiscoveryFailure,
    SourceNormalizationError,
)


class ManualCsvSourceConnector(SourceConnector):
    """Discover items from a manually curated CSV file."""

    def discover(self, source_id: str, config: ManualCsvSourceConfig) -> SourceConnectorResult:
        try:
            with config.path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None:
                    raise SourceParseError("CSV file must include a header row")

                items = []
                failures = []
                for row_number, row in enumerate(reader, start=2):
                    normalized_row = _normalize_row(row)
                    if _row_is_empty(normalized_row):
                        continue

                    raw_item = RawSourceItem(
                        source_id=source_id,
                        external_id=_lookup(normalized_row, "external_id", "id", "guid"),
                        source_url=_lookup(normalized_row, "url", "source_url", "link"),
                        title=_lookup(normalized_row, "title", "headline"),
                        summary=_lookup(normalized_row, "summary", "description"),
                        published_at=_lookup(
                            normalized_row,
                            "published_at",
                            "published",
                            "pub_date",
                            "lastmod",
                        ),
                        raw_payload={key: value for key, value in normalized_row.items() if value is not None},
                    )
                    try:
                        items.append(normalize_raw_source_item(raw_item))
                    except SourceNormalizationError as exc:
                        failures.append(
                            SourceDiscoveryFailure(
                                source_id=source_id,
                                stage="normalize",
                                item_key=f"row {row_number}",
                                message=str(exc),
                            )
                        )
        except FileNotFoundError:
            return _failure_result(source_id, SourceReadError.stage, f"CSV file not found: {config.path}")
        except UnicodeDecodeError as exc:
            return _failure_result(source_id, SourceReadError.stage, f"could not decode CSV file: {exc}")
        except OSError as exc:
            return _failure_result(source_id, SourceReadError.stage, f"could not read CSV file: {exc}")
        except csv.Error as exc:
            return _failure_result(source_id, SourceParseError.stage, f"invalid CSV: {exc}")
        except SourceParseError as exc:
            return _failure_result(source_id, exc.stage, str(exc))

        return SourceConnectorResult(items=tuple(items), failures=tuple(failures))


def _normalize_row(row: dict[str | None, str | None]) -> dict[str, str | None]:
    normalized_row: dict[str, str | None] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized_key = key.strip().lower()
        normalized_row[normalized_key] = value.strip() if value is not None else None
    return normalized_row


def _lookup(row: dict[str, str | None], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return None


def _row_is_empty(row: dict[str, str | None]) -> bool:
    return all(value in (None, "") for value in row.values())


def _failure_result(source_id: str, stage: str, message: str) -> SourceConnectorResult:
    return SourceConnectorResult(
        failures=(SourceDiscoveryFailure(source_id=source_id, stage=stage, message=message),)
    )
