"""Template view models for the human review queue."""

from __future__ import annotations

from fastapi import Request

from app.api.console_constants import _MANUAL_UPLOAD_CHANNELS
from app.api.console_view_common import (
    _append_query_params,
    _format_datetime,
    _format_list,
    _humanize_label,
    _truncate_text,
)
from app.config import ConfigError
from app.connectors.publishers.resolver import channel_requires_manual_publish_handoff
from app.services.prompt_renderer import build_domain_sensitivity


def _build_pending_review_sensitivity(row):
    """Build the same brief-based sensitivity signal used by review detail."""

    return build_domain_sensitivity(
        title=row.title,
        summary=row.summary,
        tags=tuple(row.tags),
    )


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
) -> dict[str, str | bool]:
    sensitivity = _build_pending_review_sensitivity(row)
    return {
        "queue_position": str(position),
        "draft_label": f"초안 {row.draft_id}",
        "variant_label": f"버전 {row.variant_index}",
        "review_flag": (
            f"{_humanize_label(sensitivity.domain)} 추가 확인"
            if sensitivity.is_high_risk
            else "일반 검토"
        ),
        "needs_attention": sensitivity.is_high_risk,
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
    sensitivity = build_domain_sensitivity(
        title=content_brief.title,
        summary=content_brief.summary,
        tags=tuple(content_brief.tags),
    )
    return {
        "draft_label": f"초안 {draft.id}",
        "channel": _humanize_label(draft.channel),
        "variant_label": f"버전 {draft.variant_index}",
        "account_key": content_brief.account_key,
        "draft_state": _humanize_label(draft.state.value),
        "rejection_reason": draft.rejection_reason,
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
        "sensitivity": {
            "is_high_risk": sensitivity.is_high_risk,
            "domain": _humanize_label(sensitivity.domain),
            "matched_terms": list(sensitivity.matched_terms),
            "review_note": sensitivity.review_note,
            "prompt_guidance": sensitivity.prompt_guidance,
        },
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
        "rejection_reason": action.rejection_reason,
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
    if draft.channel in {"ghost", "linkedin"}:
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
) -> dict[str, str | None]:
    return {
        "draft_label": f"초안 {draft.id}",
        "detail_href": _append_query_params(
            str(request.url_for("console_review_detail", draft_id=draft.id)),
            query_params,
        ),
        "variant_label": f"버전 {draft.variant_index}",
        "draft_state": _humanize_label(draft.state.value),
        "rejection_reason": draft.rejection_reason,
        "created_at": _format_datetime(draft.created_at, none_label="기록 없음"),
        "reviewed_at": _format_datetime(draft.reviewed_at, none_label="아직 검토되지 않음"),
        "body": draft.body,
    }
