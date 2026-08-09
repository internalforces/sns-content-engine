"""Template view models for dashboard and article history."""

from __future__ import annotations

from app.api.console_view_common import (
    _format_datetime,
    _format_list,
    _format_policy_mode_counts,
    _humanize_label,
)


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
