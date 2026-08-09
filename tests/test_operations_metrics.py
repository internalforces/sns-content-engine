"""Tests for the repeatable live-operations metrics snapshot."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.analytics import append_metrics_csv, collect_operation_metrics
from app.storage import (
    DraftVariantState,
    PipelineRun,
    PublishJob,
    PublishJobState,
    ReviewAction,
    ReviewActionType,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)


def test_collect_operation_metrics_uses_documented_denominators(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'metrics.db'}"
    engine = create_database_engine(database_url)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)
    measured_at = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
    event_at = measured_at - timedelta(minutes=1)
    with session_scope(session_factory) as session:
        session.add(
            PipelineRun(
                workflow_name="run_local",
                started_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
                discovered_count=10,
                saved_count=7,
            )
        )
        session.add_all(
            [
                _review_action(1, ReviewActionType.APPROVE, event_at),
                _review_action(2, ReviewActionType.APPROVE, event_at),
                _review_action(3, ReviewActionType.REJECT, event_at),
                _review_action(4, ReviewActionType.EDIT, event_at),
            ]
        )
        session.add_all(
            [
                _publish_job(1, PublishJobState.PUBLISHED, event_at),
                _publish_job(2, PublishJobState.PUBLISHED, event_at),
                _publish_job(3, PublishJobState.FAILED, event_at),
            ]
        )
    engine.dispose()

    metrics = collect_operation_metrics(database_url=database_url, days=14, now=measured_at)

    assert metrics.saved_count == 7
    assert metrics.throughput_per_day == 0.5
    assert metrics.duplicate_removed_count == 3
    assert metrics.deduplication_rate == 0.3
    assert metrics.approval_rate == 0.6667
    assert metrics.edit_rate == 0.3333
    assert metrics.publish_success_rate == 0.6667


def test_append_metrics_csv_writes_one_header_and_reusable_rows(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'empty.db'}"
    engine = create_database_engine(database_url)
    create_all_tables(engine)
    engine.dispose()
    measured_at = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
    metrics = collect_operation_metrics(database_url=database_url, days=28, now=measured_at)
    output = tmp_path / "metrics.csv"

    append_metrics_csv(output, metrics)
    append_metrics_csv(output, metrics)

    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert rows[0]["window_days"] == "28"
    assert rows[0]["approval_rate"] == ""


def _review_action(action_id: int, action_type: ReviewActionType, created_at: datetime) -> ReviewAction:
    return ReviewAction(
        id=action_id,
        draft_variant_id=action_id,
        action_type=action_type,
        reviewer="demo-operator",
        before_text="before",
        after_text="after",
        draft_state_before=DraftVariantState.PENDING_REVIEW,
        draft_state_after=DraftVariantState.APPROVED,
        created_at=created_at,
    )


def _publish_job(job_id: int, state: PublishJobState, updated_at: datetime) -> PublishJob:
    return PublishJob(
        id=job_id,
        draft_variant_id=job_id,
        channel="x",
        idempotency_key=f"metrics-job-{job_id}",
        state=state,
        updated_at=updated_at,
    )
