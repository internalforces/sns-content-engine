"""Template view models for publish jobs and manual handoffs."""

from __future__ import annotations

from fastapi import Request

from app.api.console_constants import _DEFAULT_PUBLISH_JOB_LIMIT, _MANUAL_UPLOAD_CHANNELS
from app.api.console_view_common import (
    _append_query_params,
    _extract_console_query_params,
    _format_datetime,
    _format_json_payload,
    _format_list,
    _humanize_label,
)
from app.storage import PublishJobState


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
