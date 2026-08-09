"""Shared navigation, query-string, and formatting helpers for console views."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import Request

from app.api.console_constants import _CONTEXT_QUERY_KEYS, _KOREAN_LABELS


@dataclass(frozen=True, slots=True)
class ConsoleNavItem:
    """Navigation metadata for the operator console shell."""

    label: str
    description: str
    status: str
    href: str | None = None
    active: bool = False


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
