"""Server-rendered operator console routes and assets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.workflows.review_queue import DraftNotFoundError

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_CONTEXT_QUERY_KEYS = ("config_dir", "database_url")
_DEFAULT_DASHBOARD_RUN_LIMIT = 6
_DEFAULT_DASHBOARD_FAILURE_LIMIT = 6
_DEFAULT_ARTICLE_LIMIT = 25

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
    """Render one review draft with provenance, audit history, and sibling variants."""

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
                "review_detail_missing": {
                    "message": str(exc),
                    "draft_id": draft_id,
                },
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
        page_description="Read-only draft workspace with provenance, brief, enrichment, audit trail, and sibling variants from the shared review detail helper.",
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
        }
    )
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/review_detail.html",
        context=context,
    )


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
            description="Planned browser visibility for publish history and queue state.",
            status="Task 06",
        ),
        ConsoleNavItem(
            label="Scheduler",
            description="Planned safe controls for discover, backfill, and dry-run publish operations.",
            status="Task 07",
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
            _build_review_action_row(action)
            for action in detail.review_actions
        ],
        "sibling_variants": [
            _build_sibling_variant_row(request, query_params, variant)
            for variant in detail.sibling_variants
        ],
    }


def _build_review_action_row(action) -> dict[str, str]:
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
        "publish_job_id": str(action.publish_job_id) if action.publish_job_id else "Not created",
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
