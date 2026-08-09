"""Template view models for scheduler operations."""

from __future__ import annotations

from fastapi import Request

from app.api.console_view_common import (
    _append_query_params,
    _extract_console_query_params,
    _format_list,
    _humanize_label,
    _truncate_text,
)


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
