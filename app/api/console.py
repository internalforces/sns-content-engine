"""Server-rendered operator console routes and assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_CONTEXT_QUERY_KEYS = ("config_dir", "database_url")

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

    query_params = _extract_console_query_params(request)
    context = {
        "page_title": "Operator Console",
        "page_description": "Server-rendered browser shell for run visibility, review work, and safe operator actions.",
        "console_asset_css_url": str(request.url_for("console_static", path="/console.css")),
        "console_nav_items": _build_console_nav_items(request, query_params),
        "operator_context": {
            "config_dir": config_dir,
            "database_url": database_url,
        },
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
    return _TEMPLATES.TemplateResponse(
        request=request,
        name="console/index.html",
        context=context,
    )


def _build_console_nav_items(request: Request, query_params: dict[str, str]) -> list[ConsoleNavItem]:
    return [
        ConsoleNavItem(
            label="Console Home",
            description="Shared shell, operator context, and roadmap framing for the browser surface.",
            status="Ready",
            href=_append_query_params(str(request.url_for("console_home")), query_params),
            active=True,
        ),
        ConsoleNavItem(
            label="Runs & Failures",
            description="Next shell extension for recent pipeline activity and readable failure rows.",
            status="Task 02",
        ),
        ConsoleNavItem(
            label="Articles",
            description="Upcoming article status table that reuses existing history query helpers.",
            status="Task 03",
        ),
        ConsoleNavItem(
            label="Pending Review",
            description="Upcoming queue page for the current manual review workload.",
            status="Task 03",
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
