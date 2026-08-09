"""Repeatable 2–4 week operating metrics derived from persisted workflow state."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.storage import (
    PipelineRun,
    PublishJob,
    PublishJobState,
    ReviewAction,
    ReviewActionType,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)


@dataclass(frozen=True, slots=True)
class OperationMetrics:
    """One reproducible snapshot for a bounded operating window."""

    window_start: datetime
    window_end: datetime
    window_days: int
    pipeline_run_count: int
    discovered_count: int
    saved_count: int
    throughput_per_day: float
    duplicate_removed_count: int
    deduplication_rate: float | None
    review_decision_count: int
    approved_count: int
    rejected_count: int
    edited_count: int
    approval_rate: float | None
    edit_rate: float | None
    terminal_publish_count: int
    published_count: int
    failed_publish_count: int
    publish_success_rate: float | None

    def as_serializable_dict(self) -> dict[str, object]:
        """Return stable JSON/CSV values with ISO-8601 timestamps."""

        values = asdict(self)
        values["window_start"] = self.window_start.isoformat()
        values["window_end"] = self.window_end.isoformat()
        return values


def collect_operation_metrics(
    *,
    database_url: str | None = None,
    days: int = 28,
    now: datetime | None = None,
) -> OperationMetrics:
    """Aggregate throughput, review, dedupe, and publish outcomes for a window."""

    if not 1 <= days <= 90:
        raise ValueError("days must be between 1 and 90")

    window_end = _as_utc(now or datetime.now(timezone.utc))
    window_start = window_end - timedelta(days=days)
    engine = create_database_engine(database_url)
    try:
        ensure_database_schema_is_current(engine)
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            run_totals = session.execute(
                select(
                    func.count(PipelineRun.id),
                    func.coalesce(func.sum(PipelineRun.discovered_count), 0),
                    func.coalesce(func.sum(PipelineRun.saved_count), 0),
                ).where(
                    PipelineRun.started_at >= window_start,
                    PipelineRun.started_at < window_end,
                )
            ).one()
            action_counts = dict(
                session.execute(
                    select(ReviewAction.action_type, func.count(ReviewAction.id))
                    .where(
                        ReviewAction.created_at >= window_start,
                        ReviewAction.created_at < window_end,
                    )
                    .group_by(ReviewAction.action_type)
                ).all()
            )
            publish_counts = dict(
                session.execute(
                    select(PublishJob.state, func.count(PublishJob.id))
                    .where(
                        PublishJob.updated_at >= window_start,
                        PublishJob.updated_at < window_end,
                        PublishJob.state.in_((PublishJobState.PUBLISHED, PublishJobState.FAILED)),
                    )
                    .group_by(PublishJob.state)
                ).all()
            )
    finally:
        engine.dispose()

    pipeline_run_count, discovered_count, saved_count = (int(value) for value in run_totals)
    duplicate_removed_count = max(discovered_count - saved_count, 0)
    approved_count = int(action_counts.get(ReviewActionType.APPROVE, 0))
    rejected_count = int(action_counts.get(ReviewActionType.REJECT, 0))
    edited_count = int(action_counts.get(ReviewActionType.EDIT, 0))
    review_decision_count = approved_count + rejected_count
    published_count = int(publish_counts.get(PublishJobState.PUBLISHED, 0))
    failed_publish_count = int(publish_counts.get(PublishJobState.FAILED, 0))
    terminal_publish_count = published_count + failed_publish_count

    return OperationMetrics(
        window_start=window_start,
        window_end=window_end,
        window_days=days,
        pipeline_run_count=pipeline_run_count,
        discovered_count=discovered_count,
        saved_count=saved_count,
        throughput_per_day=round(saved_count / days, 4),
        duplicate_removed_count=duplicate_removed_count,
        deduplication_rate=_ratio(duplicate_removed_count, discovered_count),
        review_decision_count=review_decision_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        edited_count=edited_count,
        approval_rate=_ratio(approved_count, review_decision_count),
        edit_rate=_ratio(edited_count, review_decision_count),
        terminal_publish_count=terminal_publish_count,
        published_count=published_count,
        failed_publish_count=failed_publish_count,
        publish_success_rate=_ratio(published_count, terminal_publish_count),
    )


def append_metrics_csv(path: Path | str, metrics: OperationMetrics) -> None:
    """Append one snapshot using a stable header suitable for weekly tracking."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row = metrics.as_serializable_dict()
    needs_header = not output_path.exists() or output_path.stat().st_size == 0
    with output_path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
