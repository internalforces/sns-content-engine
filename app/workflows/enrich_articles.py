"""Workflow for enriching ingested source items with fetched article content."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.domain import extract_source_tags
from app.services import (
    ArticleExtractError,
    ArticleExtractor,
    ArticleHtmlFetcher,
    HtmlFetcherError,
    SummaryRegenerationError,
    SummaryRegenerator,
)
from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    PipelineStage,
    SourceItemRepository,
    SourceItemState,
    StageExecutionStatus,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)


@dataclass(frozen=True, slots=True)
class EnrichArticleOutcome:
    """Outcome of attempting to enrich one source item."""

    source_item_id: int
    status: str
    article_enrichment_id: int | None = None
    failure_code: str | None = None
    failure_stage: PipelineStage | None = None


@dataclass(frozen=True, slots=True)
class EnrichArticlesResult:
    """Aggregated article enrichment result for one workflow run."""

    processed_source_item_ids: tuple[int, ...]
    outcomes: tuple[EnrichArticleOutcome, ...]

    @property
    def processed_count(self) -> int:
        return len(self.processed_source_item_ids)

    @property
    def enriched_count(self) -> int:
        return sum(outcome.status == "enriched" for outcome in self.outcomes)

    @property
    def failed_count(self) -> int:
        return sum(outcome.status == "failed" for outcome in self.outcomes)

    @property
    def existing_count(self) -> int:
        return sum(outcome.status == "existing" for outcome in self.outcomes)

    @property
    def skipped_count(self) -> int:
        return sum(outcome.status == "skipped" for outcome in self.outcomes)

    def failure_counts_by_stage(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for outcome in self.outcomes:
            if outcome.failure_stage is None:
                continue
            counts[outcome.failure_stage.value] = counts.get(outcome.failure_stage.value, 0) + 1
        return dict(sorted(counts.items()))


def enrich_articles(
    config_dir: Path | str = Path("config"),
    *,
    database_url: str | None = None,
    session_factory=None,
    html_fetcher: ArticleHtmlFetcher | None = None,
    article_extractor: ArticleExtractor | None = None,
    summary_regenerator: SummaryRegenerator | None = None,
    now: datetime | None = None,
) -> EnrichArticlesResult:
    """Fetch, extract, and summarize article pages for ingested source items."""

    del config_dir  # reserved for future source-specific enrichment settings

    fetcher = html_fetcher or ArticleHtmlFetcher()
    extractor = article_extractor or ArticleExtractor()
    regenerator = summary_regenerator or SummaryRegenerator()
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
        with session_scope(session_factory) as session:
            source_items = SourceItemRepository(session)
            enrichments = ArticleEnrichmentRepository(session)
            stored_source_items = source_items.list_by_state(SourceItemState.INGESTED)
            outcomes: list[EnrichArticleOutcome] = []

            for source_item in stored_source_items:
                enrichment, was_created = enrichments.get_or_create(
                    ArticleEnrichment(
                        source_item_id=source_item.id,
                        source_name=_resolve_source_name(source_item),
                        article_url=source_item.source_url,
                        published_at=source_item.published_at,
                        discovered_at=source_item.created_at,
                        tags=list(extract_source_tags(source_item.raw_payload or {})),
                        rss_discovered_status=StageExecutionStatus.SUCCEEDED,
                        saved_status=StageExecutionStatus.SUCCEEDED,
                        last_stage=PipelineStage.SAVED,
                        metadata_json={"rss_summary": source_item.summary} if source_item.summary else None,
                    )
                )
                if not was_created and enrichment.summary_regenerate_status is StageExecutionStatus.SUCCEEDED:
                    outcomes.append(
                        EnrichArticleOutcome(
                            source_item_id=source_item.id,
                            status="existing",
                            article_enrichment_id=enrichment.id,
                        )
                    )
                    continue
                if _is_existing_policy_skip(enrichment):
                    outcomes.append(
                        EnrichArticleOutcome(
                            source_item_id=source_item.id,
                            status="skipped",
                            article_enrichment_id=enrichment.id,
                        )
                    )
                    continue

                if not source_item.allow_full_text_fetch:
                    _mark_policy_skip(
                        enrichment,
                        stage=PipelineStage.HTML_FETCH,
                        reason=_policy_fetch_skip_reason(source_item),
                    )
                    outcomes.append(
                        EnrichArticleOutcome(
                            source_item_id=source_item.id,
                            status="skipped",
                            article_enrichment_id=enrichment.id,
                        )
                    )
                    session.flush()
                    continue

                try:
                    fetch_result = fetcher.fetch(source_item.source_url)
                    enrichment.html_content = fetch_result.html
                    enrichment.article_url = fetch_result.final_url or fetch_result.article_url
                    enrichment.html_fetch_status = StageExecutionStatus.SUCCEEDED
                    enrichment.fetched_at = event_time
                    enrichment.last_stage = PipelineStage.HTML_FETCH

                    extract_result = extractor.extract(fetch_result.html)
                    enrichment.article_text = extract_result.article_text
                    enrichment.article_extract_status = StageExecutionStatus.SUCCEEDED
                    enrichment.extracted_at = event_time
                    enrichment.last_stage = PipelineStage.ARTICLE_EXTRACT
                    enrichment.source_name = extract_result.source_name or enrichment.source_name
                    enrichment.published_at = extract_result.published_at or enrichment.published_at
                    enrichment.metadata_json = {
                        **(enrichment.metadata_json or {}),
                        **extract_result.metadata,
                    }

                    if not source_item.allow_llm_rewrite:
                        _mark_policy_skip(
                            enrichment,
                            stage=PipelineStage.SUMMARY_REGENERATE,
                            reason=_policy_rewrite_skip_reason(source_item),
                        )
                        outcomes.append(
                            EnrichArticleOutcome(
                                source_item_id=source_item.id,
                                status="skipped",
                                article_enrichment_id=enrichment.id,
                            )
                        )
                        session.flush()
                        continue

                    summary = regenerator.regenerate(
                        title=extract_result.title or source_item.title,
                        article_text=extract_result.article_text,
                        rss_description=source_item.summary,
                    )
                    enrichment.regenerated_summary = summary.summary
                    enrichment.regenerated_key_points = list(summary.key_points)
                    enrichment.summary_regenerate_status = StageExecutionStatus.SUCCEEDED
                    enrichment.summarized_at = event_time
                    enrichment.last_stage = PipelineStage.SUMMARY_REGENERATE
                    enrichment.policy_decision_reason = None
                    enrichment.failure_stage = None
                    enrichment.failure_code = None
                    enrichment.failure_message = None
                    outcomes.append(
                        EnrichArticleOutcome(
                            source_item_id=source_item.id,
                            status="enriched",
                            article_enrichment_id=enrichment.id,
                        )
                    )
                except HtmlFetcherError as exc:
                    _mark_failure(
                        enrichment,
                        stage=PipelineStage.HTML_FETCH,
                        code=exc.code,
                        message=exc.message,
                    )
                    outcomes.append(
                        EnrichArticleOutcome(
                            source_item_id=source_item.id,
                            status="failed",
                            article_enrichment_id=enrichment.id,
                            failure_code=exc.code,
                            failure_stage=PipelineStage.HTML_FETCH,
                        )
                    )
                except ArticleExtractError as exc:
                    _mark_failure(
                        enrichment,
                        stage=PipelineStage.ARTICLE_EXTRACT,
                        code=exc.code,
                        message=exc.message,
                    )
                    outcomes.append(
                        EnrichArticleOutcome(
                            source_item_id=source_item.id,
                            status="failed",
                            article_enrichment_id=enrichment.id,
                            failure_code=exc.code,
                            failure_stage=PipelineStage.ARTICLE_EXTRACT,
                        )
                    )
                except SummaryRegenerationError as exc:
                    _mark_failure(
                        enrichment,
                        stage=PipelineStage.SUMMARY_REGENERATE,
                        code=exc.code,
                        message=exc.message,
                    )
                    outcomes.append(
                        EnrichArticleOutcome(
                            source_item_id=source_item.id,
                            status="failed",
                            article_enrichment_id=enrichment.id,
                            failure_code=exc.code,
                            failure_stage=PipelineStage.SUMMARY_REGENERATE,
                        )
                    )
                session.flush()
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return EnrichArticlesResult(
        processed_source_item_ids=tuple(item.id for item in stored_source_items),
        outcomes=tuple(outcomes),
    )


def _mark_failure(
    enrichment: ArticleEnrichment,
    *,
    stage: PipelineStage,
    code: str,
    message: str,
) -> None:
    enrichment.failure_stage = stage
    enrichment.failure_code = code
    enrichment.failure_message = message
    enrichment.last_stage = stage
    if stage is PipelineStage.HTML_FETCH:
        enrichment.html_fetch_status = StageExecutionStatus.FAILED
    elif stage is PipelineStage.ARTICLE_EXTRACT:
        enrichment.article_extract_status = StageExecutionStatus.FAILED
    elif stage is PipelineStage.SUMMARY_REGENERATE:
        enrichment.summary_regenerate_status = StageExecutionStatus.FAILED


def _mark_policy_skip(
    enrichment: ArticleEnrichment,
    *,
    stage: PipelineStage,
    reason: str,
) -> None:
    enrichment.policy_decision_reason = reason
    enrichment.failure_stage = None
    enrichment.failure_code = None
    enrichment.failure_message = None
    enrichment.last_stage = stage

    if stage is PipelineStage.HTML_FETCH:
        enrichment.fetched_at = None
        enrichment.extracted_at = None
        enrichment.summarized_at = None
        enrichment.html_content = None
        enrichment.article_text = None
        enrichment.regenerated_summary = None
        enrichment.regenerated_key_points = []
        enrichment.html_fetch_status = StageExecutionStatus.SKIPPED
        enrichment.article_extract_status = StageExecutionStatus.SKIPPED
        enrichment.summary_regenerate_status = StageExecutionStatus.SKIPPED
        return

    if stage is PipelineStage.SUMMARY_REGENERATE:
        enrichment.summarized_at = None
        enrichment.regenerated_summary = None
        enrichment.regenerated_key_points = []
        enrichment.summary_regenerate_status = StageExecutionStatus.SKIPPED
        return

    raise ValueError(f"unsupported policy skip stage: {stage.value}")


def _is_existing_policy_skip(enrichment: ArticleEnrichment) -> bool:
    return (
        enrichment.policy_decision_reason is not None
        and (
            enrichment.html_fetch_status is StageExecutionStatus.SKIPPED
            or enrichment.summary_regenerate_status is StageExecutionStatus.SKIPPED
        )
    )


def _policy_fetch_skip_reason(source_item) -> str:
    return (
        "Source policy blocks full-text fetch for this item "
        f"(mode={source_item.policy_mode.value})."
    )


def _policy_rewrite_skip_reason(source_item) -> str:
    return (
        "Source policy allows fetch but blocks rewrite for this item "
        f"(mode={source_item.policy_mode.value})."
    )


def _resolve_source_name(source_item) -> str:
    raw_payload = source_item.raw_payload or {}
    for key in ("source_name", "feed_title", "publisher", "site_name"):
        value = raw_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return source_item.source_key


def _normalize_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)
