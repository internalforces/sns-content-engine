"""Server-rendered operator console routes and assets."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.console_constants import (
    _DEFAULT_ARTICLE_LIMIT,
    _DEFAULT_DASHBOARD_FAILURE_LIMIT,
    _DEFAULT_DASHBOARD_RUN_LIMIT,
    _DEFAULT_PUBLISH_JOB_LIMIT,
    _SCHEDULER_LIVE_VALUES,
)
from app.api.console_views import (
    _append_query_params,
    _build_article_metrics,
    _build_article_row,
    _build_console_context,
    _build_dashboard_failure_row,
    _build_dashboard_latest_run,
    _build_dashboard_metrics,
    _build_dashboard_policy_skip_row,
    _build_dashboard_run_row,
    _build_manual_publish_action_form_state,
    _build_pending_review_metrics,
    _build_pending_review_row,
    _build_publish_job_detail,
    _build_publish_job_filters,
    _build_publish_job_metrics,
    _build_publish_job_query_params,
    _build_publish_job_row,
    _build_review_action_form_state,
    _build_review_detail,
    _build_scheduler_action_result,
    _extract_console_query_params,
    _format_datetime,
    _humanize_label,
)
from app.config import ConfigError
from app.connectors.llm import DraftGenerationProviderError
from app.storage import DatabaseSchemaError, PublishJobState
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

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
_STATIC_DIR = Path(__file__).resolve().parent / "static"

console_router = APIRouter(include_in_schema=False)


def mount_console_static(application: FastAPI) -> None:
    """Mount console static assets onto the shared FastAPI app."""

    application.mount(
        "/console/static",
        StaticFiles(directory=str(_STATIC_DIR)),
        name="console_static",
    )


@console_router.get("/console", response_class=RedirectResponse)
def redirect_console_root(request: Request) -> RedirectResponse:
    """Redirect the non-slash console root to the canonical landing page."""

    url = _append_query_params(
        str(request.url_for("console_home")),
        _extract_console_query_params(request),
    )
    return RedirectResponse(url=url, status_code=307)


@console_router.get("/console/", response_class=HTMLResponse, name="console_home")
def get_console_home(
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
) -> HTMLResponse:
    """Render the initial operator console shell."""

    context = _build_console_context(
        request,
        page_title="운영 콘솔",
        page_description="실행 현황, 검토 작업, 안전한 운영자 액션을 서버 렌더링 방식으로 제공하는 브라우저 콘솔입니다.",
        active_nav_key="home",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "console_sections": [
                {
                    "title": "읽기 전용 첫 배포",
                    "copy": "초기 콘솔 셸은 브라우저 레이어를 추가 전용으로 유지하면서, 실행 이력과 실패, 아티클, 검토 대기열을 같은 레이아웃에 점진적으로 연결합니다.",
                },
                {
                    "title": "안전 기본값",
                    "copy": "수동 검토는 계속 필수이며 발행 예정 처리는 기본적으로 드라이런으로 실행됩니다. 이 콘솔은 가시성을 높일 뿐 기존 워크플로 보호 장치를 우회하지 않습니다.",
                },
                {
                    "title": "구현 구조",
                    "copy": "FastAPI가 Jinja 템플릿과 가벼운 정적 자산을 직접 제공하므로, 별도 프런트엔드 빌드 체인 없이 기존 백엔드를 그대로 재사용할 수 있습니다.",
                },
            ],
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/index.html",
        context=context,
    )


@console_router.get("/console/dashboard", response_class=HTMLResponse, name="console_dashboard")
def get_console_dashboard(
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
) -> HTMLResponse:
    """Render a read-only dashboard of recent runs, failures, and policy skips."""

    runs_result = request.app.state.console_pipeline_runs_lister(
        database_url=database_url,
        limit=_DEFAULT_DASHBOARD_RUN_LIMIT,
    )
    failures_result = request.app.state.console_pipeline_failures_lister(
        database_url=database_url,
        limit=_DEFAULT_DASHBOARD_FAILURE_LIMIT,
    )
    latest_run = runs_result.runs[0] if runs_result.runs else None

    context = _build_console_context(
        request,
        page_title="실행 대시보드",
        page_description="공용 운영 이력 헬퍼를 바탕으로 최근 파이프라인 실행, 기술 실패, 정책상 의도된 건너뜀을 확인합니다.",
        active_nav_key="dashboard",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "dashboard_metrics": _build_dashboard_metrics(runs_result, failures_result),
            "dashboard_latest_run": _build_dashboard_latest_run(latest_run),
            "dashboard_runs": [_build_dashboard_run_row(row) for row in runs_result.runs],
            "dashboard_failures": [_build_dashboard_failure_row(row) for row in failures_result.failures],
            "dashboard_policy_skips": [
                _build_dashboard_policy_skip_row(row) for row in failures_result.policy_skips
            ],
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/dashboard.html",
        context=context,
    )


@console_router.get("/console/articles", response_class=HTMLResponse, name="console_articles")
def get_console_articles(
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_ARTICLE_LIMIT, ge=1, le=100),
) -> HTMLResponse:
    """Render recent article status rows in a browser-friendly table."""

    result = request.app.state.console_article_statuses_lister(
        database_url=database_url,
        limit=limit,
    )
    context = _build_console_context(
        request,
        page_title="아티클 상태",
        page_description="운영자 아티클 API와 같은 헬퍼를 사용해 최근 저장된 소스 항목과 보강 상태를 보여줍니다.",
        active_nav_key="articles",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "article_limit": limit,
            "article_metrics": _build_article_metrics(result.articles),
            "article_rows": [_build_article_row(row) for row in result.articles],
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/articles.html",
        context=context,
    )


@console_router.get(
    "/console/publish-jobs",
    response_class=HTMLResponse,
    name="console_publish_jobs",
)
def get_console_publish_jobs(
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
    state: PublishJobState | None = Query(default=None),
    account_key: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_PUBLISH_JOB_LIMIT, ge=1, le=100),
) -> HTMLResponse:
    """Render recent publish jobs and their linked draft context in the console."""

    publish_job_query_params = _build_publish_job_query_params(
        request,
        state=state,
        account_key=account_key,
        channel=channel,
        limit=limit,
    )
    result = request.app.state.console_publish_jobs_lister(
        database_url=database_url,
        state=state,
        account_key=account_key,
        channel=channel,
        limit=limit,
    )
    context = _build_console_context(
        request,
        page_title="발행 작업",
        page_description="공용 운영 이력 헬퍼를 바탕으로 발행 대기열과 수동 전달 상태를 확인하고, 필요한 경우 개별 작업에서 결과를 기록할 수 있습니다.",
        active_nav_key="publish_jobs",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "publish_job_filters": _build_publish_job_filters(
                state=state,
                account_key=account_key,
                channel=channel,
                limit=limit,
            ),
            "publish_job_metrics": _build_publish_job_metrics(result.jobs),
            "publish_job_rows": [
                _build_publish_job_row(
                    request,
                    publish_job_query_params,
                    row,
                )
                for row in result.jobs
            ],
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/publish_jobs.html",
        context=context,
    )


@console_router.get(
    "/console/publish-jobs/{publish_job_id}",
    response_class=HTMLResponse,
    name="console_publish_job_detail",
)
def get_console_publish_job_detail(
    publish_job_id: int,
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
    state: PublishJobState | None = Query(default=None),
    account_key: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_PUBLISH_JOB_LIMIT, ge=1, le=100),
) -> HTMLResponse:
    """Render one publish job with linked draft context, logs, and manual handoff actions."""

    return _render_console_publish_job_detail_page(
        request,
        publish_job_id=publish_job_id,
        config_dir=config_dir,
        database_url=database_url,
        state=state,
        account_key=account_key,
        channel=channel,
        limit=limit,
    )


@console_router.post(
    "/console/publish-jobs/{publish_job_id}",
    response_class=HTMLResponse,
    name="console_publish_job_detail_action",
)
async def post_console_publish_job_detail_action(
    publish_job_id: int,
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
    state: PublishJobState | None = Query(default=None),
    account_key: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_PUBLISH_JOB_LIMIT, ge=1, le=100),
) -> HTMLResponse:
    """Handle manual publish outcome actions from the publish-job detail page."""

    form_data = await _parse_console_form_body(request)
    action = (form_data.get("action") or "").strip().lower()
    submitted_values = _normalize_manual_publish_action_form_data(form_data)

    if action not in {"complete", "fail", "cancel"}:
        return _render_console_publish_job_detail_page(
            request,
            publish_job_id=publish_job_id,
            config_dir=config_dir,
            database_url=database_url,
            state=state,
            account_key=account_key,
            channel=channel,
            limit=limit,
            status_code=422,
            feedback=_build_manual_publish_action_feedback(
                kind="error",
                action_label="수동 발행 기록",
                message="폼을 제출하기 전에 지원되는 수동 발행 작업을 선택하세요.",
            ),
            form_values=submitted_values,
        )

    try:
        result = _execute_console_manual_publish_action(
            request,
            publish_job_id=publish_job_id,
            action=action,
            submitted_values=submitted_values,
            database_url=database_url,
        )
    except PublishJobNotFoundError:
        return _render_console_publish_job_detail_page(
            request,
            publish_job_id=publish_job_id,
            config_dir=config_dir,
            database_url=database_url,
            state=state,
            account_key=account_key,
            channel=channel,
            limit=limit,
            status_code=404,
            form_values=submitted_values,
        )
    except ManualPublishStateError as exc:
        return _render_console_publish_job_detail_page(
            request,
            publish_job_id=publish_job_id,
            config_dir=config_dir,
            database_url=database_url,
            state=state,
            account_key=account_key,
            channel=channel,
            limit=limit,
            status_code=409,
            feedback=_build_manual_publish_action_feedback(
                kind="error",
                action_label=_manual_publish_action_label(action),
                message=str(exc),
            ),
            form_values=submitted_values,
        )
    except (ManualPublishError, ReviewerIdentityError) as exc:
        return _render_console_publish_job_detail_page(
            request,
            publish_job_id=publish_job_id,
            config_dir=config_dir,
            database_url=database_url,
            state=state,
            account_key=account_key,
            channel=channel,
            limit=limit,
            status_code=422,
            feedback=_build_manual_publish_action_feedback(
                kind="error",
                action_label=_manual_publish_action_label(action),
                message=str(exc),
            ),
            form_values=submitted_values,
        )

    return _render_console_publish_job_detail_page(
        request,
        publish_job_id=publish_job_id,
        config_dir=config_dir,
        database_url=database_url,
        state=state,
        account_key=account_key,
        channel=channel,
        limit=limit,
        feedback=_build_manual_publish_success_feedback(action, result),
    )


def _render_console_publish_job_detail_page(
    request: Request,
    *,
    publish_job_id: int,
    config_dir: str,
    database_url: str | None,
    state: PublishJobState | None,
    account_key: str | None,
    channel: str | None,
    limit: int,
    status_code: int = 200,
    feedback: dict[str, str] | None = None,
    form_values: dict[str, str] | None = None,
) -> HTMLResponse:
    """Render the shared publish-job detail page for both GET and POST flows."""

    publish_job_query_params = _build_publish_job_query_params(
        request,
        state=state,
        account_key=account_key,
        channel=channel,
        limit=limit,
    )
    publish_jobs_href = _append_query_params(
        str(request.url_for("console_publish_jobs")),
        publish_job_query_params,
    )

    try:
        detail = request.app.state.console_publish_job_detail_fetcher(
            publish_job_id,
            database_url=database_url,
        )
    except PublishJobNotFoundError as exc:
        context = _build_console_context(
            request,
            page_title="발행 작업을 찾을 수 없음",
            page_description="현재 운영 콘텍스트에서는 요청한 발행 작업 상세를 불러올 수 없습니다.",
            active_nav_key="publish_jobs",
            config_dir=config_dir,
            database_url=database_url,
        )
        context.update(
            {
                "publish_jobs_href": publish_jobs_href,
                "publish_job_detail": None,
                "publish_job_detail_missing": {
                    "message": str(exc),
                    "publish_job_id": publish_job_id,
                },
                "publish_job_action_feedback": feedback,
                "publish_job_action_forms": None,
            }
        )
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="console/publish_job_detail.html",
            context=context,
            status_code=404,
        )

    context = _build_console_context(
        request,
        page_title=f"발행 작업 {publish_job_id}",
        page_description="API와 같은 운영 이력 헬퍼를 사용해 발행 타임라인, 연결된 초안 콘텍스트, 수동 전달 결과 기록 작업을 함께 보여줍니다.",
        active_nav_key="publish_jobs",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "publish_jobs_href": publish_jobs_href,
            "publish_job_detail": _build_publish_job_detail(
                request,
                detail,
            ),
            "publish_job_detail_missing": None,
            "publish_job_action_feedback": feedback,
            "publish_job_action_forms": _build_manual_publish_action_form_state(
                request,
                publish_job_query_params,
                detail,
                form_values=form_values,
            ),
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/publish_job_detail.html",
        context=context,
        status_code=status_code,
    )


@console_router.get(
    "/console/scheduler",
    response_class=HTMLResponse,
    name="console_scheduler",
)
def get_console_scheduler(
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
) -> HTMLResponse:
    """Render scheduler actions with dry-run-first browser controls."""

    return _render_console_scheduler_page(
        request,
        config_dir=config_dir,
        database_url=database_url,
    )


@console_router.post(
    "/console/scheduler",
    response_class=HTMLResponse,
    name="console_scheduler_action",
)
async def post_console_scheduler_action(
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
) -> HTMLResponse:
    """Execute one scheduler action and re-render the browser summary."""

    form_data = await _parse_console_form_body(request)
    action = (form_data.get("action") or "").strip().lower()

    if action not in {"discover", "ingest", "enrich", "run_local", "backfill", "publish_due"}:
        return _render_console_scheduler_page(
            request,
            config_dir=config_dir,
            database_url=database_url,
            status_code=422,
            feedback=_build_scheduler_action_feedback(
                kind="error",
                action_label="운영 작업",
                message="폼을 제출하기 전에 지원되는 운영 작업을 선택하세요.",
            ),
        )

    live_requested = _is_live_publish_requested(form_data)
    try:
        result = _execute_console_scheduler_action(
            request,
            action=action,
            config_dir=config_dir,
            database_url=database_url,
            live_requested=live_requested,
        )
    except ConfigError as exc:
        return _render_console_scheduler_page(
            request,
            config_dir=config_dir,
            database_url=database_url,
            status_code=422,
            feedback=_build_scheduler_action_feedback(
                kind="error",
                action_label=_humanize_label(action),
                message=str(exc),
            ),
        )
    except DatabaseSchemaError as exc:
        return _render_console_scheduler_page(
            request,
            config_dir=config_dir,
            database_url=database_url,
            status_code=503,
            feedback=_build_scheduler_action_feedback(
                kind="error",
                action_label=_humanize_label(action),
                message=str(exc),
            ),
        )
    except DraftGenerationProviderError as exc:
        return _render_console_scheduler_page(
            request,
            config_dir=config_dir,
            database_url=database_url,
            status_code=422,
            feedback=_build_scheduler_action_feedback(
                kind="error",
                action_label=_humanize_label(action),
                message=str(exc),
            ),
        )

    return _render_console_scheduler_page(
        request,
        config_dir=config_dir,
        database_url=database_url,
        feedback=_build_scheduler_action_success_feedback(
            action=action,
            result=result,
        ),
        action_result=_build_scheduler_action_result(
            request,
            action=action,
            result=result,
            database_url=database_url,
        ),
    )


@console_router.get(
    "/console/reviews/pending",
    response_class=HTMLResponse,
    name="console_pending_review",
)
def get_console_pending_review(
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
) -> HTMLResponse:
    """Render the current manual-review queue in the console."""

    query_params = _extract_console_query_params(request)
    result = request.app.state.console_pending_review_drafts_lister(
        database_url=database_url,
    )
    context = _build_console_context(
        request,
        page_title="검토 대기",
        page_description="승인 또는 발행 안전성 규칙은 유지한 채, 공용 검토 대기열 헬퍼의 현재 수동 검토 작업량을 보여줍니다.",
        active_nav_key="pending_review",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "pending_review_metrics": _build_pending_review_metrics(result.drafts),
            "pending_review_rows": [
                _build_pending_review_row(
                    request,
                    query_params,
                    position,
                    row,
                )
                for position, row in enumerate(result.drafts, start=1)
            ],
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/pending_review.html",
        context=context,
    )


@console_router.get(
    "/console/reviews/{draft_id}",
    response_class=HTMLResponse,
    name="console_review_detail",
)
def get_console_review_detail(
    draft_id: int,
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
) -> HTMLResponse:
    """Render one review draft with provenance, audit history, and workflow-aligned actions."""

    return _render_console_review_detail_page(
        request,
        draft_id=draft_id,
        config_dir=config_dir,
        database_url=database_url,
    )


@console_router.post(
    "/console/reviews/{draft_id}",
    response_class=HTMLResponse,
    name="console_review_detail_action",
)
async def post_console_review_detail_action(
    draft_id: int,
    request: Request,
    config_dir: str = Query(default="config"),
    database_url: str | None = Query(default=None),
) -> HTMLResponse:
    """Handle review actions from the draft detail page without bypassing workflow rules."""

    form_data = await _parse_console_form_body(request)
    action = (form_data.get("action") or "").strip().lower()
    submitted_values = _normalize_review_action_form_data(form_data)

    if action not in {"approve", "reject", "edit", "schedule"}:
        return _render_console_review_detail_page(
            request,
            draft_id=draft_id,
            config_dir=config_dir,
            database_url=database_url,
            status_code=422,
            feedback=_build_review_action_feedback(
                kind="error",
                action_label="검토 작업",
                message="폼을 제출하기 전에 지원되는 검토 작업을 선택하세요.",
            ),
            form_values=submitted_values,
        )

    try:
        result = _execute_console_review_action(
            request,
            draft_id=draft_id,
            action=action,
            submitted_values=submitted_values,
            config_dir=config_dir,
            database_url=database_url,
        )
    except DraftNotFoundError:
        return _render_console_review_detail_page(
            request,
            draft_id=draft_id,
            config_dir=config_dir,
            database_url=database_url,
            status_code=404,
            form_values=submitted_values,
        )
    except DraftReviewStateError as exc:
        return _render_console_review_detail_page(
            request,
            draft_id=draft_id,
            config_dir=config_dir,
            database_url=database_url,
            status_code=409,
            feedback=_build_review_action_feedback(
                kind="error",
                action_label=_humanize_label(action),
                message=str(exc),
            ),
            form_values=submitted_values,
        )
    except DraftValidationFailedError as exc:
        return _render_console_review_detail_page(
            request,
            draft_id=draft_id,
            config_dir=config_dir,
            database_url=database_url,
            status_code=422,
            feedback=_build_review_action_feedback(
                kind="error",
                action_label=_humanize_label(action),
                message=str(exc),
            ),
            form_values=submitted_values,
        )
    except DraftScheduleError as exc:
        message = str(exc)
        return _render_console_review_detail_page(
            request,
            draft_id=draft_id,
            config_dir=config_dir,
            database_url=database_url,
            status_code=409 if "already has an active publish job" in message else 422,
            feedback=_build_review_action_feedback(
                kind="error",
                action_label=_humanize_label(action),
                message=message,
            ),
            form_values=submitted_values,
        )
    except (ReviewerIdentityError, ReviewQueueError) as exc:
        return _render_console_review_detail_page(
            request,
            draft_id=draft_id,
            config_dir=config_dir,
            database_url=database_url,
            status_code=422,
            feedback=_build_review_action_feedback(
                kind="error",
                action_label=_humanize_label(action),
                message=str(exc),
            ),
            form_values=submitted_values,
        )

    return _render_console_review_detail_page(
        request,
        draft_id=draft_id,
        config_dir=config_dir,
        database_url=database_url,
        feedback=_build_review_action_success_feedback(result),
    )


def _render_console_review_detail_page(
    request: Request,
    *,
    draft_id: int,
    config_dir: str,
    database_url: str | None,
    status_code: int = 200,
    feedback: dict[str, str] | None = None,
    form_values: dict[str, str] | None = None,
) -> HTMLResponse:
    """Render the shared review detail page for both GET and POST flows."""

    query_params = _extract_console_query_params(request)
    pending_review_href = _append_query_params(
        str(request.url_for("console_pending_review")),
        query_params,
    )

    try:
        detail = request.app.state.console_review_draft_detail_fetcher(
            draft_id,
            database_url=database_url,
        )
    except DraftNotFoundError as exc:
        context = _build_console_context(
            request,
            page_title="검토 초안을 찾을 수 없음",
            page_description="현재 운영 콘텍스트에서는 요청한 초안 상세를 불러올 수 없습니다.",
            active_nav_key="pending_review",
            config_dir=config_dir,
            database_url=database_url,
        )
        context.update(
            {
                "pending_review_href": pending_review_href,
                "review_detail": None,
                "review_detail_missing": {
                    "message": str(exc),
                    "draft_id": draft_id,
                },
                "review_action_feedback": feedback,
                "review_action_forms": None,
            }
        )
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="console/review_detail.html",
            context=context,
            status_code=404,
        )

    context = _build_console_context(
        request,
        page_title=f"검토 초안 {detail.draft.id}",
        page_description="기존 워크플로 검증과 상태 보호 장치를 재사용하는 출처 정보, 감사 이력, 브라우저 검토 액션을 한곳에서 제공합니다.",
        active_nav_key="pending_review",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "pending_review_href": pending_review_href,
            "review_detail": _build_review_detail(
                request,
                query_params,
                detail,
            ),
            "review_detail_missing": None,
            "review_action_feedback": feedback,
            "review_action_forms": _build_review_action_form_state(
                request,
                query_params,
                detail,
                config_dir=config_dir,
                form_values=form_values,
            ),
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/review_detail.html",
        context=context,
        status_code=status_code,
    )


def _execute_console_review_action(
    request: Request,
    *,
    draft_id: int,
    action: str,
    submitted_values: dict[str, str],
    config_dir: str,
    database_url: str | None,
):
    if action == "approve":
        return request.app.state.console_draft_approver(
            draft_id,
            reviewer=submitted_values["reviewer"],
            config_dir=config_dir,
            database_url=database_url,
        )
    if action == "reject":
        return request.app.state.console_draft_rejector(
            draft_id,
            reason=submitted_values["reject_reason"],
            reviewer=submitted_values["reviewer"],
            config_dir=config_dir,
            database_url=database_url,
        )
    if action == "edit":
        return request.app.state.console_draft_editor(
            draft_id,
            body=submitted_values["edit_body"],
            reviewer=submitted_values["reviewer"],
            config_dir=config_dir,
            database_url=database_url,
        )
    return request.app.state.console_draft_scheduler(
        draft_id,
        scheduled_for=submitted_values["scheduled_for"],
        reviewer=submitted_values["reviewer"],
        config_dir=config_dir,
        database_url=database_url,
    )


def _execute_console_manual_publish_action(
    request: Request,
    *,
    publish_job_id: int,
    action: str,
    submitted_values: dict[str, str],
    database_url: str | None,
):
    if action == "complete":
        return request.app.state.console_manual_publish_completer(
            publish_job_id,
            operator=submitted_values["operator"],
            external_post_id=submitted_values["external_post_id"],
            database_url=database_url,
        )
    if action == "fail":
        return request.app.state.console_manual_publish_failer(
            publish_job_id,
            operator=submitted_values["operator"],
            error_message=submitted_values["error_message"],
            database_url=database_url,
        )
    return request.app.state.console_manual_publish_canceller(
        publish_job_id,
        operator=submitted_values["operator"],
        reason=submitted_values["cancel_reason"],
        database_url=database_url,
    )


async def _parse_console_form_body(request: Request) -> dict[str, str]:
    raw_body = await request.body()
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {
        key: values[-1] if values else ""
        for key, values in parsed.items()
    }

def _normalize_review_action_form_data(form_data: dict[str, str]) -> dict[str, str]:
    return {
        "reviewer": (form_data.get("reviewer") or "").strip(),
        "reject_reason": form_data.get("reason") or "",
        "edit_body": form_data.get("body") or "",
        "scheduled_for": (form_data.get("scheduled_for") or "").strip(),
    }


def _normalize_manual_publish_action_form_data(form_data: dict[str, str]) -> dict[str, str]:
    return {
        "operator": (form_data.get("operator") or "").strip(),
        "external_post_id": (form_data.get("external_post_id") or "").strip(),
        "error_message": form_data.get("error_message") or "",
        "cancel_reason": form_data.get("reason") or "",
    }


def _build_review_action_success_feedback(result) -> dict[str, str]:
    action_label = _humanize_label(result.action_type.value)
    created_manual_handoff = (
        getattr(result, "publish_job_id", None) is not None
        and getattr(result, "scheduled_for", None) is None
    )
    approved_message = (
        "초안이 승인되었습니다. 이제 이 작업공간에서 예약을 진행할 수 있습니다."
        if not created_manual_handoff
        else "초안이 승인되었습니다. 이제 이 작업공간에서 수동 업로드용 본문을 복사해 게시할 수 있습니다."
    )
    messages = {
        "approve": approved_message,
        "reject": "초안이 반려되었습니다. 반려 사유가 감사 이력에 기록되었습니다.",
        "edit": "초안 본문이 수정되었습니다. 수정 내용이 감사 이력에 기록되었습니다.",
        "schedule": (
            f"초안이 {_format_datetime(result.scheduled_for, none_label='예약되지 않음')}에 예약되었고 "
            f"발행 작업 {result.publish_job_id}이 생성되었습니다."
        ),
    }
    return _build_review_action_feedback(
        kind="success",
        action_label=action_label,
        message=messages[result.action_type.value],
    )


def _build_review_action_feedback(
    *,
    kind: str,
    action_label: str,
    message: str,
) -> dict[str, str]:
    return {
        "kind": kind,
        "title": f"{action_label} {'완료' if kind == 'success' else '불가'}",
        "message": message,
    }

def _build_manual_publish_success_feedback(action: str, result) -> dict[str, str]:
    if action == "complete":
        external_post_detail = (
            f" 외부 게시물 ID {result.external_post_id}도 함께 저장되었습니다."
            if result.external_post_id
            else ""
        )
        message = (
            "수동 업로드 결과가 발행 완료로 기록되었습니다. "
            f"발행 작업 {result.publish_job_id}의 상태와 타임라인이 갱신되었습니다."
            f"{external_post_detail}"
        )
    elif action == "fail":
        message = (
            "수동 업로드 실패가 기록되었습니다. 마지막 오류와 발행 로그가 이 작업에 함께 남았습니다."
        )
    else:
        message = (
            "수동 업로드 handoff가 취소되었습니다. 필요하면 검토 흐름에서 새 초안을 다시 승인해 새 작업을 만들 수 있습니다."
        )
    return _build_manual_publish_action_feedback(
        kind="success",
        action_label=_manual_publish_action_label(action),
        message=message,
    )


def _build_manual_publish_action_feedback(
    *,
    kind: str,
    action_label: str,
    message: str,
) -> dict[str, str]:
    return {
        "kind": kind,
        "title": f"{action_label} {'완료' if kind == 'success' else '불가'}",
        "message": message,
    }


def _manual_publish_action_label(action: str) -> str:
    labels = {
        "complete": "발행 완료 기록",
        "fail": "발행 실패 기록",
        "cancel": "발행 전달 취소",
    }
    return labels.get(action, "수동 발행 기록")


def _render_console_scheduler_page(
    request: Request,
    *,
    config_dir: str,
    database_url: str | None,
    status_code: int = 200,
    feedback: dict[str, str] | None = None,
    action_result: dict[str, object] | None = None,
) -> HTMLResponse:
    """Render the shared scheduler control page for GET and POST flows."""

    query_params = _extract_console_query_params(request)
    context = _build_console_context(
        request,
        page_title="스케줄러",
        page_description="뉴스 수집, 발견만 확인, 저장, 기사 보강, 백필, 발행 예정 처리를 현재 워크플로 경로에 맞춰 실행하는 브라우저 제어 화면입니다.",
        active_nav_key="scheduler",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "scheduler_action_href": _append_query_params(
                str(request.url_for("console_scheduler_action")),
                query_params,
            ),
            "scheduler_action_feedback": feedback,
            "scheduler_action_result": action_result,
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/scheduler.html",
        context=context,
        status_code=status_code,
    )


def _execute_console_scheduler_action(
    request: Request,
    *,
    action: str,
    config_dir: str,
    database_url: str | None,
    live_requested: bool,
):
    if action == "discover":
        return request.app.state.console_scheduler_discover_runner(
            config_dir=config_dir,
        )
    if action == "ingest":
        return request.app.state.console_ingest_sources_runner(
            config_dir=config_dir,
            database_url=database_url,
        )
    if action == "enrich":
        return request.app.state.console_enrich_articles_runner(
            config_dir=config_dir,
            database_url=database_url,
        )
    if action == "run_local":
        return request.app.state.console_run_local_pipeline_runner(
            config_dir=config_dir,
            database_url=database_url,
        )
    if action == "backfill":
        return request.app.state.console_scheduler_backfill_runner(
            config_dir=config_dir,
            database_url=database_url,
        )
    return request.app.state.console_scheduler_publish_due_runner(
        config_dir=config_dir,
        database_url=database_url,
        dry_run=not live_requested,
    )


def _is_live_publish_requested(form_data: dict[str, str]) -> bool:
    value = (form_data.get("live") or "").strip().lower()
    return value in _SCHEDULER_LIVE_VALUES


def _build_scheduler_action_success_feedback(
    *,
    action: str,
    result,
) -> dict[str, str]:
    action_label = _humanize_label(action)
    if action == "discover":
        message = (
            f"후보 수집이 완료되었습니다. {len(result.processed_sources)}개의 설정된 소스에서 "
            f"{result.discovered_count}개의 항목을 발견했습니다."
        )
    elif action == "ingest":
        message = (
            f"수집 저장이 완료되었습니다. {result.discovered_count}개의 발견 후보 중 "
            f"{result.saved_count}개를 저장했고 {result.duplicate_count}개 중복을 차단했습니다."
        )
    elif action == "enrich":
        message = (
            f"기사 보강이 완료되었습니다. {result.processed_count}개의 저장된 수집 항목 중 "
            f"{result.enriched_count}개를 보강했고 {result.skipped_count}개를 정책에 따라 건너뛰었습니다."
        )
    elif action == "run_local":
        duplicate_count = getattr(result, "duplicate_count", 0)
        message = (
            f"뉴스 수집이 완료되었습니다. 발견 {result.ingest_discovered_count}, 저장 {result.ingest_saved_count}, "
            f"중복 차단 {duplicate_count}, 보강 {result.enrichment_enriched_count}, 브리프 {result.brief_created_count}, 초안 {result.draft_created_variant_count}건입니다. "
            "생성된 초안은 검토 대기열에 저장되었습니다."
        )
    elif action == "backfill":
        message = (
            f"백필이 완료되었습니다. {result.processed_channel_count}개의 계정 경로를 확인해 "
            f"{result.created_count}개의 발행 작업을 만들었습니다."
        )
    else:
        mode_label = "드라이런 모드" if result.dry_run else "실발행 모드"
        message = (
            f"발행 예정 처리가 {mode_label}로 완료되었습니다. "
            f"{result.processed_count}개의 도래한 작업을 처리했습니다."
        )
    return _build_scheduler_action_feedback(
        kind="success",
        action_label=action_label,
        message=message,
    )


def _build_scheduler_action_feedback(
    *,
    kind: str,
    action_label: str,
    message: str,
) -> dict[str, str]:
    return {
        "kind": kind,
        "title": f"{action_label} {'완료' if kind == 'success' else '불가'}",
        "message": message,
    }
