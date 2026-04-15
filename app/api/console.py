"""Server-rendered operator console routes and assets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.connectors.llm import DraftGenerationProviderError
from app.connectors.publishers.resolver import channel_requires_manual_publish_handoff
from app.config import ConfigError
from app.storage import DatabaseSchemaError, PublishJobState
from app.workflows.history_queries import PublishJobNotFoundError
from app.workflows.review_queue import (
    DraftNotFoundError,
    DraftReviewStateError,
    DraftScheduleError,
    DraftValidationFailedError,
    ManualPublishError,
    ManualPublishStateError,
    ReviewQueueError,
    ReviewerIdentityError,
)

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_CONTEXT_QUERY_KEYS = ("config_dir", "database_url")
_DEFAULT_DASHBOARD_RUN_LIMIT = 6
_DEFAULT_DASHBOARD_FAILURE_LIMIT = 6
_DEFAULT_ARTICLE_LIMIT = 25
_DEFAULT_PUBLISH_JOB_LIMIT = 25
_SCHEDULER_LIVE_VALUES = {"1", "on", "true", "yes"}
_MANUAL_UPLOAD_CHANNELS = frozenset({"linkedin", "threads"})
_KOREAN_LABELS = {
    "analysis": "분석",
    "approve": "승인",
    "approved": "승인됨",
    "article_extract": "본문 추출",
    "backfill": "백필",
    "brief_build": "브리프 생성",
    "cancelled": "취소됨",
    "canonical_url": "대표 URL 중복",
    "discover": "수집",
    "discovery_only": "탐색 전용",
    "draft_generate": "초안 생성",
    "dry_run": "드라이런",
    "edit": "수정",
    "enrich": "기사 보강",
    "enriched": "보강 완료",
    "existing": "기존 있음",
    "failed": "실패",
    "html_fetch": "HTML 수집",
    "ingest": "수집 저장",
    "in_progress": "진행 중",
    "linkedin": "LinkedIn",
    "manual_local": "로컬 수동 실행",
    "news": "뉴스",
    "normalized_title_hash": "정규화 제목 중복",
    "opinion": "의견",
    "other": "기타",
    "partial": "부분 완료",
    "pending": "대기",
    "pending_review": "검토 대기",
    "practical_how_to": "실무 가이드",
    "product": "제품",
    "product_update": "제품 업데이트",
    "publish_due": "발행 예정 처리",
    "published": "발행 완료",
    "publishing": "발행 중",
    "recent_fingerprint": "최근 내용 중복",
    "reject": "반려",
    "rejected": "반려됨",
    "restricted": "제한됨",
    "run_local": "뉴스 수집",
    "reusable": "재사용 가능",
    "rss_discovered": "RSS 수집",
    "running": "실행 중",
    "saved": "저장",
    "schedule": "예약",
    "scheduled": "예약됨",
    "skipped": "건너뜀",
    "source_identity": "소스 고유 ID 중복",
    "succeeded": "성공",
    "summary_regenerate": "요약 재생성",
    "threads": "Threads",
    "topic_takeaway": "핵심 요약",
    "trend_insight": "트렌드 인사이트",
    "tutorial": "튜토리얼",
    "x": "X",
}

console_router = APIRouter(include_in_schema=False)


@dataclass(frozen=True, slots=True)
class ConsoleNavItem:
    """Navigation metadata for the operator console shell."""

    label: str
    description: str
    status: str
    href: str | None = None
    active: bool = False


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


def _build_scheduler_action_result(
    request: Request,
    *,
    action: str,
    result,
    database_url: str | None,
) -> dict[str, object]:
    query_params = _extract_console_query_params(request)

    if action == "discover":
        processed_sources = list(result.processed_sources)
        failure_messages = list(result.failure_messages)
        return {
            "kind": "discover",
            "title": "후보 수집 요약",
            "badge": "후보 수집",
            "summary": (
                f"후보 수집이 {len(processed_sources)}개의 설정된 소스를 확인했고 "
                f"{result.discovered_count}개의 발견 항목을 기록했습니다."
            ),
            "metrics": [
                {"label": "발견 항목", "value": str(result.discovered_count)},
                {"label": "처리한 소스", "value": str(len(processed_sources))},
                {"label": "실패", "value": str(result.failure_count)},
            ],
            "processed_sources": processed_sources,
            "failure_messages": failure_messages,
        }

    if action == "ingest":
        processed_sources = list(result.processed_sources)
        failure_messages = [failure.format_for_cli() for failure in result.failures]
        return {
            "kind": "ingest",
            "title": "수집 저장 요약",
            "badge": "수집 저장",
            "summary": (
                f"수집 저장이 {len(processed_sources)}개의 설정된 소스를 확인했고 "
                f"{result.saved_count}개의 새 항목을 저장했습니다."
            ),
            "metrics": [
                {"label": "발견 후보", "value": str(result.discovered_count)},
                {"label": "저장", "value": str(result.saved_count)},
                {"label": "중복 차단", "value": str(result.duplicate_count)},
                {"label": "실패", "value": str(result.failure_count)},
            ],
            "processed_sources": processed_sources,
            "duplicate_reasons": [
                {
                    "label": _humanize_label(reason),
                    "value": str(count),
                }
                for reason, count in result.duplicate_counts_by_reason().items()
            ],
            "failure_messages": failure_messages,
        }

    if action == "enrich":
        failure_counts = result.failure_counts_by_stage()
        return {
            "kind": "enrich",
            "title": "기사 보강 요약",
            "badge": "기사 보강",
            "summary": (
                f"기사 보강이 저장된 수집 항목 {result.processed_count}건을 확인했고 "
                f"{result.enriched_count}건을 보강했습니다."
            ),
            "metrics": [
                {"label": "처리한 항목", "value": str(result.processed_count)},
                {"label": "보강 완료", "value": str(result.enriched_count)},
                {"label": "기존 완료", "value": str(result.existing_count)},
                {"label": "정책상 건너뜀", "value": str(result.skipped_count)},
                {"label": "실패", "value": str(result.failed_count)},
            ],
            "failure_stages": [
                {
                    "label": _humanize_label(stage),
                    "value": str(count),
                }
                for stage, count in failure_counts.items()
            ],
        }

    if action == "run_local":
        created_draft_rows = _build_scheduler_created_draft_rows(
            request,
            query_params=query_params,
            database_url=database_url,
            draft_ids=tuple(getattr(result, "created_draft_ids", ()) or ()),
        )
        duplicate_reason_rows = [
            {
                "label": _humanize_label(reason),
                "value": str(count),
            }
            for reason, count in tuple(getattr(result, "duplicate_reasons", ()) or ())
        ]
        return {
            "kind": "run_local",
            "title": "뉴스 수집 요약",
            "badge": "뉴스 수집",
            "summary": "발견부터 저장, 기사 보강, 브리프 생성, 초안 생성까지 현재 로컬 뉴스 수집 워크플로를 한 번 실행했습니다.",
            "metrics": [
                {"label": "실행 ID", "value": str(result.pipeline_run_id)},
                {"label": "상태", "value": _humanize_label(result.status.value)},
                {"label": "발견", "value": str(result.ingest_discovered_count)},
                {"label": "저장", "value": str(result.ingest_saved_count)},
                {"label": "중복 차단", "value": str(getattr(result, "duplicate_count", 0))},
                {"label": "보강", "value": str(result.enrichment_enriched_count)},
                {"label": "브리프", "value": str(result.brief_created_count)},
                {"label": "초안", "value": str(result.draft_created_variant_count)},
                {"label": "실패", "value": str(result.failure_count)},
            ],
            "pending_review_href": _append_query_params(
                str(request.url_for("console_pending_review")),
                query_params,
            ),
            "duplicate_reasons": duplicate_reason_rows,
            "created_drafts": created_draft_rows,
        }

    if action == "backfill":
        return {
            "kind": "backfill",
            "title": "백필 요약",
            "badge": "백필",
            "summary": (
                f"백필이 {result.processed_channel_count}개의 계정 경로를 확인해 "
                f"{result.created_count}개의 예약 발행 작업을 만들었습니다."
            ),
            "metrics": [
                {"label": "확인한 경로", "value": str(result.processed_channel_count)},
                {"label": "생성한 작업", "value": str(result.created_count)},
                {"label": "기존 미래 작업", "value": str(result.existing_count)},
                {"label": "건너뛴 슬롯", "value": str(result.skipped_count)},
            ],
            "outcomes": [_build_scheduler_backfill_outcome_row(outcome) for outcome in result.outcomes],
        }

    return {
        "kind": "publish_due",
        "title": "발행 예정 처리 요약",
        "badge": "발행 예정 처리",
        "mode_label": "드라이런" if result.dry_run else "실발행",
        "summary": (
            "브라우저에서 명시적으로 선택했기 때문에 실발행이 실행되었습니다."
            if not result.dry_run
            else "드라이런이 브라우저 기본 경로로 유지되어 발행 상태 변경은 적용되지 않았습니다."
        ),
        "metrics": [
            {"label": "처리한 도래 작업", "value": str(result.processed_count)},
            {"label": "발행 완료", "value": str(result.published_count)},
            {"label": "실패", "value": str(result.failed_count)},
            {"label": "드라이런만 수행", "value": str(result.dry_run_count)},
            {"label": "건너뜀", "value": str(result.skipped_count)},
        ],
        "outcomes": [_build_scheduler_publish_due_outcome_row(outcome) for outcome in result.outcomes],
    }


def _build_scheduler_created_draft_rows(
    request: Request,
    *,
    query_params: dict[str, str],
    database_url: str | None,
    draft_ids: tuple[int, ...],
) -> list[dict[str, str]]:
    if not draft_ids:
        return []

    pending_result = request.app.state.console_pending_review_drafts_lister(
        database_url=database_url,
    )
    pending_by_id = {
        row.draft_id: row
        for row in pending_result.drafts
    }
    rows: list[dict[str, str]] = []

    for draft_id in draft_ids:
        pending_row = pending_by_id.get(draft_id)
        rows.append(
            {
                "draft_label": f"초안 {draft_id}",
                "detail_href": _append_query_params(
                    str(request.url_for("console_review_detail", draft_id=draft_id)),
                    query_params,
                ),
                "title": pending_row.title if pending_row is not None else "생성된 초안",
                "body_preview": _truncate_text(
                    pending_row.body if pending_row is not None else "초안 본문은 상세 화면에서 확인하세요.",
                    limit=180,
                ),
            }
        )

    return rows


def _build_scheduler_backfill_outcome_row(outcome) -> dict[str, str]:
    return {
        "route_label": f"{outcome.account_key} / {outcome.channel.upper()}",
        "backlog_target": str(outcome.backlog_target),
        "existing_future_job_count": str(outcome.existing_future_job_count),
        "eligible_draft_count": str(outcome.eligible_draft_count),
        "planned_slot_count": str(outcome.planned_slot_count),
        "created_job_ids": _format_list(outcome.created_job_ids, fallback="생성 없음"),
        "created_count": str(outcome.created_count),
        "skipped_slot_count": str(outcome.skipped_slot_count),
    }


def _build_scheduler_publish_due_outcome_row(outcome) -> dict[str, str]:
    return {
        "publish_job_label": f"발행 작업 {outcome.publish_job_id}",
        "status": _humanize_label(outcome.status),
        "state": _humanize_label(outcome.state.value),
        "message": outcome.message,
        "external_post_id": outcome.external_post_id or "기록된 외부 게시물 없음",
    }


def _build_console_context(
    request: Request,
    *,
    page_title: str,
    page_description: str,
    active_nav_key: str,
    config_dir: str,
    database_url: str | None,
) -> dict[str, object]:
    query_params = _extract_console_query_params(request)
    return {
        "page_title": page_title,
        "page_description": page_description,
        "console_asset_css_url": str(request.url_for("console_static", path="/console.css")),
        "console_nav_items": _build_console_nav_items(
            request,
            query_params,
            active_nav_key=active_nav_key,
        ),
        "operator_context": {
            "config_dir": config_dir,
            "database_url": database_url,
        },
    }


def _build_console_nav_items(
    request: Request,
    query_params: dict[str, str],
    *,
    active_nav_key: str,
) -> list[ConsoleNavItem]:
    return [
        ConsoleNavItem(
            label="콘솔 홈",
            description="브라우저 콘솔의 공통 셸, 운영 콘텍스트, 진행 방향을 보여줍니다.",
            status="준비됨",
            href=_append_query_params(str(request.url_for("console_home")), query_params),
            active=active_nav_key == "home",
        ),
        ConsoleNavItem(
            label="실행 및 실패",
            description="최근 파이프라인 실행, 기술 실패, 정책상 건너뜀을 읽기 전용으로 확인합니다.",
            status="준비됨",
            href=_append_query_params(str(request.url_for("console_dashboard")), query_params),
            active=active_nav_key == "dashboard",
        ),
        ConsoleNavItem(
            label="아티클",
            description="공용 운영자 아티클 상태 헬퍼를 기반으로 한 읽기 전용 상태 표입니다.",
            status="준비됨",
            href=_append_query_params(str(request.url_for("console_articles")), query_params),
            active=active_nav_key == "articles",
        ),
        ConsoleNavItem(
            label="검토 대기",
            description="현재 검토 대기열과 수동 검토용 초안 상세 작업공간을 제공합니다.",
            status="준비됨",
            href=_append_query_params(str(request.url_for("console_pending_review")), query_params),
            active=active_nav_key == "pending_review",
        ),
        ConsoleNavItem(
            label="발행 작업",
            description="발행 대기열, 전달 상태, 수동 업로드 결과 기록이 가능한 개별 작업 화면을 제공합니다.",
            status="준비됨",
            href=_append_query_params(str(request.url_for("console_publish_jobs")), query_params),
            active=active_nav_key == "publish_jobs",
        ),
        ConsoleNavItem(
            label="스케줄러",
            description="뉴스 수집, 발견만 확인, 저장, 기사 보강, 백필, 드라이런 우선 발행을 실행하는 제어 화면입니다.",
            status="준비됨",
            href=_append_query_params(str(request.url_for("console_scheduler")), query_params),
            active=active_nav_key == "scheduler",
        ),
    ]


def _build_dashboard_metrics(runs_result, failures_result) -> list[dict[str, str]]:
    latest_run = runs_result.runs[0] if runs_result.runs else None
    latest_status = _humanize_label(latest_run.status) if latest_run else "아직 실행 이력 없음"
    latest_detail = (
        f"{latest_run.workflow_name} / {_format_datetime(latest_run.started_at)}"
        if latest_run
        else "다음 파이프라인 실행 이력이 저장되면 대시보드가 채워집니다."
    )
    return [
        {
            "label": "최신 실행",
            "value": latest_status,
            "detail": latest_detail,
        },
        {
            "label": "최근 실행",
            "value": str(len(runs_result.runs)),
            "detail": "공용 파이프라인 실행 이력 헬퍼에서 가져온 값입니다.",
        },
        {
            "label": "기술 실패",
            "value": str(len(failures_result.failures)),
            "detail": "읽을 수 없거나 차단된 콘텐츠 수집·추출 실패입니다.",
        },
        {
            "label": "정책상 건너뜀",
            "value": str(len(failures_result.policy_skips)),
            "detail": "실패와 별도로 기록되는 의도된 정책 제약입니다.",
        },
    ]


def _build_dashboard_latest_run(run) -> dict[str, object] | None:
    if run is None:
        return None
    return {
        "workflow_name": run.workflow_name,
        "status": _humanize_label(run.status),
        "trigger_mode": _humanize_label(run.trigger_mode),
        "started_at": _format_datetime(run.started_at),
        "completed_at": _format_datetime(run.completed_at),
        "counts": [
            {"label": "발견", "value": str(run.discovered_count)},
            {"label": "저장", "value": str(run.saved_count)},
            {"label": "보강", "value": str(run.enriched_count)},
            {"label": "브리프", "value": str(run.brief_count)},
            {"label": "초안", "value": str(run.draft_count)},
            {"label": "실패", "value": str(run.failure_count)},
        ],
        "policy_summary": _format_policy_mode_counts(run.policy_mode_counts),
        "policy_guardrails": (
            f"정책상 건너뜀 {run.policy_skipped_count} / 출처 표기 필수 {run.attribution_required_count}"
        ),
        "rewrite_providers": _format_list(run.rewrite_providers, fallback="기록 없음"),
        "latest_error_code": run.latest_error_code or "없음",
    }


def _build_dashboard_run_row(row) -> dict[str, str]:
    return {
        "workflow_name": row.workflow_name,
        "status": _humanize_label(row.status),
        "trigger_mode": _humanize_label(row.trigger_mode),
        "started_at": _format_datetime(row.started_at),
        "completed_at": _format_datetime(row.completed_at),
        "counts_summary": (
            f"발견 {row.discovered_count} / 저장 {row.saved_count} / "
            f"보강 {row.enriched_count} / 브리프 {row.brief_count} / "
            f"초안 {row.draft_count} / 실패 {row.failure_count}"
        ),
        "policy_summary": _format_policy_mode_counts(row.policy_mode_counts),
        "policy_guardrails": (
            f"정책상 건너뜀 {row.policy_skipped_count} / 출처 표기 필수 {row.attribution_required_count}"
        ),
        "rewrite_providers": _format_list(row.rewrite_providers, fallback="기록 없음"),
        "latest_error_code": row.latest_error_code or "없음",
    }


def _build_dashboard_failure_row(row) -> dict[str, str]:
    return {
        "title": row.title,
        "source_name": row.source_name or "알 수 없는 소스",
        "article_url": row.article_url,
        "failure_code": row.failure_code,
        "failure_stage": _humanize_label(row.failure_stage),
        "failure_message": row.failure_message,
        "policy_mode": _humanize_label(row.source_policy_mode),
        "require_attribution": "필수" if row.require_attribution else "불필요",
        "updated_at": _format_datetime(row.updated_at),
    }


def _build_dashboard_policy_skip_row(row) -> dict[str, str]:
    return {
        "title": row.title,
        "source_name": row.source_name or "알 수 없는 소스",
        "article_url": row.article_url,
        "skipped_stage": _humanize_label(row.skipped_stage),
        "policy_decision_reason": row.policy_decision_reason,
        "policy_mode": _humanize_label(row.source_policy_mode),
        "require_attribution": "필수" if row.require_attribution else "불필요",
        "updated_at": _format_datetime(row.updated_at),
    }


def _build_article_metrics(rows) -> list[dict[str, str]]:
    pending_or_active = sum(
        1
        for row in rows
        if row.enrichment_state in {"pending", "in_progress"}
    )
    enriched = sum(1 for row in rows if row.enrichment_state == "enriched")
    needs_attention = sum(
        1
        for row in rows
        if row.enrichment_state in {"failed", "skipped"}
    )
    latest_discovered = (
        _format_datetime(rows[0].discovered_at, none_label="기록 없음")
        if rows
        else "저장된 발견 이력을 기다리는 중"
    )
    return [
        {
            "label": "표시 중인 행",
            "value": str(len(rows)),
            "detail": "현재 운영 콘텍스트에서 최근 저장된 소스 항목을 표 순서대로 보여줍니다.",
        },
        {
            "label": "대기 또는 진행 중",
            "value": str(pending_or_active),
            "detail": f"가장 최근 발견 시각 {latest_discovered}",
        },
        {
            "label": "보강 완료",
            "value": str(enriched),
            "detail": "요약 재생성을 성공적으로 마친 행입니다.",
        },
        {
            "label": "확인 필요",
            "value": str(needs_attention),
            "detail": "실패했거나 정책상 건너뛴 행도 워크플로 상태 변경 없이 계속 표시됩니다.",
        },
    ]


def _build_article_row(row) -> dict[str, str | None]:
    return {
        "source_name": row.source_name,
        "source_item_label": f"소스 항목 {row.source_item_id}",
        "article_enrichment_label": (
            f"보강 {row.article_enrichment_id}"
            if row.article_enrichment_id is not None
            else "보강이 아직 생성되지 않음"
        ),
        "title": row.title,
        "original_url": row.original_url,
        "article_url": row.article_url,
        "published_at": _format_datetime(row.published_at, none_label="기록 없음"),
        "discovered_at": _format_datetime(row.discovered_at, none_label="기록 없음"),
        "enrichment_state": _humanize_label(row.enrichment_state),
        "stage_summary": (
            f"수집 {_humanize_label(row.fetch_status)} / "
            f"추출 {_humanize_label(row.extract_status)} / "
            f"요약 {_humanize_label(row.summarize_status)}"
        ),
        "last_failure_message": row.last_failure_message or "표시할 실패 기록이 없습니다.",
    }


def _build_publish_job_query_params(
    request: Request,
    *,
    state: PublishJobState | None,
    account_key: str | None,
    channel: str | None,
    limit: int,
) -> dict[str, str]:
    query_params = dict(_extract_console_query_params(request))
    normalized_account_key = account_key.strip() if account_key else ""
    normalized_channel = channel.strip() if channel else ""

    if state is not None:
        query_params["state"] = state.value
    if normalized_account_key:
        query_params["account_key"] = normalized_account_key
    if normalized_channel:
        query_params["channel"] = normalized_channel
    if limit != _DEFAULT_PUBLISH_JOB_LIMIT:
        query_params["limit"] = str(limit)
    return query_params


def _build_publish_job_filters(
    *,
    state: PublishJobState | None,
    account_key: str | None,
    channel: str | None,
    limit: int,
) -> dict[str, str]:
    normalized_account_key = account_key.strip() if account_key else ""
    normalized_channel = channel.strip() if channel else ""
    return {
        "state": _humanize_label(state.value) if state is not None else "전체 상태",
        "account_key": normalized_account_key or "전체 계정",
        "channel": normalized_channel.upper() if normalized_channel else "전체 채널",
        "limit": str(limit),
    }


def _build_publish_job_metrics(rows) -> list[dict[str, str]]:
    active_jobs = sum(1 for row in rows if row.state in {"scheduled", "publishing"})
    published_jobs = sum(1 for row in rows if row.state == "published")
    needs_attention = sum(1 for row in rows if row.state in {"failed", "cancelled"})
    account_keys = sorted({row.account_key for row in rows})
    return [
        {
            "label": "표시 중인 작업",
            "value": str(len(rows)),
            "detail": "공용 운영자 목록 헬퍼가 반환한 최근 발행 작업입니다.",
        },
        {
            "label": "활성 대기열",
            "value": str(active_jobs),
            "detail": "아직 전달 전인 예약 또는 발행 중 작업입니다.",
        },
        {
            "label": "발행 완료",
            "value": str(published_jobs),
            "detail": "외부 발행이 완료된 상태까지 도달한 작업입니다.",
        },
        {
            "label": "표시 중인 계정",
            "value": str(len(account_keys)),
            "detail": _format_list(account_keys, fallback="표시 중인 계정 없음"),
        },
        {
            "label": "확인 필요",
            "value": str(needs_attention),
            "detail": "실패 또는 취소된 작업도 상태 변경 없이 계속 표시됩니다.",
        },
    ]


def _build_publish_job_row(
    request: Request,
    publish_job_query_params: dict[str, str],
    row,
) -> dict[str, str]:
    return {
        "publish_job_label": f"발행 작업 {row.publish_job_id}",
        "detail_href": _append_query_params(
            str(request.url_for("console_publish_job_detail", publish_job_id=row.publish_job_id)),
            publish_job_query_params,
        ),
        "draft_label": f"초안 {row.draft_id}",
        "review_detail_href": _append_query_params(
            str(request.url_for("console_review_detail", draft_id=row.draft_id)),
            _extract_console_query_params(request),
        ),
        "variant_label": f"버전 {row.variant_index}",
        "brief_label": f"브리프 {row.brief_id}",
        "account_key": row.account_key,
        "channel": row.channel.upper(),
        "state": _humanize_label(row.state),
        "draft_state": _humanize_label(row.draft_state),
        "scheduled_for": _format_datetime(row.scheduled_for, none_label="예약되지 않음"),
        "published_at": _format_datetime(row.published_at, none_label="아직 발행되지 않음"),
        "created_at": _format_datetime(row.created_at, none_label="기록 없음"),
        "updated_at": _format_datetime(row.updated_at, none_label="기록 없음"),
        "attempt_count": str(row.attempt_count),
        "external_post_id": row.external_post_id or "아직 발행되지 않음",
        "last_error": row.last_error or "기록된 발행 오류가 없습니다.",
        "brief_title": row.brief_title,
        "source_title": row.source_title,
    }


def _build_publish_job_detail(
    request: Request,
    detail,
) -> dict[str, object]:
    job = detail.job
    draft = job.draft_variant
    content_brief = draft.content_brief
    source_item = content_brief.source_item
    review_detail_href = _append_query_params(
        str(request.url_for("console_review_detail", draft_id=draft.id)),
        _extract_console_query_params(request),
    )
    return {
        "job_label": f"발행 작업 {job.id}",
        "account_key": content_brief.account_key,
        "channel": job.channel.upper(),
        "state": _humanize_label(job.state.value),
        "scheduled_for": _format_datetime(job.scheduled_for, none_label="예약되지 않음"),
        "published_at": _format_datetime(job.published_at, none_label="아직 발행되지 않음"),
        "created_at": _format_datetime(job.created_at, none_label="기록 없음"),
        "updated_at": _format_datetime(job.updated_at, none_label="기록 없음"),
        "attempt_count": str(job.attempt_count),
        "external_post_id": job.external_post_id or "아직 발행되지 않음",
        "last_error": job.last_error or "기록된 발행 오류가 없습니다.",
        "review_detail_href": review_detail_href,
        "draft": {
            "draft_label": f"초안 {draft.id}",
            "variant_label": f"버전 {draft.variant_index}",
            "body": draft.body,
            "draft_state": _humanize_label(draft.state.value),
            "rejection_reason": draft.rejection_reason or "반려 사유 없음",
            "created_at": _format_datetime(draft.created_at, none_label="기록 없음"),
            "reviewed_at": _format_datetime(draft.reviewed_at, none_label="아직 검토되지 않음"),
        },
        "provenance": {
            "source_name": draft.source_name or "기록 없음",
            "source_url": draft.source_url,
            "article_url": draft.article_url,
            "source_published_at": _format_datetime(
                draft.source_published_at,
                none_label="기록 없음",
            ),
            "source_policy_mode": _humanize_label(
                draft.source_policy_mode.value if draft.source_policy_mode else None
            ),
        },
        "brief": {
            "brief_id": content_brief.id,
            "title": content_brief.title,
            "summary": content_brief.summary or "기록된 요약 없음",
            "key_points": list(content_brief.key_points),
            "landing_url": content_brief.landing_url,
            "tags": list(content_brief.tags),
            "angle": _humanize_label(content_brief.angle),
            "language": content_brief.language,
        },
        "source_item": {
            "source_item_id": source_item.id,
            "source_key": source_item.source_key,
            "external_id": source_item.external_id,
            "title": source_item.title,
            "summary": source_item.summary or "기록된 소스 요약 없음",
            "source_url": source_item.source_url,
            "canonical_url": source_item.canonical_url,
            "published_at": _format_datetime(source_item.published_at, none_label="기록 없음"),
            "policy_mode": _humanize_label(source_item.policy_mode.value),
            "require_attribution": "필수" if source_item.require_attribution else "불필요",
        },
        "publish_logs": [
            _build_publish_job_log_row(log)
            for log in detail.publish_logs
        ],
    }


def _build_manual_publish_action_form_state(
    request: Request,
    query_params: dict[str, str],
    detail,
    *,
    form_values: dict[str, str] | None,
) -> dict[str, str | bool]:
    job = detail.job
    values = form_values or {}
    is_manual_handoff = _is_manual_publish_handoff(job)
    show_actions = is_manual_handoff and job.state is PublishJobState.SCHEDULED

    if show_actions:
        state_hint = (
            "이 작업은 외부 플랫폼에 직접 올린 뒤 결과를 기록하는 수동 업로드 handoff입니다. "
            "업로드가 끝나면 완료, 실패, 취소 중 하나를 선택해 상태와 로그를 함께 남기세요."
        )
        read_only_notice = ""
    elif is_manual_handoff:
        state_hint = (
            "이 수동 업로드 handoff는 이미 종료 상태입니다. 아래 타임라인에서 최종 결과와 남겨진 메모를 확인할 수 있습니다."
        )
        read_only_notice = (
            "이 작업은 이미 종료되어 추가 브라우저 액션을 숨깁니다. 다시 게시가 필요하면 검토 흐름에서 새 handoff를 시작하세요."
        )
    else:
        state_hint = (
            "이 작업은 수동 업로드 handoff가 아니라 현재 화면에서는 결과 기록 폼을 제공하지 않습니다."
        )
        read_only_notice = (
            "현재 발행 작업은 수동 전달 기록 대상이 아닙니다. 스케줄러나 기존 발행 타임라인을 통해 상태를 확인하세요."
        )

    return {
        "action_href": _append_query_params(
            str(request.url_for("console_publish_job_detail_action", publish_job_id=job.id)),
            query_params,
        ),
        "operator": values.get("operator", ""),
        "external_post_id": values.get("external_post_id", ""),
        "error_message": values.get("error_message", ""),
        "cancel_reason": values.get("cancel_reason", ""),
        "show_manual_publish_actions": show_actions,
        "state_hint": state_hint,
        "read_only_notice": read_only_notice,
        "action_title": f"{_humanize_label(job.channel)} 수동 발행 기록",
    }


def _is_manual_publish_handoff(job) -> bool:
    return job.channel in _MANUAL_UPLOAD_CHANNELS and job.scheduled_for is None


def _build_publish_job_log_row(log) -> dict[str, str]:
    return {
        "log_label": f"로그 {log.id}",
        "event_type": _humanize_label(log.event_type),
        "message": log.message,
        "payload": _format_json_payload(log.payload),
        "created_at": _format_datetime(log.created_at, none_label="기록 없음"),
    }


def _build_pending_review_metrics(rows) -> list[dict[str, str]]:
    account_keys = sorted({row.account_key for row in rows})
    channels = sorted({row.channel.upper() for row in rows if row.channel})
    oldest_created = (
        min((row.created_at for row in rows), default=None)
    )
    return [
        {
            "label": "검토 대기 초안",
            "value": str(len(rows)),
            "detail": "운영자 결정이 아직 남아 있는 현재 수동 검토 항목입니다.",
        },
        {
            "label": "계정 경로",
            "value": str(len(account_keys)),
            "detail": _format_list(account_keys, fallback="대기 중인 계정 없음"),
        },
        {
            "label": "채널",
            "value": _format_list(channels, fallback="없음"),
            "detail": "현재 검토 대기열에 표시되는 채널 구성입니다.",
        },
        {
            "label": "가장 오래된 대기 항목",
            "value": _format_datetime(oldest_created, none_label="대기 항목 없음"),
            "detail": "브라우저 대기열에서 오래된 작업부터 우선 처리할 때 유용합니다.",
        },
    ]


def _build_pending_review_row(
    request: Request,
    query_params: dict[str, str],
    position: int,
    row,
) -> dict[str, str]:
    return {
        "queue_position": str(position),
        "draft_label": f"초안 {row.draft_id}",
        "variant_label": f"버전 {row.variant_index}",
        "account_key": row.account_key,
        "channel": row.channel.upper(),
        "created_at": _format_datetime(row.created_at, none_label="기록 없음"),
        "title": row.title,
        "body_preview": _truncate_text(row.body, limit=180),
        "detail_href": _append_query_params(
            str(request.url_for("console_review_detail", draft_id=row.draft_id)),
            query_params,
        ),
    }


def _build_review_detail(
    request: Request,
    query_params: dict[str, str],
    detail,
) -> dict[str, object]:
    draft = detail.draft
    content_brief = draft.content_brief
    source_item = content_brief.source_item
    article_enrichment = source_item.article_enrichment
    return {
        "draft_label": f"초안 {draft.id}",
        "channel": _humanize_label(draft.channel),
        "variant_label": f"버전 {draft.variant_index}",
        "account_key": content_brief.account_key,
        "draft_state": _humanize_label(draft.state.value),
        "rejection_reason": draft.rejection_reason or "반려 사유 없음",
        "created_at": _format_datetime(draft.created_at, none_label="기록 없음"),
        "reviewed_at": _format_datetime(draft.reviewed_at, none_label="아직 검토되지 않음"),
        "body": draft.body,
        "provenance": {
            "source_name": draft.source_name or "기록 없음",
            "source_url": draft.source_url,
            "article_url": draft.article_url,
            "source_published_at": _format_datetime(
                draft.source_published_at,
                none_label="기록 없음",
            ),
            "source_policy_mode": _humanize_label(
                draft.source_policy_mode.value if draft.source_policy_mode else None
            ),
        },
        "brief": {
            "brief_id": content_brief.id,
            "title": content_brief.title,
            "summary": content_brief.summary or "기록된 요약 없음",
            "key_points": list(content_brief.key_points),
            "landing_url": content_brief.landing_url,
            "tags": list(content_brief.tags),
            "angle": _humanize_label(content_brief.angle),
            "language": content_brief.language,
        },
        "source_item": {
            "source_item_id": source_item.id,
            "source_key": source_item.source_key,
            "external_id": source_item.external_id,
            "title": source_item.title,
            "summary": source_item.summary or "기록된 소스 요약 없음",
            "source_url": source_item.source_url,
            "canonical_url": source_item.canonical_url,
            "published_at": _format_datetime(source_item.published_at, none_label="기록 없음"),
            "policy_mode": _humanize_label(source_item.policy_mode.value),
            "require_attribution": "필수" if source_item.require_attribution else "불필요",
        },
        "article_enrichment": (
            {
                "article_enrichment_id": article_enrichment.id,
                "source_name": article_enrichment.source_name or "기록 없음",
                "article_url": article_enrichment.article_url,
                "published_at": _format_datetime(
                    article_enrichment.published_at,
                    none_label="기록 없음",
                ),
                "discovered_at": _format_datetime(
                    article_enrichment.discovered_at,
                    none_label="기록 없음",
                ),
                "regenerated_summary": (
                    article_enrichment.regenerated_summary
                    or "재생성된 요약 없음"
                ),
                "regenerated_key_points": list(article_enrichment.regenerated_key_points),
                "classification": _humanize_label(article_enrichment.classification),
            }
            if article_enrichment is not None
            else None
        ),
        "review_actions": [
            _build_review_action_row(
                request,
                query_params,
                action,
            )
            for action in detail.review_actions
        ],
        "sibling_variants": [
            _build_sibling_variant_row(request, query_params, variant)
            for variant in detail.sibling_variants
        ],
    }


def _build_review_action_row(
    request: Request,
    query_params: dict[str, str],
    action,
) -> dict[str, str | None]:
    return {
        "action_id": str(action.id),
        "action_type": _humanize_label(action.action_type.value),
        "reviewer": action.reviewer,
        "created_at": _format_datetime(action.created_at, none_label="기록 없음"),
        "before_text": action.before_text,
        "after_text": action.after_text,
        "draft_state_before": _humanize_label(action.draft_state_before.value),
        "draft_state_after": _humanize_label(action.draft_state_after.value),
        "rejection_reason": action.rejection_reason or "반려 사유 없음",
        "scheduled_for": _format_datetime(action.scheduled_for, none_label="예약되지 않음"),
        "publish_job_label": (
            f"발행 작업 {action.publish_job_id}"
            if action.publish_job_id
            else "생성되지 않음"
        ),
        "publish_job_href": (
            _append_query_params(
                str(
                    request.url_for(
                        "console_publish_job_detail",
                        publish_job_id=action.publish_job_id,
                    )
                ),
                query_params,
            )
            if action.publish_job_id
            else None
        ),
    }


def _build_review_action_form_state(
    request: Request,
    query_params: dict[str, str],
    detail,
    *,
    config_dir: str,
    form_values: dict[str, str] | None,
) -> dict[str, str | bool]:
    draft = detail.draft
    state_value = draft.state.value
    values = form_values or {}
    manual_upload = state_value == "approved" and _review_detail_requires_manual_upload_guidance(
        detail,
        config_dir=config_dir,
    )

    if state_value == "pending_review":
        state_hint = (
            "이 초안이 아직 수동 검토 단계에 있는 동안에는 승인, 반려, 수정 작업을 사용할 수 있습니다. "
            "예약은 승인 이후에만 열립니다."
        )
        read_only_notice = ""
        manual_upload_copy = ""
        manual_upload_helper = ""
    elif state_value == "approved":
        if manual_upload:
            state_hint = (
                "이미 승인이 기록되어 있습니다. 이 채널은 현재 브라우저 자동 업로드 대신 "
                "수동 업로드용 본문을 복사해 게시하는 흐름을 권장합니다."
            )
            manual_upload_copy = (
                f"{_humanize_label(draft.channel)} 게시창에 아래 본문을 그대로 붙여넣고, 업로드 후 외부 게시 링크를 운영 기록에 남기세요."
            )
            manual_upload_helper = (
                "현재 이 채널은 프로젝트 내 live publisher가 연결되어 있지 않아 예약 발행 버튼을 숨깁니다. "
                "본문 줄바꿈과 번호 구조를 유지한 채 수동 게시하는 것이 가장 안전합니다."
            )
        else:
            state_hint = (
                "이미 승인이 기록되어 있습니다. 공용 검토 워크플로에서 다음으로 가능한 작업은 예약입니다."
            )
            manual_upload_copy = ""
            manual_upload_helper = ""
        read_only_notice = ""
    else:
        state_hint = (
            "공용 검토 워크플로에서 이 상태를 읽기 전용으로 보기 때문에, 이 초안은 더 이상 브라우저에서 작업할 수 없습니다."
        )
        read_only_notice = (
            "이 초안의 현재 상태에서는 브라우저 작업을 수행할 수 없습니다. 아래 검토 이력에서 최종 결정을 확인하세요."
        )
        manual_upload_copy = ""
        manual_upload_helper = ""

    return {
        "action_href": _append_query_params(
            str(request.url_for("console_review_detail_action", draft_id=draft.id)),
            query_params,
        ),
        "reviewer": values.get("reviewer", ""),
        "reject_reason": values.get("reject_reason", ""),
        "edit_body": values.get("edit_body", draft.body),
        "scheduled_for": values.get("scheduled_for", ""),
        "show_pending_actions": state_value == "pending_review",
        "show_schedule_action": state_value == "approved" and not manual_upload,
        "show_manual_upload_guidance": manual_upload,
        "state_hint": state_hint,
        "read_only_notice": read_only_notice,
        "manual_upload_title": f"{_humanize_label(draft.channel)} 수동 업로드",
        "manual_upload_copy": manual_upload_copy,
        "manual_upload_helper": manual_upload_helper,
        "manual_upload_body": draft.body,
    }


def _review_detail_requires_manual_upload_guidance(
    detail,
    *,
    config_dir: str,
) -> bool:
    draft = detail.draft
    if draft.channel not in _MANUAL_UPLOAD_CHANNELS:
        return False
    if draft.channel == "linkedin":
        return True

    content_brief = draft.content_brief
    if content_brief is None:
        return True

    try:
        return channel_requires_manual_publish_handoff(
            config_dir=config_dir,
            account_key=content_brief.account_key,
            channel=draft.channel,
        )
    except (ConfigError, FileNotFoundError):
        return True


def _build_sibling_variant_row(
    request: Request,
    query_params: dict[str, str],
    draft,
) -> dict[str, str]:
    return {
        "draft_label": f"초안 {draft.id}",
        "detail_href": _append_query_params(
            str(request.url_for("console_review_detail", draft_id=draft.id)),
            query_params,
        ),
        "variant_label": f"버전 {draft.variant_index}",
        "draft_state": _humanize_label(draft.state.value),
        "rejection_reason": draft.rejection_reason or "반려 사유 없음",
        "created_at": _format_datetime(draft.created_at, none_label="기록 없음"),
        "reviewed_at": _format_datetime(draft.reviewed_at, none_label="아직 검토되지 않음"),
        "body": draft.body,
    }


def _extract_console_query_params(request: Request) -> dict[str, str]:
    return {
        key: value
        for key in _CONTEXT_QUERY_KEYS
        if (value := request.query_params.get(key))
    }


def _append_query_params(url: str, query_params: dict[str, str]) -> str:
    if not query_params:
        return url
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_params),
            parts.fragment,
        )
    )


def _format_datetime(value: datetime | None, *, none_label: str = "실행 중") -> str:
    if value is None:
        return none_label
    return value.isoformat()


def _humanize_label(value: str | None) -> str:
    if not value:
        return "기록 없음"
    normalized = value.strip()
    return _KOREAN_LABELS.get(
        normalized.casefold(),
        normalized.replace("_", " ").title(),
    )


def _format_policy_mode_counts(policy_mode_counts: dict[str, int]) -> str:
    if not policy_mode_counts:
        return "정책 모드 요약 없음"
    return " / ".join(
        f"{_humanize_label(mode)} {count}"
        for mode, count in sorted(policy_mode_counts.items())
    )


def _format_list(values, *, fallback: str) -> str:
    items = [str(value) for value in values if value]
    if not items:
        return fallback
    return ", ".join(items)


def _truncate_text(value: str, *, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _format_json_payload(payload: dict | None) -> str:
    if payload is None:
        return "기록된 페이로드 없음"
    return json.dumps(payload, sort_keys=True)
