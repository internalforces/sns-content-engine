"""FastAPI application wiring for operational read-only routes."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.workflows.history_queries import (
        ArticleStatusResult,
        ArticleStatusRow,
        PipelineFailureHistoryResult,
        PipelineFailureRow,
        PipelinePolicySkipRow,
        PipelineRunHistoryResult,
        PipelineRunHistoryRow,
    )
    from app.workflows.review_queue import PendingReviewDraft, PendingReviewDraftsResult


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthcheckCheckResponse(_ApiModel):
    name: str
    status: str
    message: str


class HealthcheckResponse(_ApiModel):
    status: str
    failed_check_count: int
    checks: list[HealthcheckCheckResponse]


class PipelineRunResponse(_ApiModel):
    run_id: int
    workflow_name: str
    status: str
    trigger_mode: str
    started_at: str
    completed_at: str | None
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
    rewrite_providers: list[str]


class PipelineRunsResponse(_ApiModel):
    runs: list[PipelineRunResponse]


class PipelineFailureResponse(_ApiModel):
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
    updated_at: str


class PipelinePolicySkipResponse(_ApiModel):
    source_item_id: int
    article_enrichment_id: int
    title: str
    source_name: str | None
    article_url: str
    source_policy_mode: str
    require_attribution: bool
    skipped_stage: str
    policy_decision_reason: str
    updated_at: str


class PipelineFailuresResponse(_ApiModel):
    failures: list[PipelineFailureResponse]
    policy_skips: list[PipelinePolicySkipResponse]


class ArticleStatusResponse(_ApiModel):
    source_item_id: int
    article_enrichment_id: int | None
    source_name: str
    title: str
    original_url: str
    article_url: str | None
    published_at: str | None
    discovered_at: str
    enrichment_state: str
    fetch_status: str
    extract_status: str
    summarize_status: str
    last_failure_message: str | None


class ArticleStatusesResponse(_ApiModel):
    articles: list[ArticleStatusResponse]


class PendingReviewDraftResponse(_ApiModel):
    draft_id: int
    account_key: str
    channel: str
    variant_index: int
    created_at: str
    title: str
    body: str


class PendingReviewDraftsResponse(_ApiModel):
    pending_count: int
    drafts: list[PendingReviewDraftResponse]


def create_app(
    *,
    healthcheck_runner: Callable[..., Any] | None = None,
    pipeline_runs_lister: Callable[..., PipelineRunHistoryResult] | None = None,
    pipeline_failures_lister: Callable[..., PipelineFailureHistoryResult] | None = None,
    article_statuses_lister: Callable[..., ArticleStatusResult] | None = None,
    pending_review_drafts_lister: Callable[..., PendingReviewDraftsResult] | None = None,
) -> FastAPI:
    """Create the FastAPI application for read-only operator routes."""

    if healthcheck_runner is None:
        from app.operations import run_healthcheck as default_healthcheck_runner

        healthcheck_runner = default_healthcheck_runner
    if pipeline_runs_lister is None:
        from app.workflows.history_queries import list_pipeline_runs as default_pipeline_runs_lister

        pipeline_runs_lister = default_pipeline_runs_lister
    if pipeline_failures_lister is None:
        from app.workflows.history_queries import list_pipeline_failures as default_pipeline_failures_lister

        pipeline_failures_lister = default_pipeline_failures_lister
    if article_statuses_lister is None:
        from app.workflows.history_queries import list_article_statuses as default_article_statuses_lister

        article_statuses_lister = default_article_statuses_lister
    if pending_review_drafts_lister is None:
        from app.workflows.review_queue import list_pending_review_drafts as default_pending_review_drafts_lister

        pending_review_drafts_lister = default_pending_review_drafts_lister

    application = FastAPI(
        title="sns-content-engine API",
        version="0.1.0",
    )

    @application.get("/health", response_model=HealthcheckResponse, tags=["operations"])
    def get_health(
        config_dir: str = Query(default="config"),
        database_url: str | None = Query(default=None),
    ) -> HealthcheckResponse:
        result = healthcheck_runner(
            config_dir=Path(config_dir),
            database_url=database_url,
        )
        return HealthcheckResponse(
            status=result.status,
            failed_check_count=result.failed_check_count,
            checks=[HealthcheckCheckResponse(**asdict(check)) for check in result.checks],
        )

    @application.get("/runs", response_model=PipelineRunsResponse, tags=["history"])
    def get_runs(
        database_url: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
    ) -> PipelineRunsResponse:
        result = pipeline_runs_lister(database_url=database_url, limit=limit)
        return PipelineRunsResponse(
            runs=[_build_run_response(row) for row in result.runs],
        )

    @application.get("/failures", response_model=PipelineFailuresResponse, tags=["history"])
    def get_failures(
        database_url: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> PipelineFailuresResponse:
        result = pipeline_failures_lister(database_url=database_url, limit=limit)
        return PipelineFailuresResponse(
            failures=[_build_failure_response(row) for row in result.failures],
            policy_skips=[_build_policy_skip_response(row) for row in result.policy_skips],
        )

    @application.get("/articles", response_model=ArticleStatusesResponse, tags=["articles"])
    def get_articles(
        database_url: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> ArticleStatusesResponse:
        result = article_statuses_lister(database_url=database_url, limit=limit)
        return ArticleStatusesResponse(
            articles=[_build_article_status_response(row) for row in result.articles],
        )

    @application.get("/reviews/pending", response_model=PendingReviewDraftsResponse, tags=["reviews"])
    def get_pending_review_drafts(
        database_url: str | None = Query(default=None),
    ) -> PendingReviewDraftsResponse:
        result = pending_review_drafts_lister(database_url=database_url)
        return PendingReviewDraftsResponse(
            pending_count=result.pending_count,
            drafts=[_build_pending_review_draft_response(row) for row in result.drafts],
        )

    return application


def _build_run_response(row: PipelineRunHistoryRow) -> PipelineRunResponse:
    return PipelineRunResponse(
        run_id=row.run_id,
        workflow_name=row.workflow_name,
        status=row.status,
        trigger_mode=row.trigger_mode,
        started_at=row.started_at.isoformat(),
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        discovered_count=row.discovered_count,
        saved_count=row.saved_count,
        enriched_count=row.enriched_count,
        brief_count=row.brief_count,
        draft_count=row.draft_count,
        failure_count=row.failure_count,
        latest_error_code=row.latest_error_code,
        policy_mode_counts=dict(row.policy_mode_counts),
        policy_skipped_count=row.policy_skipped_count,
        attribution_required_count=row.attribution_required_count,
        rewrite_providers=list(row.rewrite_providers),
    )


def _build_failure_response(row: PipelineFailureRow) -> PipelineFailureResponse:
    return PipelineFailureResponse(
        source_item_id=row.source_item_id,
        article_enrichment_id=row.article_enrichment_id,
        title=row.title,
        source_name=row.source_name,
        article_url=row.article_url,
        source_policy_mode=row.source_policy_mode,
        require_attribution=row.require_attribution,
        failure_stage=row.failure_stage,
        failure_code=row.failure_code,
        failure_message=row.failure_message,
        updated_at=row.updated_at.isoformat(),
    )


def _build_policy_skip_response(row: PipelinePolicySkipRow) -> PipelinePolicySkipResponse:
    return PipelinePolicySkipResponse(
        source_item_id=row.source_item_id,
        article_enrichment_id=row.article_enrichment_id,
        title=row.title,
        source_name=row.source_name,
        article_url=row.article_url,
        source_policy_mode=row.source_policy_mode,
        require_attribution=row.require_attribution,
        skipped_stage=row.skipped_stage,
        policy_decision_reason=row.policy_decision_reason,
        updated_at=row.updated_at.isoformat(),
    )


def _build_article_status_response(row: ArticleStatusRow) -> ArticleStatusResponse:
    return ArticleStatusResponse(
        source_item_id=row.source_item_id,
        article_enrichment_id=row.article_enrichment_id,
        source_name=row.source_name,
        title=row.title,
        original_url=row.original_url,
        article_url=row.article_url,
        published_at=row.published_at.isoformat() if row.published_at else None,
        discovered_at=row.discovered_at.isoformat(),
        enrichment_state=row.enrichment_state,
        fetch_status=row.fetch_status,
        extract_status=row.extract_status,
        summarize_status=row.summarize_status,
        last_failure_message=row.last_failure_message,
    )


def _build_pending_review_draft_response(row: PendingReviewDraft) -> PendingReviewDraftResponse:
    return PendingReviewDraftResponse(
        draft_id=row.draft_id,
        account_key=row.account_key,
        channel=row.channel,
        variant_index=row.variant_index,
        created_at=row.created_at.isoformat(),
        title=row.title,
        body=row.body,
    )


app = create_app()
