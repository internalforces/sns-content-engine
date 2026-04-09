"""FastAPI application wiring for operator routes."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.config import ConfigError
from app.storage import DatabaseSchemaError, PublishJobState

if TYPE_CHECKING:
    from app.scheduler import (
        BackfillChannelResult,
        BackfillResult,
        PublishDueOutcome,
        PublishDueResult,
        SchedulerDiscoverResult,
    )
    from app.storage import DraftVariant, ReviewAction
    from app.workflows.history_queries import (
        ArticleStatusResult,
        ArticleStatusRow,
        PipelineFailureHistoryResult,
        PipelineFailureRow,
        PipelinePolicySkipRow,
        PublishJobDetailResult,
        PublishJobListResult,
        PublishJobListRow,
        PipelineRunHistoryResult,
        PipelineRunHistoryRow,
    )
    from app.workflows.review_queue import PendingReviewDraft, PendingReviewDraftsResult, ReviewDraftResult
    from app.workflows.review_queue import ReviewDraftDetailResult


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


class PublishJobRowResponse(_ApiModel):
    publish_job_id: int
    draft_id: int
    brief_id: int
    account_key: str
    channel: str
    state: str
    scheduled_for: str | None
    published_at: str | None
    created_at: str
    updated_at: str
    attempt_count: int
    external_post_id: str | None
    last_error: str | None
    variant_index: int
    draft_state: str
    brief_title: str
    source_title: str


class PublishJobsResponse(_ApiModel):
    jobs: list[PublishJobRowResponse]


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


class ReviewDraftProvenanceResponse(_ApiModel):
    source_name: str | None
    source_url: str | None
    article_url: str | None
    source_published_at: str | None
    source_policy_mode: str | None


class ReviewDraftBriefResponse(_ApiModel):
    brief_id: int
    title: str
    summary: str | None
    key_points: list[str]
    landing_url: str
    tags: list[str]
    angle: str
    language: str


class ReviewDraftSourceItemResponse(_ApiModel):
    source_item_id: int
    source_key: str
    external_id: str
    title: str
    summary: str | None
    source_url: str
    canonical_url: str
    published_at: str | None
    policy_mode: str
    require_attribution: bool


class ReviewDraftArticleEnrichmentResponse(_ApiModel):
    article_enrichment_id: int
    source_name: str | None
    article_url: str
    published_at: str | None
    discovered_at: str
    regenerated_summary: str | None
    regenerated_key_points: list[str]
    classification: str | None


class ReviewDraftAuditEntryResponse(_ApiModel):
    action_id: int
    action_type: str
    reviewer: str
    created_at: str
    before_text: str
    after_text: str
    draft_state_before: str
    draft_state_after: str
    rejection_reason: str | None
    scheduled_for: str | None
    publish_job_id: int | None


class ReviewDraftSiblingVariantResponse(_ApiModel):
    draft_id: int
    variant_index: int
    body: str
    draft_state: str
    rejection_reason: str | None
    created_at: str
    reviewed_at: str | None


class ReviewDraftDetailResponse(_ApiModel):
    draft_id: int
    account_key: str
    channel: str
    variant_index: int
    body: str
    draft_state: str
    rejection_reason: str | None
    created_at: str
    reviewed_at: str | None
    provenance: ReviewDraftProvenanceResponse
    brief: ReviewDraftBriefResponse
    source_item: ReviewDraftSourceItemResponse
    article_enrichment: ReviewDraftArticleEnrichmentResponse | None
    review_actions: list[ReviewDraftAuditEntryResponse]
    sibling_variants: list[ReviewDraftSiblingVariantResponse]


class PublishJobDraftResponse(_ApiModel):
    draft_id: int
    variant_index: int
    body: str
    draft_state: str
    rejection_reason: str | None
    created_at: str
    reviewed_at: str | None


class PublishJobLogEntryResponse(_ApiModel):
    log_id: int
    event_type: str
    message: str
    payload: dict[str, Any] | None
    created_at: str


class PublishJobDetailResponse(_ApiModel):
    publish_job_id: int
    account_key: str
    channel: str
    state: str
    scheduled_for: str | None
    published_at: str | None
    created_at: str
    updated_at: str
    attempt_count: int
    external_post_id: str | None
    last_error: str | None
    draft: PublishJobDraftResponse
    provenance: ReviewDraftProvenanceResponse
    brief: ReviewDraftBriefResponse
    source_item: ReviewDraftSourceItemResponse
    publish_logs: list[PublishJobLogEntryResponse]


class SchedulerDiscoverResponse(_ApiModel):
    discovered_count: int
    processed_sources: list[str]
    failure_count: int
    failure_messages: list[str]


class SchedulerBackfillChannelResponse(_ApiModel):
    account_key: str
    channel: str
    backlog_target: int
    existing_future_job_count: int
    eligible_draft_count: int
    planned_slot_count: int
    created_job_ids: list[int]
    created_count: int
    skipped_slot_count: int


class SchedulerBackfillResponse(_ApiModel):
    processed_channel_count: int
    created_count: int
    existing_count: int
    skipped_count: int
    outcomes: list[SchedulerBackfillChannelResponse]


class SchedulerPublishDueOutcomeResponse(_ApiModel):
    publish_job_id: int
    status: str
    state: str
    message: str
    external_post_id: str | None


class SchedulerPublishDueResponse(_ApiModel):
    dry_run: bool
    processed_count: int
    published_count: int
    failed_count: int
    dry_run_count: int
    skipped_count: int
    outcomes: list[SchedulerPublishDueOutcomeResponse]


class SchedulerActionContextRequest(_ApiModel):
    config_dir: str = "config"


class SchedulerPublishDueRequest(SchedulerActionContextRequest):
    live: bool = False


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
    publish_jobs_lister: Callable[..., PublishJobListResult] | None = None,
    publish_job_detail_fetcher: Callable[..., PublishJobDetailResult] | None = None,
    scheduler_discover_runner: Callable[..., SchedulerDiscoverResult] | None = None,
    scheduler_backfill_runner: Callable[..., BackfillResult] | None = None,
    scheduler_publish_due_runner: Callable[..., PublishDueResult] | None = None,
    pending_review_drafts_lister: Callable[..., PendingReviewDraftsResult] | None = None,
    review_draft_detail_fetcher: Callable[..., ReviewDraftDetailResult] | None = None,
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
    if publish_jobs_lister is None:
        from app.workflows.history_queries import list_publish_jobs as default_publish_jobs_lister

        publish_jobs_lister = default_publish_jobs_lister
    if publish_job_detail_fetcher is None:
        from app.workflows.history_queries import (
            get_publish_job_detail as default_publish_job_detail_fetcher,
        )

        publish_job_detail_fetcher = default_publish_job_detail_fetcher
    if scheduler_discover_runner is None:
        from app.scheduler import scheduler_discover as default_scheduler_discover_runner

        scheduler_discover_runner = default_scheduler_discover_runner
    if scheduler_backfill_runner is None:
        from app.scheduler import backfill_publish_jobs as default_scheduler_backfill_runner

        scheduler_backfill_runner = default_scheduler_backfill_runner
    if scheduler_publish_due_runner is None:
        from app.scheduler import publish_due_jobs as default_scheduler_publish_due_runner

        scheduler_publish_due_runner = default_scheduler_publish_due_runner
    if pending_review_drafts_lister is None:
        from app.workflows.review_queue import list_pending_review_drafts as default_pending_review_drafts_lister

        pending_review_drafts_lister = default_pending_review_drafts_lister
    if review_draft_detail_fetcher is None:
        from app.workflows.review_queue import get_review_draft_detail as default_review_draft_detail_fetcher

        review_draft_detail_fetcher = default_review_draft_detail_fetcher
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

    from app.api.console import console_router, mount_console_static
    from app.workflows.history_queries import PublishJobNotFoundError
    from app.workflows.review_queue import (
        DraftNotFoundError,
        DraftReviewStateError,
        DraftScheduleError,
        DraftValidationFailedError,
        ReviewQueueError,
        ReviewerIdentityError,
    )

    mount_console_static(application)
    application.state.console_pipeline_runs_lister = pipeline_runs_lister
    application.state.console_pipeline_failures_lister = pipeline_failures_lister
    application.state.console_article_statuses_lister = article_statuses_lister
    application.state.console_pending_review_drafts_lister = pending_review_drafts_lister
    application.include_router(console_router)

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

    @application.exception_handler(PublishJobNotFoundError)
    async def handle_publish_job_not_found(
        _request: Request, exc: PublishJobNotFoundError
    ) -> JSONResponse:
        return _build_api_error_response(
            status_code=404,
            error_code="publish_job_not_found",
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

    @application.get("/publish-jobs", response_model=PublishJobsResponse, tags=["publish"])
    def get_publish_jobs(
        database_url: str | None = Query(default=None),
        state: PublishJobState | None = Query(default=None),
        account_key: str | None = Query(default=None),
        channel: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> PublishJobsResponse:
        result = publish_jobs_lister(
            database_url=database_url,
            state=state,
            account_key=account_key,
            channel=channel,
            limit=limit,
        )
        return PublishJobsResponse(
            jobs=[_build_publish_job_response(row) for row in result.jobs],
        )

    @application.get("/publish-jobs/{publish_job_id}", response_model=PublishJobDetailResponse, tags=["publish"])
    def get_publish_job_detail(
        publish_job_id: int,
        database_url: str | None = Query(default=None),
    ) -> PublishJobDetailResponse:
        detail = publish_job_detail_fetcher(
            publish_job_id,
            database_url=database_url,
        )
        return _build_publish_job_detail_response(detail)

    @application.post("/scheduler/discover", response_model=SchedulerDiscoverResponse, tags=["scheduler"])
    def run_scheduler_discover(
        payload: SchedulerActionContextRequest,
    ) -> SchedulerDiscoverResponse:
        result = scheduler_discover_runner(config_dir=payload.config_dir)
        return _build_scheduler_discover_response(result)

    @application.post("/scheduler/backfill", response_model=SchedulerBackfillResponse, tags=["scheduler"])
    def run_scheduler_backfill(
        payload: SchedulerActionContextRequest,
        database_url: str | None = Query(default=None),
    ) -> SchedulerBackfillResponse:
        result = scheduler_backfill_runner(
            config_dir=payload.config_dir,
            database_url=database_url,
        )
        return _build_scheduler_backfill_response(result)

    @application.post("/scheduler/publish-due", response_model=SchedulerPublishDueResponse, tags=["scheduler"])
    def run_scheduler_publish_due(
        payload: SchedulerPublishDueRequest,
        database_url: str | None = Query(default=None),
    ) -> SchedulerPublishDueResponse:
        result = scheduler_publish_due_runner(
            config_dir=payload.config_dir,
            database_url=database_url,
            dry_run=not payload.live,
        )
        return _build_scheduler_publish_due_response(result)

    @application.get("/reviews/pending", response_model=PendingReviewDraftsResponse, tags=["reviews"])
    def get_pending_review_drafts(
        database_url: str | None = Query(default=None),
    ) -> PendingReviewDraftsResponse:
        result = pending_review_drafts_lister(database_url=database_url)
        return PendingReviewDraftsResponse(
            pending_count=result.pending_count,
            drafts=[_build_pending_review_draft_response(row) for row in result.drafts],
        )

    @application.get("/reviews/{draft_id}", response_model=ReviewDraftDetailResponse, tags=["reviews"])
    def get_review_draft_detail(
        draft_id: int,
        database_url: str | None = Query(default=None),
    ) -> ReviewDraftDetailResponse:
        detail = review_draft_detail_fetcher(draft_id, database_url=database_url)
        return _build_review_draft_detail_response(detail)

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


def _build_publish_job_response(row: PublishJobListRow) -> PublishJobRowResponse:
    return PublishJobRowResponse(
        publish_job_id=row.publish_job_id,
        draft_id=row.draft_id,
        brief_id=row.brief_id,
        account_key=row.account_key,
        channel=row.channel,
        state=row.state,
        scheduled_for=row.scheduled_for.isoformat() if row.scheduled_for else None,
        published_at=row.published_at.isoformat() if row.published_at else None,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        attempt_count=row.attempt_count,
        external_post_id=row.external_post_id,
        last_error=row.last_error,
        variant_index=row.variant_index,
        draft_state=row.draft_state,
        brief_title=row.brief_title,
        source_title=row.source_title,
    )


def _build_publish_job_detail_response(detail: PublishJobDetailResult) -> PublishJobDetailResponse:
    job = detail.job
    draft = job.draft_variant
    content_brief = draft.content_brief
    source_item = content_brief.source_item
    return PublishJobDetailResponse(
        publish_job_id=job.id,
        account_key=content_brief.account_key,
        channel=job.channel,
        state=job.state.value,
        scheduled_for=job.scheduled_for.isoformat() if job.scheduled_for else None,
        published_at=job.published_at.isoformat() if job.published_at else None,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        attempt_count=job.attempt_count,
        external_post_id=job.external_post_id,
        last_error=job.last_error,
        draft=PublishJobDraftResponse(
            draft_id=draft.id,
            variant_index=draft.variant_index,
            body=draft.body,
            draft_state=draft.state.value,
            rejection_reason=draft.rejection_reason,
            created_at=draft.created_at.isoformat(),
            reviewed_at=draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        ),
        provenance=ReviewDraftProvenanceResponse(
            source_name=draft.source_name,
            source_url=draft.source_url,
            article_url=draft.article_url,
            source_published_at=draft.source_published_at.isoformat()
            if draft.source_published_at
            else None,
            source_policy_mode=draft.source_policy_mode.value if draft.source_policy_mode else None,
        ),
        brief=ReviewDraftBriefResponse(
            brief_id=content_brief.id,
            title=content_brief.title,
            summary=content_brief.summary,
            key_points=list(content_brief.key_points),
            landing_url=content_brief.landing_url,
            tags=list(content_brief.tags),
            angle=content_brief.angle,
            language=content_brief.language,
        ),
        source_item=ReviewDraftSourceItemResponse(
            source_item_id=source_item.id,
            source_key=source_item.source_key,
            external_id=source_item.external_id,
            title=source_item.title,
            summary=source_item.summary,
            source_url=source_item.source_url,
            canonical_url=source_item.canonical_url,
            published_at=source_item.published_at.isoformat() if source_item.published_at else None,
            policy_mode=source_item.policy_mode.value,
            require_attribution=source_item.require_attribution,
        ),
        publish_logs=[_build_publish_job_log_entry_response(log) for log in detail.publish_logs],
    )


def _build_publish_job_log_entry_response(log) -> PublishJobLogEntryResponse:
    return PublishJobLogEntryResponse(
        log_id=log.id,
        event_type=log.event_type,
        message=log.message,
        payload=log.payload,
        created_at=log.created_at.isoformat(),
    )


def _build_scheduler_discover_response(result: SchedulerDiscoverResult) -> SchedulerDiscoverResponse:
    return SchedulerDiscoverResponse(
        discovered_count=result.discovered_count,
        processed_sources=list(result.processed_sources),
        failure_count=result.failure_count,
        failure_messages=list(result.failure_messages),
    )


def _build_scheduler_backfill_response(result: BackfillResult) -> SchedulerBackfillResponse:
    return SchedulerBackfillResponse(
        processed_channel_count=result.processed_channel_count,
        created_count=result.created_count,
        existing_count=result.existing_count,
        skipped_count=result.skipped_count,
        outcomes=[_build_scheduler_backfill_channel_response(outcome) for outcome in result.outcomes],
    )


def _build_scheduler_backfill_channel_response(
    outcome: BackfillChannelResult,
) -> SchedulerBackfillChannelResponse:
    return SchedulerBackfillChannelResponse(
        account_key=outcome.account_key,
        channel=outcome.channel,
        backlog_target=outcome.backlog_target,
        existing_future_job_count=outcome.existing_future_job_count,
        eligible_draft_count=outcome.eligible_draft_count,
        planned_slot_count=outcome.planned_slot_count,
        created_job_ids=list(outcome.created_job_ids),
        created_count=outcome.created_count,
        skipped_slot_count=outcome.skipped_slot_count,
    )


def _build_scheduler_publish_due_response(result: PublishDueResult) -> SchedulerPublishDueResponse:
    return SchedulerPublishDueResponse(
        dry_run=result.dry_run,
        processed_count=result.processed_count,
        published_count=result.published_count,
        failed_count=result.failed_count,
        dry_run_count=result.dry_run_count,
        skipped_count=result.skipped_count,
        outcomes=[_build_scheduler_publish_due_outcome_response(outcome) for outcome in result.outcomes],
    )


def _build_scheduler_publish_due_outcome_response(
    outcome: PublishDueOutcome,
) -> SchedulerPublishDueOutcomeResponse:
    return SchedulerPublishDueOutcomeResponse(
        publish_job_id=outcome.publish_job_id,
        status=outcome.status,
        state=outcome.state.value,
        message=outcome.message,
        external_post_id=outcome.external_post_id,
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


def _build_review_draft_detail_response(detail) -> ReviewDraftDetailResponse:
    draft = detail.draft
    content_brief = draft.content_brief
    source_item = content_brief.source_item
    article_enrichment = source_item.article_enrichment
    return ReviewDraftDetailResponse(
        draft_id=draft.id,
        account_key=content_brief.account_key,
        channel=draft.channel,
        variant_index=draft.variant_index,
        body=draft.body,
        draft_state=draft.state.value,
        rejection_reason=draft.rejection_reason,
        created_at=draft.created_at.isoformat(),
        reviewed_at=draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        provenance=ReviewDraftProvenanceResponse(
            source_name=draft.source_name,
            source_url=draft.source_url,
            article_url=draft.article_url,
            source_published_at=draft.source_published_at.isoformat()
            if draft.source_published_at
            else None,
            source_policy_mode=draft.source_policy_mode.value if draft.source_policy_mode else None,
        ),
        brief=ReviewDraftBriefResponse(
            brief_id=content_brief.id,
            title=content_brief.title,
            summary=content_brief.summary,
            key_points=list(content_brief.key_points),
            landing_url=content_brief.landing_url,
            tags=list(content_brief.tags),
            angle=content_brief.angle,
            language=content_brief.language,
        ),
        source_item=ReviewDraftSourceItemResponse(
            source_item_id=source_item.id,
            source_key=source_item.source_key,
            external_id=source_item.external_id,
            title=source_item.title,
            summary=source_item.summary,
            source_url=source_item.source_url,
            canonical_url=source_item.canonical_url,
            published_at=source_item.published_at.isoformat() if source_item.published_at else None,
            policy_mode=source_item.policy_mode.value,
            require_attribution=source_item.require_attribution,
        ),
        article_enrichment=_build_review_draft_article_enrichment_response(article_enrichment)
        if article_enrichment
        else None,
        review_actions=[_build_review_draft_audit_entry_response(action) for action in detail.review_actions],
        sibling_variants=[
            _build_review_draft_sibling_variant_response(variant) for variant in detail.sibling_variants
        ],
    )


def _build_review_draft_article_enrichment_response(
    article_enrichment,
) -> ReviewDraftArticleEnrichmentResponse:
    return ReviewDraftArticleEnrichmentResponse(
        article_enrichment_id=article_enrichment.id,
        source_name=article_enrichment.source_name,
        article_url=article_enrichment.article_url,
        published_at=article_enrichment.published_at.isoformat()
        if article_enrichment.published_at
        else None,
        discovered_at=article_enrichment.discovered_at.isoformat(),
        regenerated_summary=article_enrichment.regenerated_summary,
        regenerated_key_points=list(article_enrichment.regenerated_key_points),
        classification=article_enrichment.classification,
    )


def _build_review_draft_audit_entry_response(action: ReviewAction) -> ReviewDraftAuditEntryResponse:
    return ReviewDraftAuditEntryResponse(
        action_id=action.id,
        action_type=action.action_type.value,
        reviewer=action.reviewer,
        created_at=action.created_at.isoformat(),
        before_text=action.before_text,
        after_text=action.after_text,
        draft_state_before=action.draft_state_before.value,
        draft_state_after=action.draft_state_after.value,
        rejection_reason=action.rejection_reason,
        scheduled_for=action.scheduled_for.isoformat() if action.scheduled_for else None,
        publish_job_id=action.publish_job_id,
    )


def _build_review_draft_sibling_variant_response(draft: DraftVariant) -> ReviewDraftSiblingVariantResponse:
    return ReviewDraftSiblingVariantResponse(
        draft_id=draft.id,
        variant_index=draft.variant_index,
        body=draft.body,
        draft_state=draft.state.value,
        rejection_reason=draft.rejection_reason,
        created_at=draft.created_at.isoformat(),
        reviewed_at=draft.reviewed_at.isoformat() if draft.reviewed_at else None,
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
