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
    trigger_mode: str
    started_at: datetime
    completed_at: datetime | None
    discovered_count: int
    saved_count: int
    enriched_count: int
    brief_count: int
    draft_count: int
    failure_count: int
    latest_error_code: str | None
    policy_mode_counts: dict[str, int]
    policy_skipped_count: int
    attribution_required_count: int
    rewrite_providers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PipelineFailureRow:
    source_item_id: int
    article_enrichment_id: int
    title: str
    source_name: str | None
    article_url: str
    source_policy_mode: str
    require_attribution: bool
    failure_stage: str | None
    failure_code: str
    failure_message: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PipelinePolicySkipRow:
    source_item_id: int
    article_enrichment_id: int
    title: str
    source_name: str | None
    article_url: str
    source_policy_mode: str
    require_attribution: bool
    skipped_stage: str
    policy_decision_reason: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PipelineRunHistoryResult:
    runs: tuple[PipelineRunHistoryRow, ...]


@dataclass(frozen=True, slots=True)
class PipelineFailureHistoryResult:
    failures: tuple[PipelineFailureRow, ...]
    policy_skips: tuple[PipelinePolicySkipRow, ...]


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
                    trigger_mode=run.trigger_mode,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    discovered_count=run.discovered_count,
                    saved_count=run.saved_count,
                    enriched_count=run.enriched_count,
                    brief_count=run.brief_count,
                    draft_count=run.draft_count,
                    failure_count=run.failure_count,
                    latest_error_code=run.latest_error_code,
                    policy_mode_counts=_normalize_policy_mode_counts(run.summary_json),
                    policy_skipped_count=_read_int_summary_field(run.summary_json, "policy_skipped_count"),
                    attribution_required_count=_read_int_summary_field(
                        run.summary_json,
                        "attribution_required_count",
                    ),
                    rewrite_providers=_read_string_tuple_summary_field(
                        run.summary_json,
                        "rewrite_providers",
                        fallback_key="rewrite_provider",
                    ),
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
            enrichments = ArticleEnrichmentRepository(session)
            failures = tuple(
                PipelineFailureRow(
                    source_item_id=enrichment.source_item_id,
                    article_enrichment_id=enrichment.id,
                    title=enrichment.source_item.title,
                    source_name=enrichment.source_name,
                    article_url=enrichment.article_url,
                    source_policy_mode=enrichment.source_item.policy_mode.value,
                    require_attribution=enrichment.source_item.require_attribution,
                    failure_stage=enrichment.failure_stage.value if enrichment.failure_stage else None,
                    failure_code=enrichment.failure_code or "unknown_failure",
                    failure_message=enrichment.failure_message or "실패 사유를 확인하지 못했어요",
                    updated_at=enrichment.updated_at,
                )
                for enrichment in enrichments.list_failed(limit=limit)
            )
            policy_skips = tuple(
                PipelinePolicySkipRow(
                    source_item_id=enrichment.source_item_id,
                    article_enrichment_id=enrichment.id,
                    title=enrichment.source_item.title,
                    source_name=enrichment.source_name,
                    article_url=enrichment.article_url,
                    source_policy_mode=enrichment.source_item.policy_mode.value,
                    require_attribution=enrichment.source_item.require_attribution,
                    skipped_stage=enrichment.last_stage.value,
                    policy_decision_reason=(
                        enrichment.policy_decision_reason
                        or "Policy skip reason was not recorded."
                    ),
                    updated_at=enrichment.updated_at,
                )
                for enrichment in enrichments.list_policy_skipped(limit=limit)
            )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return PipelineFailureHistoryResult(failures=failures, policy_skips=policy_skips)


def _normalize_policy_mode_counts(summary_json: dict | None) -> dict[str, int]:
    if not isinstance(summary_json, dict):
        return {}

    raw_counts = summary_json.get("policy_mode_counts")
    if not isinstance(raw_counts, dict):
        return {}

    normalized: dict[str, int] = {}
    for key, value in raw_counts.items():
        if not isinstance(key, str) or not key.strip():
            continue
        normalized[key] = _coerce_non_negative_int(value)
    return dict(sorted(normalized.items()))


def _read_int_summary_field(summary_json: dict | None, key: str) -> int:
    if not isinstance(summary_json, dict):
        return 0
    return _coerce_non_negative_int(summary_json.get(key))


def _read_string_tuple_summary_field(
    summary_json: dict | None,
    key: str,
    *,
    fallback_key: str | None = None,
) -> tuple[str, ...]:
    if not isinstance(summary_json, dict):
        return ()

    raw_value = summary_json.get(key)
    if raw_value is None and fallback_key is not None:
        raw_value = summary_json.get(fallback_key)

    if isinstance(raw_value, str):
        value = raw_value.strip()
        return (value,) if value else ()

    if not isinstance(raw_value, (list, tuple)):
        return ()

    normalized = tuple(
        value.strip()
        for value in raw_value
        if isinstance(value, str) and value.strip()
    )
    return tuple(sorted(set(normalized)))


def _coerce_non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    return 0
