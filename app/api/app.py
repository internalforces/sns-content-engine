"""FastAPI application wiring for operator routes."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from app.api.presenters import (
    _build_api_error_response,
    _build_article_status_response,
    _build_failure_response,
    _build_manual_publish_outcome_response,
    _build_pending_review_draft_response,
    _build_policy_skip_response,
    _build_publish_job_detail_response,
    _build_publish_job_response,
    _build_review_action_response,
    _build_review_draft_detail_response,
    _build_run_response,
    _build_scheduler_backfill_response,
    _build_scheduler_discover_response,
    _build_scheduler_publish_due_response,
)
from app.api.schemas import (
    ApproveDraftRequest,
    ArticleStatusesResponse,
    CancelManualPublishRequest,
    CompleteManualPublishRequest,
    EditDraftRequest,
    FailManualPublishRequest,
    HealthcheckCheckResponse,
    HealthcheckResponse,
    ManualPublishOutcomeResponse,
    PendingReviewDraftsResponse,
    PipelineFailuresResponse,
    PipelineRunsResponse,
    PublishJobDetailResponse,
    PublishJobsResponse,
    RejectDraftRequest,
    ReviewActionResponse,
    ReviewDraftDetailResponse,
    ScheduleDraftRequest,
    SchedulerActionContextRequest,
    SchedulerBackfillResponse,
    SchedulerDiscoverResponse,
    SchedulerPublishDueRequest,
    SchedulerPublishDueResponse,
)
from app.config import ConfigError
from app.env import load_project_env
from app.storage import DatabaseSchemaError, PublishJobState

if TYPE_CHECKING:
    from app.scheduler import (
        BackfillResult,
        PublishDueResult,
        SchedulerDiscoverResult,
    )
    from app.workflows import (
        EnrichArticlesResult,
        IngestSourcesResult,
        RunLocalPipelineResult,
    )
    from app.workflows.history_queries import (
        ArticleStatusResult,
        PipelineFailureHistoryResult,
        PipelineRunHistoryResult,
        PublishJobDetailResult,
        PublishJobListResult,
    )
    from app.workflows.review_queue import (
        ManualPublishOutcomeResult,
        PendingReviewDraftsResult,
        ReviewDraftDetailResult,
        ReviewDraftResult,
    )


def create_app(
    *,
    healthcheck_runner: Callable[..., Any] | None = None,
    pipeline_runs_lister: Callable[..., PipelineRunHistoryResult] | None = None,
    pipeline_failures_lister: Callable[..., PipelineFailureHistoryResult] | None = None,
    article_statuses_lister: Callable[..., ArticleStatusResult] | None = None,
    publish_jobs_lister: Callable[..., PublishJobListResult] | None = None,
    publish_job_detail_fetcher: Callable[..., PublishJobDetailResult] | None = None,
    scheduler_discover_runner: Callable[..., SchedulerDiscoverResult] | None = None,
    ingest_sources_runner: Callable[..., IngestSourcesResult] | None = None,
    enrich_articles_runner: Callable[..., EnrichArticlesResult] | None = None,
    run_local_pipeline_runner: Callable[..., RunLocalPipelineResult] | None = None,
    scheduler_backfill_runner: Callable[..., BackfillResult] | None = None,
    scheduler_publish_due_runner: Callable[..., PublishDueResult] | None = None,
    pending_review_drafts_lister: Callable[..., PendingReviewDraftsResult] | None = None,
    review_draft_detail_fetcher: Callable[..., ReviewDraftDetailResult] | None = None,
    draft_approver: Callable[..., ReviewDraftResult] | None = None,
    draft_rejector: Callable[..., ReviewDraftResult] | None = None,
    draft_editor: Callable[..., ReviewDraftResult] | None = None,
    draft_scheduler: Callable[..., ReviewDraftResult] | None = None,
    manual_publish_completer: Callable[..., ManualPublishOutcomeResult] | None = None,
    manual_publish_failer: Callable[..., ManualPublishOutcomeResult] | None = None,
    manual_publish_canceller: Callable[..., ManualPublishOutcomeResult] | None = None,
) -> FastAPI:
    """Create the FastAPI application for operator routes."""

    if healthcheck_runner is None:
        from app.operations import run_healthcheck as default_healthcheck_runner

        healthcheck_runner = default_healthcheck_runner
    if pipeline_runs_lister is None:
        from app.workflows.history_queries import list_pipeline_runs as default_pipeline_runs_lister

        pipeline_runs_lister = default_pipeline_runs_lister
    if pipeline_failures_lister is None:
        from app.workflows.history_queries import (
            list_pipeline_failures as default_pipeline_failures_lister,
        )

        pipeline_failures_lister = default_pipeline_failures_lister
    if article_statuses_lister is None:
        from app.workflows.history_queries import (
            list_article_statuses as default_article_statuses_lister,
        )

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
    if ingest_sources_runner is None:
        from app.workflows.ingest_sources import ingest_sources as default_ingest_sources_runner

        ingest_sources_runner = default_ingest_sources_runner
    if enrich_articles_runner is None:
        from app.workflows.enrich_articles import enrich_articles as default_enrich_articles_runner

        enrich_articles_runner = default_enrich_articles_runner
    if run_local_pipeline_runner is None:
        from app.workflows.run_local_pipeline import (
            run_local_pipeline as default_run_local_pipeline_runner,
        )

        run_local_pipeline_runner = default_run_local_pipeline_runner
    if scheduler_backfill_runner is None:
        from app.scheduler import backfill_publish_jobs as default_scheduler_backfill_runner

        scheduler_backfill_runner = default_scheduler_backfill_runner
    if scheduler_publish_due_runner is None:
        from app.scheduler import publish_due_jobs as default_scheduler_publish_due_runner

        scheduler_publish_due_runner = default_scheduler_publish_due_runner
    if pending_review_drafts_lister is None:
        from app.workflows.review_queue import (
            list_pending_review_drafts as default_pending_review_drafts_lister,
        )

        pending_review_drafts_lister = default_pending_review_drafts_lister
    if review_draft_detail_fetcher is None:
        from app.workflows.review_queue import (
            get_review_draft_detail as default_review_draft_detail_fetcher,
        )

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
    if manual_publish_completer is None:
        from app.workflows.review_queue import (
            complete_manual_publish_handoff as default_manual_publish_completer,
        )

        manual_publish_completer = default_manual_publish_completer
    if manual_publish_failer is None:
        from app.workflows.review_queue import (
            fail_manual_publish_handoff as default_manual_publish_failer,
        )

        manual_publish_failer = default_manual_publish_failer
    if manual_publish_canceller is None:
        from app.workflows.review_queue import (
            cancel_manual_publish_handoff as default_manual_publish_canceller,
        )

        manual_publish_canceller = default_manual_publish_canceller

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
        ManualPublishError,
        ManualPublishStateError,
        ReviewerIdentityError,
        ReviewQueueError,
    )

    mount_console_static(application)
    application.state.console_pipeline_runs_lister = pipeline_runs_lister
    application.state.console_pipeline_failures_lister = pipeline_failures_lister
    application.state.console_article_statuses_lister = article_statuses_lister
    application.state.console_publish_jobs_lister = publish_jobs_lister
    application.state.console_publish_job_detail_fetcher = publish_job_detail_fetcher
    application.state.console_scheduler_discover_runner = scheduler_discover_runner
    application.state.console_ingest_sources_runner = ingest_sources_runner
    application.state.console_enrich_articles_runner = enrich_articles_runner
    application.state.console_run_local_pipeline_runner = run_local_pipeline_runner
    application.state.console_scheduler_backfill_runner = scheduler_backfill_runner
    application.state.console_scheduler_publish_due_runner = scheduler_publish_due_runner
    application.state.console_pending_review_drafts_lister = pending_review_drafts_lister
    application.state.console_review_draft_detail_fetcher = review_draft_detail_fetcher
    application.state.console_draft_approver = draft_approver
    application.state.console_draft_rejector = draft_rejector
    application.state.console_draft_editor = draft_editor
    application.state.console_draft_scheduler = draft_scheduler
    application.state.console_manual_publish_completer = manual_publish_completer
    application.state.console_manual_publish_failer = manual_publish_failer
    application.state.console_manual_publish_canceller = manual_publish_canceller
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

    @application.exception_handler(ManualPublishStateError)
    async def handle_manual_publish_state_error(
        _request: Request, exc: ManualPublishStateError
    ) -> JSONResponse:
        return _build_api_error_response(
            status_code=409,
            error_code="manual_publish_state_conflict",
            message=str(exc),
        )

    @application.exception_handler(ManualPublishError)
    async def handle_manual_publish_error(
        _request: Request, exc: ManualPublishError
    ) -> JSONResponse:
        return _build_api_error_response(
            status_code=422,
            error_code="manual_publish_invalid",
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

    @application.post(
        "/publish-jobs/{publish_job_id}/manual/complete",
        response_model=ManualPublishOutcomeResponse,
        tags=["publish"],
    )
    def complete_manual_publish_job(
        publish_job_id: int,
        payload: CompleteManualPublishRequest,
        database_url: str | None = Query(default=None),
    ) -> ManualPublishOutcomeResponse:
        result = manual_publish_completer(
            publish_job_id,
            operator=payload.operator,
            external_post_id=payload.external_post_id,
            database_url=database_url,
        )
        return _build_manual_publish_outcome_response(result)

    @application.post(
        "/publish-jobs/{publish_job_id}/manual/fail",
        response_model=ManualPublishOutcomeResponse,
        tags=["publish"],
    )
    def fail_manual_publish_job(
        publish_job_id: int,
        payload: FailManualPublishRequest,
        database_url: str | None = Query(default=None),
    ) -> ManualPublishOutcomeResponse:
        result = manual_publish_failer(
            publish_job_id,
            operator=payload.operator,
            error_message=payload.error_message,
            database_url=database_url,
        )
        return _build_manual_publish_outcome_response(result)

    @application.post(
        "/publish-jobs/{publish_job_id}/manual/cancel",
        response_model=ManualPublishOutcomeResponse,
        tags=["publish"],
    )
    def cancel_manual_publish_job(
        publish_job_id: int,
        payload: CancelManualPublishRequest,
        database_url: str | None = Query(default=None),
    ) -> ManualPublishOutcomeResponse:
        result = manual_publish_canceller(
            publish_job_id,
            operator=payload.operator,
            reason=payload.reason,
            database_url=database_url,
        )
        return _build_manual_publish_outcome_response(result)

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


load_project_env()
app = create_app()
