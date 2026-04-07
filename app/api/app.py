"""FastAPI application wiring for operator routes."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.config import ConfigError
from app.storage import DatabaseSchemaError

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
    from app.workflows.review_queue import PendingReviewDraft, PendingReviewDraftsResult, ReviewDraftResult


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


class ReviewActionContextRequest(_ApiModel):
    reviewer: str | None = None
    config_dir: str = "config"


class ApproveDraftRequest(ReviewActionContextRequest):
    pass


class RejectDraftRequest(ReviewActionContextRequest):
    reason: str


class EditDraftRequest(ReviewActionContextRequest):
    body: str


class ScheduleDraftRequest(ReviewActionContextRequest):
    scheduled_for: str


class ReviewActionResponse(_ApiModel):
    draft_id: int
    reviewer: str
    action_type: str
    draft_state: str
    action_id: int
    publish_job_id: int | None = None
    scheduled_for: str | None = None


class ApiErrorResponse(_ApiModel):
    error_code: str
    message: str


def create_app(
    *,
    healthcheck_runner: Callable[..., Any] | None = None,
    pipeline_runs_lister: Callable[..., PipelineRunHistoryResult] | None = None,
    pipeline_failures_lister: Callable[..., PipelineFailureHistoryResult] | None = None,
    article_statuses_lister: Callable[..., ArticleStatusResult] | None = None,
    pending_review_drafts_lister: Callable[..., PendingReviewDraftsResult] | None = None,
    draft_approver: Callable[..., ReviewDraftResult] | None = None,
    draft_rejector: Callable[..., ReviewDraftResult] | None = None,
    draft_editor: Callable[..., ReviewDraftResult] | None = None,
    draft_scheduler: Callable[..., ReviewDraftResult] | None = None,
) -> FastAPI:
    """Create the FastAPI application for operator routes."""

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
    if draft_approver is None:
        from app.workflows.review_queue import approve_draft as default_draft_approver

        draft_approver = default_draft_approver
    if draft_rejector is None:
        from app.workflows.review_queue import reject_draft as default_draft_rejector

        draft_rejector = default_draft_rejector
    if draft_editor is None:
        from app.workflows.review_queue import edit_draft as default_draft_editor

        draft_editor = default_draft_editor
    if draft_scheduler is None:
        from app.workflows.review_queue import schedule_draft as default_draft_scheduler

        draft_scheduler = default_draft_scheduler

    application = FastAPI(
        title="sns-content-engine API",
        version="0.1.0",
    )

    from app.workflows.review_queue import (
        DraftNotFoundError,
        DraftReviewStateError,
        DraftScheduleError,
        DraftValidationFailedError,
        ReviewQueueError,
        ReviewerIdentityError,
    )

    @application.exception_handler(DatabaseSchemaError)
    async def handle_database_schema_error(
        _request: Request, exc: DatabaseSchemaError
    ) -> JSONResponse:
        return _build_api_error_response(
            status_code=503,
            error_code="database_schema_error",
            message=str(exc),
        )

    @application.exception_handler(ConfigError)
    async def handle_config_error(_request: Request, exc: ConfigError) -> JSONResponse:
        return _build_api_error_response(
            status_code=422,
            error_code="config_invalid",
            message=str(exc),
        )

    @application.exception_handler(DraftNotFoundError)
    async def handle_draft_not_found(_request: Request, exc: DraftNotFoundError) -> JSONResponse:
        return _build_api_error_response(
            status_code=404,
            error_code="draft_not_found",
            message=str(exc),
        )

    @application.exception_handler(DraftReviewStateError)
    async def handle_draft_state_conflict(
        _request: Request, exc: DraftReviewStateError
    ) -> JSONResponse:
        return _build_api_error_response(
            status_code=409,
            error_code="draft_state_conflict",
            message=str(exc),
        )

    @application.exception_handler(DraftValidationFailedError)
    async def handle_draft_validation_failed(
        _request: Request, exc: DraftValidationFailedError
    ) -> JSONResponse:
        return _build_api_error_response(
            status_code=422,
            error_code="draft_validation_failed",
            message=str(exc),
        )

    @application.exception_handler(DraftScheduleError)
    async def handle_draft_schedule_error(
        _request: Request, exc: DraftScheduleError
    ) -> JSONResponse:
        message = str(exc)
        if "already has an active publish job" in message:
            return _build_api_error_response(
                status_code=409,
                error_code="draft_schedule_conflict",
                message=message,
            )
        return _build_api_error_response(
            status_code=422,
            error_code="draft_schedule_invalid",
            message=message,
        )

    @application.exception_handler(ReviewerIdentityError)
    async def handle_reviewer_identity_error(
        _request: Request, exc: ReviewerIdentityError
    ) -> JSONResponse:
        return _build_api_error_response(
            status_code=422,
            error_code="reviewer_identity_required",
            message=str(exc),
        )

    @application.exception_handler(ReviewQueueError)
    async def handle_review_queue_error(
        _request: Request, exc: ReviewQueueError
    ) -> JSONResponse:
        return _build_api_error_response(
            status_code=422,
            error_code="review_queue_error",
            message=str(exc),
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

    @application.post("/reviews/{draft_id}/approve", response_model=ReviewActionResponse, tags=["reviews"])
    def approve_review_draft(
        draft_id: int,
        payload: ApproveDraftRequest,
        database_url: str | None = Query(default=None),
    ) -> ReviewActionResponse:
        result = draft_approver(
            draft_id,
            reviewer=payload.reviewer,
            config_dir=payload.config_dir,
            database_url=database_url,
        )
        return _build_review_action_response(result)

    @application.post("/reviews/{draft_id}/reject", response_model=ReviewActionResponse, tags=["reviews"])
    def reject_review_draft(
        draft_id: int,
        payload: RejectDraftRequest,
        database_url: str | None = Query(default=None),
    ) -> ReviewActionResponse:
        result = draft_rejector(
            draft_id,
            reason=payload.reason,
            reviewer=payload.reviewer,
            config_dir=payload.config_dir,
            database_url=database_url,
        )
        return _build_review_action_response(result)

    @application.post("/reviews/{draft_id}/edit", response_model=ReviewActionResponse, tags=["reviews"])
    def edit_review_draft(
        draft_id: int,
        payload: EditDraftRequest,
        database_url: str | None = Query(default=None),
    ) -> ReviewActionResponse:
        result = draft_editor(
            draft_id,
            body=payload.body,
            reviewer=payload.reviewer,
            config_dir=payload.config_dir,
            database_url=database_url,
        )
        return _build_review_action_response(result)

    @application.post("/reviews/{draft_id}/schedule", response_model=ReviewActionResponse, tags=["reviews"])
    def schedule_review_draft(
        draft_id: int,
        payload: ScheduleDraftRequest,
        database_url: str | None = Query(default=None),
    ) -> ReviewActionResponse:
        result = draft_scheduler(
            draft_id,
            scheduled_for=payload.scheduled_for,
            reviewer=payload.reviewer,
            config_dir=payload.config_dir,
            database_url=database_url,
        )
        return _build_review_action_response(result)

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


def _build_review_action_response(result: ReviewDraftResult) -> ReviewActionResponse:
    return ReviewActionResponse(
        draft_id=result.draft_id,
        reviewer=result.reviewer,
        action_type=result.action_type.value,
        draft_state=result.draft_state.value,
        action_id=result.action_id,
        publish_job_id=result.publish_job_id,
        scheduled_for=result.scheduled_for.isoformat() if result.scheduled_for else None,
    )


def _build_api_error_response(*, status_code: int, error_code: str, message: str) -> JSONResponse:
    payload = ApiErrorResponse(error_code=error_code, message=message)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


app = create_app()
