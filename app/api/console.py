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
from app.config import ConfigError
from app.storage import DatabaseSchemaError, PublishJobState
from app.workflows.history_queries import PublishJobNotFoundError
from app.workflows.review_queue import (
    DraftNotFoundError,
    DraftReviewStateError,
    DraftScheduleError,
    DraftValidationFailedError,
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
        page_title="Operator Console",
        page_description="Server-rendered browser shell for run visibility, review work, and safe operator actions.",
        active_nav_key="home",
        config_dir=config_dir,
        database_url=database_url,
    )
    context.update(
        {
            "console_sections": [
                {
                    "title": "Read-only rollout",
                    "copy": "This first shell keeps the browser surface additive while Tasks 02 and 03 wire run, failure, article, and review queue data into the same layout.",
                },
                {
                    "title": "Safety model",
                    "copy": "Manual review stays required and publish-due remains dry-run first. The shell is only exposing operator visibility, not bypassing existing workflow gates.",
                },
                {
                    "title": "Implementation shape",
                    "copy": "FastAPI serves Jinja templates and lightweight static assets directly, so later console work can reuse the existing backend without a separate frontend build chain.",
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
        page_title="Run Dashboard",
        page_description="Recent pipeline activity, visible technical failures, and intentional policy skips from the shared operator history helpers.",
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
        page_title="Article Status",
        page_description="Recent stored source items and enrichment state pulled from the same helper that powers the operator article API.",
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
        page_title="Publish Jobs",
        page_description="Read-only publish queue and delivery visibility from the shared operator history helpers, without adding new browser mutation paths.",
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
    """Render one publish job with linked draft context and publish logs."""

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
            page_title="Publish Job Not Found",
            page_description="The requested publish job detail could not be loaded for this operator context.",
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
        page_title=f"Publish Job {publish_job_id}",
        page_description="Publish timeline, linked draft context, and stored log events from the same operator-ready history helpers used by the API.",
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
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/publish_job_detail.html",
        context=context,
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

    if action not in {"discover", "backfill", "publish_due"}:
        return _render_console_scheduler_page(
            request,
            config_dir=config_dir,
            database_url=database_url,
            status_code=422,
            feedback=_build_scheduler_action_feedback(
                kind="error",
                action_label="Scheduler action",
                message="Select one of the supported scheduler actions before submitting the form.",
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

    return _render_console_scheduler_page(
        request,
        config_dir=config_dir,
        database_url=database_url,
        feedback=_build_scheduler_action_success_feedback(
            action=action,
            result=result,
        ),
        action_result=_build_scheduler_action_result(
            action=action,
            result=result,
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
        page_title="Pending Review",
        page_description="Current manual-review workload from the shared review-queue helper, without changing approval or publish safety semantics.",
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
                action_label="Review action",
                message="Select one of the supported review actions before submitting the form.",
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
            page_title="Review Draft Not Found",
            page_description="The requested draft detail could not be loaded for this operator context.",
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
        page_title=f"Review Draft {detail.draft.id}",
        page_description="Draft workspace with provenance, audit history, and browser review actions that reuse the existing workflow validation and state guards.",
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


def _build_review_action_success_feedback(result) -> dict[str, str]:
    action_label = _humanize_label(result.action_type.value)
    messages = {
        "approve": "Draft approved. Scheduling is now available from this workspace.",
        "reject": "Draft rejected. The rejection reason is now part of the recorded audit trail.",
        "edit": "Draft body updated. The edit is now captured in the audit trail.",
        "schedule": (
            f"Draft scheduled for {_format_datetime(result.scheduled_for, none_label='Not scheduled')} "
            f"as publish job {result.publish_job_id}."
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
        "title": f"{action_label} {'saved' if kind == 'success' else 'blocked'}",
        "message": message,
    }


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
        page_title="Scheduler",
        page_description="Browser controls for discover, backfill, and publish-due execution that reuse the current scheduler wrappers and keep dry-run publish as the default path.",
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
            f"Discover completed with {result.discovered_count} discovered items across "
            f"{len(result.processed_sources)} configured sources."
        )
    elif action == "backfill":
        message = (
            f"Backfill checked {result.processed_channel_count} account routes and created "
            f"{result.created_count} publish jobs."
        )
    else:
        mode_label = "dry-run mode" if result.dry_run else "live publishing enabled"
        message = (
            f"Publish-due completed with {mode_label}. "
            f"Processed {result.processed_count} due jobs."
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
        "title": f"{action_label} {'saved' if kind == 'success' else 'blocked'}",
        "message": message,
    }


def _build_scheduler_action_result(
    *,
    action: str,
    result,
) -> dict[str, object]:
    if action == "discover":
        processed_sources = list(result.processed_sources)
        failure_messages = list(result.failure_messages)
        return {
            "kind": "discover",
            "title": "Discover summary",
            "badge": "Discover",
            "summary": (
                f"Discover checked {len(processed_sources)} configured sources and recorded "
                f"{result.discovered_count} discovered items."
            ),
            "metrics": [
                {"label": "Discovered items", "value": str(result.discovered_count)},
                {"label": "Sources processed", "value": str(len(processed_sources))},
                {"label": "Failures", "value": str(result.failure_count)},
            ],
            "processed_sources": processed_sources,
            "failure_messages": failure_messages,
        }

    if action == "backfill":
        return {
            "kind": "backfill",
            "title": "Backfill summary",
            "badge": "Backfill",
            "summary": (
                f"Backfill checked {result.processed_channel_count} account routes and created "
                f"{result.created_count} scheduled publish jobs."
            ),
            "metrics": [
                {"label": "Routes checked", "value": str(result.processed_channel_count)},
                {"label": "Jobs created", "value": str(result.created_count)},
                {"label": "Existing future jobs", "value": str(result.existing_count)},
                {"label": "Skipped slots", "value": str(result.skipped_count)},
            ],
            "outcomes": [_build_scheduler_backfill_outcome_row(outcome) for outcome in result.outcomes],
        }

    return {
        "kind": "publish_due",
        "title": "Publish-due summary",
        "badge": "Publish Due",
        "mode_label": "Dry run" if result.dry_run else "Live publish",
        "summary": (
            "Live publish ran because the explicit browser opt-in was selected."
            if not result.dry_run
            else "Dry run remained the default browser path, so no publish state changes were applied."
        ),
        "metrics": [
            {"label": "Due jobs processed", "value": str(result.processed_count)},
            {"label": "Published", "value": str(result.published_count)},
            {"label": "Failures", "value": str(result.failed_count)},
            {"label": "Dry-run only", "value": str(result.dry_run_count)},
            {"label": "Skipped", "value": str(result.skipped_count)},
        ],
        "outcomes": [_build_scheduler_publish_due_outcome_row(outcome) for outcome in result.outcomes],
    }


def _build_scheduler_backfill_outcome_row(outcome) -> dict[str, str]:
    return {
        "route_label": f"{outcome.account_key} / {outcome.channel.upper()}",
        "backlog_target": str(outcome.backlog_target),
        "existing_future_job_count": str(outcome.existing_future_job_count),
        "eligible_draft_count": str(outcome.eligible_draft_count),
        "planned_slot_count": str(outcome.planned_slot_count),
        "created_job_ids": _format_list(outcome.created_job_ids, fallback="None created"),
        "created_count": str(outcome.created_count),
        "skipped_slot_count": str(outcome.skipped_slot_count),
    }


def _build_scheduler_publish_due_outcome_row(outcome) -> dict[str, str]:
    return {
        "publish_job_label": f"Publish job {outcome.publish_job_id}",
        "status": _humanize_label(outcome.status),
        "state": _humanize_label(outcome.state.value),
        "message": outcome.message,
        "external_post_id": outcome.external_post_id or "No external post recorded.",
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
            label="Console Home",
            description="Shared shell, operator context, and roadmap framing for the browser surface.",
            status="Ready",
            href=_append_query_params(str(request.url_for("console_home")), query_params),
            active=active_nav_key == "home",
        ),
        ConsoleNavItem(
            label="Runs & Failures",
            description="Read-only dashboard for recent pipeline runs, technical failures, and intentional policy skips.",
            status="Ready",
            href=_append_query_params(str(request.url_for("console_dashboard")), query_params),
            active=active_nav_key == "dashboard",
        ),
        ConsoleNavItem(
            label="Articles",
            description="Read-only article status table backed by the shared operator article-status helper.",
            status="Ready",
            href=_append_query_params(str(request.url_for("console_articles")), query_params),
            active=active_nav_key == "articles",
        ),
        ConsoleNavItem(
            label="Pending Review",
            description="Current review queue and draft-detail workspace for manual review context.",
            status="Ready",
            href=_append_query_params(str(request.url_for("console_pending_review")), query_params),
            active=active_nav_key == "pending_review",
        ),
        ConsoleNavItem(
            label="Publish Jobs",
            description="Read-only publish queue, delivery state, and one-job timeline visibility.",
            status="Ready",
            href=_append_query_params(str(request.url_for("console_publish_jobs")), query_params),
            active=active_nav_key == "publish_jobs",
        ),
        ConsoleNavItem(
            label="Scheduler",
            description="Safe browser controls for discover, backfill, and dry-run-first publish execution.",
            status="Ready",
            href=_append_query_params(str(request.url_for("console_scheduler")), query_params),
            active=active_nav_key == "scheduler",
        ),
    ]


def _build_dashboard_metrics(runs_result, failures_result) -> list[dict[str, str]]:
    latest_run = runs_result.runs[0] if runs_result.runs else None
    latest_status = _humanize_label(latest_run.status) if latest_run else "No runs yet"
    latest_detail = (
        f"{latest_run.workflow_name} / {_format_datetime(latest_run.started_at)}"
        if latest_run
        else "The dashboard will populate after the next stored pipeline run."
    )
    return [
        {
            "label": "Latest run",
            "value": latest_status,
            "detail": latest_detail,
        },
        {
            "label": "Recent runs",
            "value": str(len(runs_result.runs)),
            "detail": "Visible from the shared pipeline run history helper.",
        },
        {
            "label": "Technical failures",
            "value": str(len(failures_result.failures)),
            "detail": "Unreadable or blocked content fetch/extract failures.",
        },
        {
            "label": "Policy skips",
            "value": str(len(failures_result.policy_skips)),
            "detail": "Intentional policy constraints recorded separately from failures.",
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
            {"label": "Discovered", "value": str(run.discovered_count)},
            {"label": "Saved", "value": str(run.saved_count)},
            {"label": "Enriched", "value": str(run.enriched_count)},
            {"label": "Briefs", "value": str(run.brief_count)},
            {"label": "Drafts", "value": str(run.draft_count)},
            {"label": "Failures", "value": str(run.failure_count)},
        ],
        "policy_summary": _format_policy_mode_counts(run.policy_mode_counts),
        "policy_guardrails": (
            f"Policy skips {run.policy_skipped_count} / Attribution required {run.attribution_required_count}"
        ),
        "rewrite_providers": _format_list(run.rewrite_providers, fallback="Not recorded"),
        "latest_error_code": run.latest_error_code or "None",
    }


def _build_dashboard_run_row(row) -> dict[str, str]:
    return {
        "workflow_name": row.workflow_name,
        "status": _humanize_label(row.status),
        "trigger_mode": _humanize_label(row.trigger_mode),
        "started_at": _format_datetime(row.started_at),
        "completed_at": _format_datetime(row.completed_at),
        "counts_summary": (
            f"Discovered {row.discovered_count} / Saved {row.saved_count} / "
            f"Enriched {row.enriched_count} / Briefs {row.brief_count} / "
            f"Drafts {row.draft_count} / Failures {row.failure_count}"
        ),
        "policy_summary": _format_policy_mode_counts(row.policy_mode_counts),
        "policy_guardrails": (
            f"Policy skips {row.policy_skipped_count} / Attribution required {row.attribution_required_count}"
        ),
        "rewrite_providers": _format_list(row.rewrite_providers, fallback="Not recorded"),
        "latest_error_code": row.latest_error_code or "None",
    }


def _build_dashboard_failure_row(row) -> dict[str, str]:
    return {
        "title": row.title,
        "source_name": row.source_name or "Unknown source",
        "article_url": row.article_url,
        "failure_code": row.failure_code,
        "failure_stage": _humanize_label(row.failure_stage),
        "failure_message": row.failure_message,
        "policy_mode": _humanize_label(row.source_policy_mode),
        "require_attribution": "Required" if row.require_attribution else "Not required",
        "updated_at": _format_datetime(row.updated_at),
    }


def _build_dashboard_policy_skip_row(row) -> dict[str, str]:
    return {
        "title": row.title,
        "source_name": row.source_name or "Unknown source",
        "article_url": row.article_url,
        "skipped_stage": _humanize_label(row.skipped_stage),
        "policy_decision_reason": row.policy_decision_reason,
        "policy_mode": _humanize_label(row.source_policy_mode),
        "require_attribution": "Required" if row.require_attribution else "Not required",
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
        _format_datetime(rows[0].discovered_at, none_label="Not recorded")
        if rows
        else "Waiting for stored discovery rows"
    )
    return [
        {
            "label": "Visible rows",
            "value": str(len(rows)),
            "detail": "Recent stored source items in table order for this operator context.",
        },
        {
            "label": "Pending or active",
            "value": str(pending_or_active),
            "detail": f"Latest discovery timestamp {latest_discovered}",
        },
        {
            "label": "Enriched",
            "value": str(enriched),
            "detail": "Rows that completed summary regeneration successfully.",
        },
        {
            "label": "Needs attention",
            "value": str(needs_attention),
            "detail": "Failed or policy-skipped rows remain visible without changing workflow state.",
        },
    ]


def _build_article_row(row) -> dict[str, str | None]:
    return {
        "source_name": row.source_name,
        "source_item_label": f"Source item {row.source_item_id}",
        "article_enrichment_label": (
            f"Enrichment {row.article_enrichment_id}"
            if row.article_enrichment_id is not None
            else "Enrichment not created yet"
        ),
        "title": row.title,
        "original_url": row.original_url,
        "article_url": row.article_url,
        "published_at": _format_datetime(row.published_at, none_label="Not recorded"),
        "discovered_at": _format_datetime(row.discovered_at, none_label="Not recorded"),
        "enrichment_state": _humanize_label(row.enrichment_state),
        "stage_summary": (
            f"Fetch {_humanize_label(row.fetch_status)} / "
            f"Extract {_humanize_label(row.extract_status)} / "
            f"Summarize {_humanize_label(row.summarize_status)}"
        ),
        "last_failure_message": row.last_failure_message or "No readable failure recorded.",
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
        "state": _humanize_label(state.value if state is not None else None),
        "account_key": normalized_account_key or "All accounts",
        "channel": normalized_channel.upper() if normalized_channel else "All channels",
        "limit": str(limit),
    }


def _build_publish_job_metrics(rows) -> list[dict[str, str]]:
    active_jobs = sum(1 for row in rows if row.state in {"scheduled", "publishing"})
    published_jobs = sum(1 for row in rows if row.state == "published")
    needs_attention = sum(1 for row in rows if row.state in {"failed", "cancelled"})
    account_keys = sorted({row.account_key for row in rows})
    return [
        {
            "label": "Visible jobs",
            "value": str(len(rows)),
            "detail": "Recent publish rows returned by the shared operator list helper.",
        },
        {
            "label": "Active queue",
            "value": str(active_jobs),
            "detail": "Scheduled or publishing jobs still ahead of delivery.",
        },
        {
            "label": "Published",
            "value": str(published_jobs),
            "detail": "Jobs that already reached a completed external publish state.",
        },
        {
            "label": "Accounts visible",
            "value": str(len(account_keys)),
            "detail": _format_list(account_keys, fallback="No accounts visible"),
        },
        {
            "label": "Needs attention",
            "value": str(needs_attention),
            "detail": "Failed or cancelled jobs remain visible without changing state.",
        },
    ]


def _build_publish_job_row(
    request: Request,
    publish_job_query_params: dict[str, str],
    row,
) -> dict[str, str]:
    return {
        "publish_job_label": f"Publish job {row.publish_job_id}",
        "detail_href": _append_query_params(
            str(request.url_for("console_publish_job_detail", publish_job_id=row.publish_job_id)),
            publish_job_query_params,
        ),
        "draft_label": f"Draft {row.draft_id}",
        "review_detail_href": _append_query_params(
            str(request.url_for("console_review_detail", draft_id=row.draft_id)),
            _extract_console_query_params(request),
        ),
        "variant_label": f"Variant {row.variant_index}",
        "brief_label": f"Brief {row.brief_id}",
        "account_key": row.account_key,
        "channel": row.channel.upper(),
        "state": _humanize_label(row.state),
        "draft_state": _humanize_label(row.draft_state),
        "scheduled_for": _format_datetime(row.scheduled_for, none_label="Not scheduled"),
        "published_at": _format_datetime(row.published_at, none_label="Not published yet"),
        "created_at": _format_datetime(row.created_at, none_label="Not recorded"),
        "updated_at": _format_datetime(row.updated_at, none_label="Not recorded"),
        "attempt_count": str(row.attempt_count),
        "external_post_id": row.external_post_id or "Not published yet",
        "last_error": row.last_error or "No publish error recorded.",
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
        "job_label": f"Publish job {job.id}",
        "account_key": content_brief.account_key,
        "channel": job.channel.upper(),
        "state": _humanize_label(job.state.value),
        "scheduled_for": _format_datetime(job.scheduled_for, none_label="Not scheduled"),
        "published_at": _format_datetime(job.published_at, none_label="Not published yet"),
        "created_at": _format_datetime(job.created_at, none_label="Not recorded"),
        "updated_at": _format_datetime(job.updated_at, none_label="Not recorded"),
        "attempt_count": str(job.attempt_count),
        "external_post_id": job.external_post_id or "Not published yet",
        "last_error": job.last_error or "No publish error recorded.",
        "review_detail_href": review_detail_href,
        "draft": {
            "draft_label": f"Draft {draft.id}",
            "variant_label": f"Variant {draft.variant_index}",
            "body": draft.body,
            "draft_state": _humanize_label(draft.state.value),
            "rejection_reason": draft.rejection_reason or "No rejection recorded.",
            "created_at": _format_datetime(draft.created_at, none_label="Not recorded"),
            "reviewed_at": _format_datetime(draft.reviewed_at, none_label="Not reviewed yet"),
        },
        "provenance": {
            "source_name": draft.source_name or "Not recorded",
            "source_url": draft.source_url,
            "article_url": draft.article_url,
            "source_published_at": _format_datetime(
                draft.source_published_at,
                none_label="Not recorded",
            ),
            "source_policy_mode": _humanize_label(
                draft.source_policy_mode.value if draft.source_policy_mode else None
            ),
        },
        "brief": {
            "brief_id": content_brief.id,
            "title": content_brief.title,
            "summary": content_brief.summary or "No summary recorded.",
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
            "summary": source_item.summary or "No source summary recorded.",
            "source_url": source_item.source_url,
            "canonical_url": source_item.canonical_url,
            "published_at": _format_datetime(source_item.published_at, none_label="Not recorded"),
            "policy_mode": _humanize_label(source_item.policy_mode.value),
            "require_attribution": "Required" if source_item.require_attribution else "Not required",
        },
        "publish_logs": [
            _build_publish_job_log_row(log)
            for log in detail.publish_logs
        ],
    }


def _build_publish_job_log_row(log) -> dict[str, str]:
    return {
        "log_label": f"Log {log.id}",
        "event_type": _humanize_label(log.event_type),
        "message": log.message,
        "payload": _format_json_payload(log.payload),
        "created_at": _format_datetime(log.created_at, none_label="Not recorded"),
    }


def _build_pending_review_metrics(rows) -> list[dict[str, str]]:
    account_keys = sorted({row.account_key for row in rows})
    channels = sorted({row.channel.upper() for row in rows if row.channel})
    oldest_created = (
        min((row.created_at for row in rows), default=None)
    )
    return [
        {
            "label": "Pending drafts",
            "value": str(len(rows)),
            "detail": "Current manual-review items still waiting for an operator decision.",
        },
        {
            "label": "Account routes",
            "value": str(len(account_keys)),
            "detail": _format_list(account_keys, fallback="No accounts waiting"),
        },
        {
            "label": "Channels",
            "value": _format_list(channels, fallback="None"),
            "detail": "Channel mix currently visible in the review queue.",
        },
        {
            "label": "Oldest queued",
            "value": _format_datetime(oldest_created, none_label="Nothing queued"),
            "detail": "Useful when the browser queue is triaging stale work first.",
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
        "draft_label": f"Draft {row.draft_id}",
        "variant_label": f"Variant {row.variant_index}",
        "account_key": row.account_key,
        "channel": row.channel.upper(),
        "created_at": _format_datetime(row.created_at, none_label="Not recorded"),
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
        "draft_label": f"Draft {draft.id}",
        "channel": _humanize_label(draft.channel),
        "variant_label": f"Variant {draft.variant_index}",
        "account_key": content_brief.account_key,
        "draft_state": _humanize_label(draft.state.value),
        "rejection_reason": draft.rejection_reason or "No rejection recorded.",
        "created_at": _format_datetime(draft.created_at, none_label="Not recorded"),
        "reviewed_at": _format_datetime(draft.reviewed_at, none_label="Not reviewed yet"),
        "body": draft.body,
        "provenance": {
            "source_name": draft.source_name or "Not recorded",
            "source_url": draft.source_url,
            "article_url": draft.article_url,
            "source_published_at": _format_datetime(
                draft.source_published_at,
                none_label="Not recorded",
            ),
            "source_policy_mode": _humanize_label(
                draft.source_policy_mode.value if draft.source_policy_mode else None
            ),
        },
        "brief": {
            "brief_id": content_brief.id,
            "title": content_brief.title,
            "summary": content_brief.summary or "No summary recorded.",
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
            "summary": source_item.summary or "No source summary recorded.",
            "source_url": source_item.source_url,
            "canonical_url": source_item.canonical_url,
            "published_at": _format_datetime(source_item.published_at, none_label="Not recorded"),
            "policy_mode": _humanize_label(source_item.policy_mode.value),
            "require_attribution": "Required" if source_item.require_attribution else "Not required",
        },
        "article_enrichment": (
            {
                "article_enrichment_id": article_enrichment.id,
                "source_name": article_enrichment.source_name or "Not recorded",
                "article_url": article_enrichment.article_url,
                "published_at": _format_datetime(
                    article_enrichment.published_at,
                    none_label="Not recorded",
                ),
                "discovered_at": _format_datetime(
                    article_enrichment.discovered_at,
                    none_label="Not recorded",
                ),
                "regenerated_summary": (
                    article_enrichment.regenerated_summary
                    or "No regenerated summary recorded."
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
        "created_at": _format_datetime(action.created_at, none_label="Not recorded"),
        "before_text": action.before_text,
        "after_text": action.after_text,
        "draft_state_before": _humanize_label(action.draft_state_before.value),
        "draft_state_after": _humanize_label(action.draft_state_after.value),
        "rejection_reason": action.rejection_reason or "No rejection recorded.",
        "scheduled_for": _format_datetime(action.scheduled_for, none_label="Not scheduled"),
        "publish_job_label": (
            f"Publish job {action.publish_job_id}"
            if action.publish_job_id
            else "Not created"
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
    form_values: dict[str, str] | None,
) -> dict[str, str | bool]:
    draft = detail.draft
    state_value = draft.state.value
    values = form_values or {}

    if state_value == "pending_review":
        state_hint = (
            "Approve, reject, and edit remain available while this draft is still in manual review. "
            "Scheduling unlocks only after approval."
        )
        read_only_notice = ""
    elif state_value == "approved":
        state_hint = (
            "Approval is already recorded. Scheduling is the next allowed action in the shared review workflow."
        )
        read_only_notice = ""
    else:
        state_hint = (
            "This draft is no longer actionable in the browser because the shared review workflow marks this state read-only."
        )
        read_only_notice = (
            "No browser actions are available for this draft's current state. Use the audit trail below to confirm the final decision."
        )

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
        "show_schedule_action": state_value == "approved",
        "state_hint": state_hint,
        "read_only_notice": read_only_notice,
    }


def _build_sibling_variant_row(
    request: Request,
    query_params: dict[str, str],
    draft,
) -> dict[str, str]:
    return {
        "draft_label": f"Draft {draft.id}",
        "detail_href": _append_query_params(
            str(request.url_for("console_review_detail", draft_id=draft.id)),
            query_params,
        ),
        "variant_label": f"Variant {draft.variant_index}",
        "draft_state": _humanize_label(draft.state.value),
        "rejection_reason": draft.rejection_reason or "No rejection recorded.",
        "created_at": _format_datetime(draft.created_at, none_label="Not recorded"),
        "reviewed_at": _format_datetime(draft.reviewed_at, none_label="Not reviewed yet"),
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


def _format_datetime(value: datetime | None, *, none_label: str = "Still running") -> str:
    if value is None:
        return none_label
    return value.isoformat()


def _humanize_label(value: str | None) -> str:
    if not value:
        return "Not recorded"
    return value.replace("_", " ").title()


def _format_policy_mode_counts(policy_mode_counts: dict[str, int]) -> str:
    if not policy_mode_counts:
        return "No policy-mode summary"
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
        return "No payload recorded."
    return json.dumps(payload, sort_keys=True)
