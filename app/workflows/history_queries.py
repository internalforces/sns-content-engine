"""Readable run-history and failure query helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.storage import (
    ArticleEnrichmentRepository,
    PipelineRunRepository,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)


@dataclass(frozen=True, slots=True)
class PipelineRunHistoryRow:
    run_id: int
    workflow_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    discovered_count: int
    saved_count: int
    enriched_count: int
    brief_count: int
    draft_count: int
    failure_count: int


@dataclass(frozen=True, slots=True)
class PipelineFailureRow:
    source_item_id: int
    article_enrichment_id: int
    title: str
    source_name: str | None
    article_url: str
    failure_stage: str | None
    failure_code: str
    failure_message: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PipelineRunHistoryResult:
    runs: tuple[PipelineRunHistoryRow, ...]


@dataclass(frozen=True, slots=True)
class PipelineFailureHistoryResult:
    failures: tuple[PipelineFailureRow, ...]


def list_pipeline_runs(*, database_url: str | None = None, session_factory=None, limit: int = 20) -> PipelineRunHistoryResult:
    owned_engine = None
    if session_factory is None:
        owned_engine = create_database_engine(database_url)
        ensure_database_schema_is_current(owned_engine)
        session_factory = create_session_factory(owned_engine)
    else:
        bound_engine = getattr(session_factory, "kw", {}).get("bind")
        if bound_engine is not None:
            ensure_database_schema_is_current(bound_engine)

    try:
        with session_scope(session_factory) as session:
            rows = tuple(
                PipelineRunHistoryRow(
                    run_id=run.id,
                    workflow_name=run.workflow_name,
                    status=run.status.value,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    discovered_count=run.discovered_count,
                    saved_count=run.saved_count,
                    enriched_count=run.enriched_count,
                    brief_count=run.brief_count,
                    draft_count=run.draft_count,
                    failure_count=run.failure_count,
                )
                for run in PipelineRunRepository(session).list_recent(limit=limit)
            )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return PipelineRunHistoryResult(runs=rows)


def list_pipeline_failures(*, database_url: str | None = None, session_factory=None, limit: int = 50) -> PipelineFailureHistoryResult:
    owned_engine = None
    if session_factory is None:
        owned_engine = create_database_engine(database_url)
        ensure_database_schema_is_current(owned_engine)
        session_factory = create_session_factory(owned_engine)
    else:
        bound_engine = getattr(session_factory, "kw", {}).get("bind")
        if bound_engine is not None:
            ensure_database_schema_is_current(bound_engine)

    try:
        with session_scope(session_factory) as session:
            failures = tuple(
                PipelineFailureRow(
                    source_item_id=enrichment.source_item_id,
                    article_enrichment_id=enrichment.id,
                    title=enrichment.source_item.title,
                    source_name=enrichment.source_name,
                    article_url=enrichment.article_url,
                    failure_stage=enrichment.failure_stage.value if enrichment.failure_stage else None,
                    failure_code=enrichment.failure_code or "unknown_failure",
                    failure_message=enrichment.failure_message or "실패 사유를 확인하지 못했어요",
                    updated_at=enrichment.updated_at,
                )
                for enrichment in ArticleEnrichmentRepository(session).list_failed(limit=limit)
            )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return PipelineFailureHistoryResult(failures=failures)
