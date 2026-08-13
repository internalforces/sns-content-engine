"""Display models for the review-first console home."""

from __future__ import annotations

from datetime import datetime

from fastapi import Request

from app.api.console_view_common import _append_query_params, _humanize_label
from app.api.console_view_review import _build_pending_review_sensitivity


def _format_wait_duration(created_at: datetime, *, now: datetime) -> str:
    """Format a draft's queue time using concise operator-facing units."""

    minutes = max(0, int((now - created_at).total_seconds()) // 60)
    if minutes < 60:
        return f"{minutes}분"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}시간 {minutes % 60}분"
    return f"{hours // 24}일 {hours % 24}시간"


def _build_home_review_rows(
    request: Request,
    query_params: dict[str, str],
    rows,
    *,
    now: datetime,
    limit: int = 3,
) -> list[dict[str, str | bool]]:
    """Build the oldest pending drafts for the home review shortcut."""

    items: list[dict[str, str | bool]] = []
    for row in sorted(rows, key=lambda item: item.created_at)[:limit]:
        sensitivity = _build_pending_review_sensitivity(row)
        items.append(
            {
                "draft_id": str(row.draft_id),
                "title": row.title,
                "channel": _humanize_label(row.channel),
                "account_key": row.account_key,
                "review_flag": (
                    f"{_humanize_label(sensitivity.domain)} 추가 확인"
                    if sensitivity.is_high_risk
                    else "일반 검토"
                ),
                "needs_attention": sensitivity.is_high_risk,
                "wait_duration": _format_wait_duration(row.created_at, now=now),
                "detail_href": _append_query_params(
                    str(request.url_for("console_review_detail", draft_id=row.draft_id)),
                    query_params,
                ),
            }
        )
    return items


def _build_home_summary(rows, latest_run) -> list[dict[str, str]]:
    """Build the small set of review-first home summary values."""

    sensitive_count = sum(
        _build_pending_review_sensitivity(row).is_high_risk
        for row in rows
    )
    return [
        {"label": "검토 대기", "value": str(len(rows))},
        {"label": "추가 확인 필요", "value": str(sensitive_count)},
        {
            "label": "최근 파이프라인",
            "value": _humanize_label(latest_run.status) if latest_run else "이력 없음",
        },
    ]
