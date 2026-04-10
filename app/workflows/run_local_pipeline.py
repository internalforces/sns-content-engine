"""One-shot local finance pipeline workflow."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.connectors.llm import DraftGenerationProvider
from app.connectors.sources import SourceConnectorRegistry
from app.services import ArticleExtractor, ArticleHtmlFetcher, SummaryRegenerator
from app.storage import (
    PipelineRun,
    PipelineRunRepository,
    PipelineRunStage,
    PipelineRunStageRepository,
    PipelineRunStatus,
    PipelineStage,
    SourceItemRepository,
    StageExecutionStatus,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)
from app.workflows.build_content_briefs import build_content_briefs
from app.workflows.enrich_articles import enrich_articles
from app.workflows.generate_drafts import generate_drafts
from app.workflows.ingest_sources import ingest_sources


@dataclass(frozen=True, slots=True)
class RunLocalPipelineResult:
    """Aggregated result for the local one-shot finance pipeline."""

    pipeline_run_id: int
    status: PipelineRunStatus
    ingest_discovered_count: int
    ingest_saved_count: int
    enrichment_enriched_count: int
    brief_created_count: int
    draft_created_variant_count: int
    failure_count: int
    created_draft_ids: tuple[int, ...] = ()


def run_local_pipeline(
    config_dir: Path | str = Path("config"),
    *,
    database_url: str | None = None,
    connector_registry: SourceConnectorRegistry | None = None,
    llm_provider: DraftGenerationProvider | None = None,
    html_fetcher: ArticleHtmlFetcher | None = None,
    article_extractor: ArticleExtractor | None = None,
    summary_regenerator: SummaryRegenerator | None = None,
    session_factory=None,
    now: datetime | None = None,
) -> RunLocalPipelineResult:
    """Run the local finance MVP pipeline once and stop at pending review."""

    event_time = _normalize_now(now)

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
        run_id = _create_pipeline_run(session_factory, started_at=event_time)

        ingest_result = ingest_sources(
            config_dir,
            connector_registry=connector_registry,
            database_url=database_url,
            session_factory=session_factory,
            now=event_time,
        )
        _record_stage(
            session_factory,
            pipeline_run_id=run_id,
            stage=PipelineStage.RSS_DISCOVERED,
            status=(
                StageExecutionStatus.FAILED if ingest_result.failure_count else StageExecutionStatus.SUCCEEDED
            ),
            item_count=ingest_result.discovered_count,
            success_count=ingest_result.discovered_count - ingest_result.failure_count,
            failure_count=ingest_result.failure_count,
            started_at=event_time,
            completed_at=_normalize_now(None),
            latest_error_code="discover_failed" if ingest_result.failure_count else None,
            latest_error_message=(
                ingest_result.failures[-1].message if ingest_result.failures else None
            ),
            summary_json={"processed_sources": list(ingest_result.processed_sources)},
        )
        _record_stage(
            session_factory,
            pipeline_run_id=run_id,
            stage=PipelineStage.SAVED,
            status=(StageExecutionStatus.FAILED if ingest_result.duplicate_count == 0 and ingest_result.saved_count == 0 and ingest_result.discovered_count > 0 else StageExecutionStatus.SUCCEEDED),
            item_count=ingest_result.discovered_count,
            success_count=ingest_result.saved_count,
            failure_count=ingest_result.failure_count,
            started_at=event_time,
            completed_at=_normalize_now(None),
            summary_json={
                "duplicate_count": ingest_result.duplicate_count,
                "duplicate_reasons": ingest_result.duplicate_counts_by_reason(),
            },
        )

        enrichment_result = enrich_articles(
            config_dir,
            database_url=database_url,
            session_factory=session_factory,
            html_fetcher=html_fetcher,
            article_extractor=article_extractor,
            summary_regenerator=summary_regenerator,
            now=event_time,
        )
        enrichment_failures = enrichment_result.failure_counts_by_stage()
        _record_stage(
            session_factory,
            pipeline_run_id=run_id,
            stage=PipelineStage.HTML_FETCH,
            status=(StageExecutionStatus.FAILED if enrichment_failures.get(PipelineStage.HTML_FETCH.value) else StageExecutionStatus.SUCCEEDED),
            item_count=enrichment_result.processed_count,
            success_count=enrichment_result.processed_count - enrichment_failures.get(PipelineStage.HTML_FETCH.value, 0),
            failure_count=enrichment_failures.get(PipelineStage.HTML_FETCH.value, 0),
            started_at=event_time,
            completed_at=_normalize_now(None),
        )
        _record_stage(
            session_factory,
            pipeline_run_id=run_id,
            stage=PipelineStage.ARTICLE_EXTRACT,
            status=(StageExecutionStatus.FAILED if enrichment_failures.get(PipelineStage.ARTICLE_EXTRACT.value) else StageExecutionStatus.SUCCEEDED),
            item_count=enrichment_result.processed_count,
            success_count=enrichment_result.processed_count - enrichment_failures.get(PipelineStage.ARTICLE_EXTRACT.value, 0),
            failure_count=enrichment_failures.get(PipelineStage.ARTICLE_EXTRACT.value, 0),
            started_at=event_time,
            completed_at=_normalize_now(None),
        )
        _record_stage(
            session_factory,
            pipeline_run_id=run_id,
            stage=PipelineStage.SUMMARY_REGENERATE,
            status=(StageExecutionStatus.FAILED if enrichment_failures.get(PipelineStage.SUMMARY_REGENERATE.value) else StageExecutionStatus.SUCCEEDED),
            item_count=enrichment_result.processed_count,
            success_count=enrichment_result.enriched_count,
            failure_count=enrichment_failures.get(PipelineStage.SUMMARY_REGENERATE.value, 0),
            started_at=event_time,
            completed_at=_normalize_now(None),
            latest_error_code=(enrichment_result.outcomes[-1].failure_code if enrichment_result.failed_count else None),
        )

        brief_result = build_content_briefs(
            config_dir,
            database_url=database_url,
            session_factory=session_factory,
        )
        _record_stage(
            session_factory,
            pipeline_run_id=run_id,
            stage=PipelineStage.BRIEF_BUILD,
            status=StageExecutionStatus.SUCCEEDED,
            item_count=brief_result.processed_count,
            success_count=brief_result.created_count + brief_result.existing_count,
            failure_count=0,
            started_at=event_time,
            completed_at=_normalize_now(None),
            summary_json=brief_result.counts_by_status(),
        )

        drafts_result = generate_drafts(
            config_dir,
            database_url=database_url,
            session_factory=session_factory,
            llm_provider=llm_provider,
        )
        _record_stage(
            session_factory,
            pipeline_run_id=run_id,
            stage=PipelineStage.DRAFT_GENERATE,
            status=StageExecutionStatus.SUCCEEDED,
            item_count=drafts_result.processed_count,
            success_count=drafts_result.created_variant_count,
            failure_count=0,
            started_at=event_time,
            completed_at=_normalize_now(None),
            summary_json=drafts_result.counts_by_status(),
        )
        _record_stage(
            session_factory,
            pipeline_run_id=run_id,
            stage=PipelineStage.PENDING_REVIEW,
            status=StageExecutionStatus.SUCCEEDED,
            item_count=drafts_result.created_variant_count,
            success_count=drafts_result.created_variant_count,
            failure_count=0,
            started_at=event_time,
            completed_at=_normalize_now(None),
        )

        policy_history_summary = _build_policy_history_summary(
            session_factory,
            source_item_ids=enrichment_result.processed_source_item_ids,
            skipped_count=enrichment_result.skipped_count,
        )
        total_failures = ingest_result.failure_count + enrichment_result.failed_count
        final_status = PipelineRunStatus.PARTIAL if total_failures else PipelineRunStatus.SUCCEEDED
        _finish_pipeline_run(
            session_factory,
            pipeline_run_id=run_id,
            completed_at=_normalize_now(None),
            status=final_status,
            source_count=len(ingest_result.processed_sources),
            discovered_count=ingest_result.discovered_count,
            saved_count=ingest_result.saved_count,
            enriched_count=enrichment_result.enriched_count,
            summarized_count=enrichment_result.enriched_count,
            brief_count=brief_result.created_count,
            draft_count=drafts_result.created_variant_count,
            failure_count=total_failures,
            latest_error_code=(enrichment_result.outcomes[-1].failure_code if enrichment_result.failed_count else ("discover_failed" if ingest_result.failure_count else None)),
            latest_error_message=(ingest_result.failures[-1].message if ingest_result.failure_count else None),
            summary_json={
                "duplicate_count": ingest_result.duplicate_count,
                "enrichment_existing_count": enrichment_result.existing_count,
                "brief_existing_count": brief_result.existing_count,
                "draft_existing_count": drafts_result.existing_count,
                "policy_mode_counts": policy_history_summary["policy_mode_counts"],
                "attribution_required_count": policy_history_summary["attribution_required_count"],
                "policy_skipped_count": policy_history_summary["policy_skipped_count"],
                "rewrite_providers": list(drafts_result.provider_names),
            },
        )

        return RunLocalPipelineResult(
            pipeline_run_id=run_id,
            status=final_status,
            ingest_discovered_count=ingest_result.discovered_count,
            ingest_saved_count=ingest_result.saved_count,
            enrichment_enriched_count=enrichment_result.enriched_count,
            brief_created_count=brief_result.created_count,
            draft_created_variant_count=drafts_result.created_variant_count,
            created_draft_ids=drafts_result.created_draft_variant_ids,
            failure_count=total_failures,
        )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()


def _create_pipeline_run(session_factory, *, started_at: datetime) -> int:
    with session_scope(session_factory) as session:
        repository = PipelineRunRepository(session)
        pipeline_run = repository.add(
            PipelineRun(
                workflow_name="run_local_finance",
                trigger_mode="manual_local",
                status=PipelineRunStatus.RUNNING,
                started_at=started_at,
            )
        )
        return pipeline_run.id


def _record_stage(
    session_factory,
    *,
    pipeline_run_id: int,
    stage: PipelineStage,
    status: StageExecutionStatus,
    item_count: int,
    success_count: int,
    failure_count: int,
    started_at: datetime,
    completed_at: datetime,
    latest_error_code: str | None = None,
    latest_error_message: str | None = None,
    summary_json: dict | None = None,
) -> None:
    with session_scope(session_factory) as session:
        repository = PipelineRunStageRepository(session)
        stage_run, _ = repository.get_or_create(
            PipelineRunStage(
                pipeline_run_id=pipeline_run_id,
                stage=stage,
            )
        )
        stage_run.status = status
        stage_run.item_count = item_count
        stage_run.success_count = success_count
        stage_run.failure_count = failure_count
        stage_run.started_at = started_at
        stage_run.completed_at = completed_at
        stage_run.latest_error_code = latest_error_code
        stage_run.latest_error_message = latest_error_message
        stage_run.summary_json = summary_json
        session.flush()


def _finish_pipeline_run(
    session_factory,
    *,
    pipeline_run_id: int,
    completed_at: datetime,
    status: PipelineRunStatus,
    source_count: int,
    discovered_count: int,
    saved_count: int,
    enriched_count: int,
    summarized_count: int,
    brief_count: int,
    draft_count: int,
    failure_count: int,
    latest_error_code: str | None,
    latest_error_message: str | None,
    summary_json: dict | None,
) -> None:
    with session_scope(session_factory) as session:
        repository = PipelineRunRepository(session)
        pipeline_run = repository.get(pipeline_run_id)
        if pipeline_run is None:
            raise ValueError(f"pipeline run {pipeline_run_id} does not exist")
        pipeline_run.status = status
        pipeline_run.completed_at = completed_at
        pipeline_run.source_count = source_count
        pipeline_run.discovered_count = discovered_count
        pipeline_run.saved_count = saved_count
        pipeline_run.enriched_count = enriched_count
        pipeline_run.summarized_count = summarized_count
        pipeline_run.brief_count = brief_count
        pipeline_run.draft_count = draft_count
        pipeline_run.failure_count = failure_count
        pipeline_run.latest_error_code = latest_error_code
        pipeline_run.latest_error_message = latest_error_message
        pipeline_run.summary_json = summary_json
        session.flush()


def _build_policy_history_summary(
    session_factory,
    *,
    source_item_ids: tuple[int, ...],
    skipped_count: int,
) -> dict[str, object]:
    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        source_items = repository.list_by_ids(source_item_ids)

    policy_mode_counts = Counter(item.policy_mode.value for item in source_items)
    attribution_required_count = sum(item.require_attribution for item in source_items)
    return {
        "policy_mode_counts": dict(sorted(policy_mode_counts.items())),
        "attribution_required_count": attribution_required_count,
        "policy_skipped_count": skipped_count,
    }


def _normalize_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)
