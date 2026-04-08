"""Readable run-history and failure query helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    PipelineRunRepository,
    PublishJob,
    PublishLog,
    PublishLogRepository,
    PublishJobRepository,
    PublishJobState,
    SourceItem,
    StageExecutionStatus,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)


class PublishJobNotFoundError(ValueError):
    """Raised when a referenced publish job does not exist."""


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


@dataclass(frozen=True, slots=True)
class ArticleStatusRow:
    source_item_id: int
    article_enrichment_id: int | None
    source_name: str
    title: str
    original_url: str
    article_url: str | None
    published_at: datetime | None
    discovered_at: datetime
    enrichment_state: str
    fetch_status: str
    extract_status: str
    summarize_status: str
    last_failure_message: str | None


@dataclass(frozen=True, slots=True)
class ArticleStatusResult:
    articles: tuple[ArticleStatusRow, ...]


@dataclass(frozen=True, slots=True)
class PublishJobListRow:
    publish_job_id: int
    draft_id: int
    brief_id: int
    account_key: str
    channel: str
    state: str
    scheduled_for: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    attempt_count: int
    external_post_id: str | None
    last_error: str | None
    variant_index: int
    draft_state: str
    brief_title: str
    source_title: str


@dataclass(frozen=True, slots=True)
class PublishJobListResult:
    jobs: tuple[PublishJobListRow, ...]


@dataclass(frozen=True, slots=True)
class PublishJobDetailResult:
    job: PublishJob
    publish_logs: tuple[PublishLog, ...]


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


def list_article_statuses(*, database_url: str | None = None, session_factory=None, limit: int = 50) -> ArticleStatusResult:
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
            statement = (
                select(SourceItem, ArticleEnrichment)
                .outerjoin(ArticleEnrichment, ArticleEnrichment.source_item_id == SourceItem.id)
                .order_by(SourceItem.created_at.desc(), SourceItem.id.desc())
                .limit(limit)
            )
            rows = tuple(
                _build_article_status_row(source_item, enrichment)
                for source_item, enrichment in session.execute(statement).all()
            )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return ArticleStatusResult(articles=rows)


def list_publish_jobs(
    *,
    database_url: str | None = None,
    session_factory=None,
    state: PublishJobState | None = None,
    account_key: str | None = None,
    channel: str | None = None,
    limit: int = 50,
) -> PublishJobListResult:
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
            jobs = tuple(
                PublishJobListRow(
                    publish_job_id=job.id,
                    draft_id=job.draft_variant.id,
                    brief_id=job.draft_variant.content_brief.id,
                    account_key=job.draft_variant.content_brief.account_key,
                    channel=job.channel,
                    state=job.state.value,
                    scheduled_for=job.scheduled_for,
                    published_at=job.published_at,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    attempt_count=job.attempt_count,
                    external_post_id=job.external_post_id,
                    last_error=job.last_error,
                    variant_index=job.draft_variant.variant_index,
                    draft_state=job.draft_variant.state.value,
                    brief_title=job.draft_variant.content_brief.title,
                    source_title=job.draft_variant.content_brief.source_item.title,
                )
                for job in PublishJobRepository(session).list_for_operator(
                    state=state,
                    account_key=account_key,
                    channel=channel,
                    limit=limit,
                )
            )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return PublishJobListResult(jobs=jobs)


def get_publish_job_detail(
    publish_job_id: int,
    *,
    database_url: str | None = None,
    session_factory=None,
) -> PublishJobDetailResult:
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
            jobs = PublishJobRepository(session)
            job = jobs.get_detail(publish_job_id)
            if job is None:
                raise PublishJobNotFoundError(f"publish job {publish_job_id} was not found")

            publish_logs = tuple(PublishLogRepository(session).list_for_job(publish_job_id))
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return PublishJobDetailResult(job=job, publish_logs=publish_logs)


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


def _build_article_status_row(source_item: SourceItem, enrichment: ArticleEnrichment | None) -> ArticleStatusRow:
    if enrichment is None:
        fetch_status = StageExecutionStatus.PENDING.value
        extract_status = StageExecutionStatus.PENDING.value
        summarize_status = StageExecutionStatus.PENDING.value
        article_url = None
        article_enrichment_id = None
        source_name = source_item.source_key
        published_at = source_item.published_at
        discovered_at = source_item.created_at
        last_failure_message = None
    else:
        fetch_status = enrichment.html_fetch_status.value
        extract_status = enrichment.article_extract_status.value
        summarize_status = enrichment.summary_regenerate_status.value
        article_url = enrichment.article_url
        article_enrichment_id = enrichment.id
        source_name = enrichment.source_name or source_item.source_key
        published_at = enrichment.published_at or source_item.published_at
        discovered_at = enrichment.discovered_at
        last_failure_message = enrichment.failure_message

    return ArticleStatusRow(
        source_item_id=source_item.id,
        article_enrichment_id=article_enrichment_id,
        source_name=source_name,
        title=source_item.title,
        original_url=source_item.source_url,
        article_url=article_url,
        published_at=published_at,
        discovered_at=discovered_at,
        enrichment_state=_derive_article_enrichment_state(enrichment),
        fetch_status=fetch_status,
        extract_status=extract_status,
        summarize_status=summarize_status,
        last_failure_message=last_failure_message,
    )


def _derive_article_enrichment_state(enrichment: ArticleEnrichment | None) -> str:
    if enrichment is None:
        return "pending"
    if enrichment.failure_code:
        return "failed"
    if _is_policy_skipped(enrichment):
        return "skipped"
    if enrichment.summary_regenerate_status is StageExecutionStatus.SUCCEEDED:
        return "enriched"
    if any(
        status is StageExecutionStatus.SUCCEEDED
        for status in (
            enrichment.html_fetch_status,
            enrichment.article_extract_status,
            enrichment.summary_regenerate_status,
        )
    ):
        return "in_progress"
    return "pending"


def _is_policy_skipped(enrichment: ArticleEnrichment) -> bool:
    return bool(enrichment.policy_decision_reason) and (
        enrichment.html_fetch_status is StageExecutionStatus.SKIPPED
        or enrichment.summary_regenerate_status is StageExecutionStatus.SKIPPED
    )
