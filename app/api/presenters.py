"""Translate workflow and storage results into public API responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from app.api.schemas import (
    ApiErrorResponse,
    ArticleStatusResponse,
    ManualPublishOutcomeResponse,
    PendingReviewDraftResponse,
    PipelineFailureResponse,
    PipelinePolicySkipResponse,
    PipelineRunResponse,
    PublishJobDetailResponse,
    PublishJobDraftResponse,
    PublishJobLogEntryResponse,
    PublishJobRowResponse,
    ReviewActionResponse,
    ReviewDraftArticleEnrichmentResponse,
    ReviewDraftAuditEntryResponse,
    ReviewDraftBriefResponse,
    ReviewDraftDetailResponse,
    ReviewDraftProvenanceResponse,
    ReviewDraftSensitivityResponse,
    ReviewDraftSiblingVariantResponse,
    ReviewDraftSourceItemResponse,
    SchedulerBackfillChannelResponse,
    SchedulerBackfillResponse,
    SchedulerDiscoverResponse,
    SchedulerPublishDueOutcomeResponse,
    SchedulerPublishDueResponse,
)
from app.services.prompt_renderer import build_domain_sensitivity

if TYPE_CHECKING:
    from app.scheduler import (
        BackfillChannelResult,
        BackfillResult,
        PublishDueOutcome,
        PublishDueResult,
        SchedulerDiscoverResult,
    )
    from app.storage import DraftVariant, ReviewAction
    from app.workflows.history_queries import (
        ArticleStatusRow,
        PipelineFailureRow,
        PipelinePolicySkipRow,
        PipelineRunHistoryRow,
        PublishJobDetailResult,
        PublishJobListRow,
    )
    from app.workflows.review_queue import (
        ManualPublishOutcomeResult,
        PendingReviewDraft,
        ReviewDraftResult,
    )

def _build_run_response(row: PipelineRunHistoryRow) -> PipelineRunResponse:
    return PipelineRunResponse(
        run_id=row.run_id,
        workflow_name=row.workflow_name,
        status=row.status,
        trigger_mode=row.trigger_mode,
        started_at=row.started_at.isoformat(),
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        discovered_count=row.discovered_count,
        saved_count=row.saved_count,
        enriched_count=row.enriched_count,
        brief_count=row.brief_count,
        draft_count=row.draft_count,
        failure_count=row.failure_count,
        latest_error_code=row.latest_error_code,
        policy_mode_counts=dict(row.policy_mode_counts),
        policy_skipped_count=row.policy_skipped_count,
        attribution_required_count=row.attribution_required_count,
        rewrite_providers=list(row.rewrite_providers),
    )


def _build_failure_response(row: PipelineFailureRow) -> PipelineFailureResponse:
    return PipelineFailureResponse(
        source_item_id=row.source_item_id,
        article_enrichment_id=row.article_enrichment_id,
        title=row.title,
        source_name=row.source_name,
        article_url=row.article_url,
        source_policy_mode=row.source_policy_mode,
        require_attribution=row.require_attribution,
        failure_stage=row.failure_stage,
        failure_code=row.failure_code,
        failure_message=row.failure_message,
        updated_at=row.updated_at.isoformat(),
    )


def _build_policy_skip_response(row: PipelinePolicySkipRow) -> PipelinePolicySkipResponse:
    return PipelinePolicySkipResponse(
        source_item_id=row.source_item_id,
        article_enrichment_id=row.article_enrichment_id,
        title=row.title,
        source_name=row.source_name,
        article_url=row.article_url,
        source_policy_mode=row.source_policy_mode,
        require_attribution=row.require_attribution,
        skipped_stage=row.skipped_stage,
        policy_decision_reason=row.policy_decision_reason,
        updated_at=row.updated_at.isoformat(),
    )


def _build_article_status_response(row: ArticleStatusRow) -> ArticleStatusResponse:
    return ArticleStatusResponse(
        source_item_id=row.source_item_id,
        article_enrichment_id=row.article_enrichment_id,
        source_name=row.source_name,
        title=row.title,
        original_url=row.original_url,
        article_url=row.article_url,
        published_at=row.published_at.isoformat() if row.published_at else None,
        discovered_at=row.discovered_at.isoformat(),
        enrichment_state=row.enrichment_state,
        fetch_status=row.fetch_status,
        extract_status=row.extract_status,
        summarize_status=row.summarize_status,
        last_failure_message=row.last_failure_message,
    )


def _build_publish_job_response(row: PublishJobListRow) -> PublishJobRowResponse:
    return PublishJobRowResponse(
        publish_job_id=row.publish_job_id,
        draft_id=row.draft_id,
        brief_id=row.brief_id,
        account_key=row.account_key,
        channel=row.channel,
        state=row.state,
        scheduled_for=row.scheduled_for.isoformat() if row.scheduled_for else None,
        published_at=row.published_at.isoformat() if row.published_at else None,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        attempt_count=row.attempt_count,
        external_post_id=row.external_post_id,
        last_error=row.last_error,
        variant_index=row.variant_index,
        draft_state=row.draft_state,
        brief_title=row.brief_title,
        source_title=row.source_title,
    )


def _build_publish_job_detail_response(detail: PublishJobDetailResult) -> PublishJobDetailResponse:
    job = detail.job
    draft = job.draft_variant
    content_brief = draft.content_brief
    source_item = content_brief.source_item
    return PublishJobDetailResponse(
        publish_job_id=job.id,
        account_key=content_brief.account_key,
        channel=job.channel,
        state=job.state.value,
        scheduled_for=job.scheduled_for.isoformat() if job.scheduled_for else None,
        published_at=job.published_at.isoformat() if job.published_at else None,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        attempt_count=job.attempt_count,
        external_post_id=job.external_post_id,
        last_error=job.last_error,
        draft=PublishJobDraftResponse(
            draft_id=draft.id,
            variant_index=draft.variant_index,
            body=draft.body,
            draft_state=draft.state.value,
            rejection_reason=draft.rejection_reason,
            created_at=draft.created_at.isoformat(),
            reviewed_at=draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        ),
        provenance=ReviewDraftProvenanceResponse(
            source_name=draft.source_name,
            source_url=draft.source_url,
            article_url=draft.article_url,
            source_published_at=draft.source_published_at.isoformat()
            if draft.source_published_at
            else None,
            source_policy_mode=draft.source_policy_mode.value if draft.source_policy_mode else None,
        ),
        brief=ReviewDraftBriefResponse(
            brief_id=content_brief.id,
            title=content_brief.title,
            summary=content_brief.summary,
            key_points=list(content_brief.key_points),
            landing_url=content_brief.landing_url,
            tags=list(content_brief.tags),
            angle=content_brief.angle,
            language=content_brief.language,
        ),
        source_item=ReviewDraftSourceItemResponse(
            source_item_id=source_item.id,
            source_key=source_item.source_key,
            external_id=source_item.external_id,
            title=source_item.title,
            summary=source_item.summary,
            source_url=source_item.source_url,
            canonical_url=source_item.canonical_url,
            published_at=source_item.published_at.isoformat() if source_item.published_at else None,
            policy_mode=source_item.policy_mode.value,
            require_attribution=source_item.require_attribution,
        ),
        publish_logs=[_build_publish_job_log_entry_response(log) for log in detail.publish_logs],
    )


def _build_publish_job_log_entry_response(log) -> PublishJobLogEntryResponse:
    return PublishJobLogEntryResponse(
        log_id=log.id,
        event_type=log.event_type,
        message=log.message,
        payload=log.payload,
        created_at=log.created_at.isoformat(),
    )


def _build_manual_publish_outcome_response(
    result: ManualPublishOutcomeResult,
) -> ManualPublishOutcomeResponse:
    return ManualPublishOutcomeResponse(
        publish_job_id=result.publish_job_id,
        channel=result.channel,
        operator=result.operator,
        previous_state=result.previous_state.value,
        publish_job_state=result.publish_job_state.value,
        external_post_id=result.external_post_id,
        last_error=result.last_error,
        published_at=result.published_at.isoformat() if result.published_at else None,
    )


def _build_scheduler_discover_response(result: SchedulerDiscoverResult) -> SchedulerDiscoverResponse:
    return SchedulerDiscoverResponse(
        discovered_count=result.discovered_count,
        processed_sources=list(result.processed_sources),
        failure_count=result.failure_count,
        failure_messages=list(result.failure_messages),
    )


def _build_scheduler_backfill_response(result: BackfillResult) -> SchedulerBackfillResponse:
    return SchedulerBackfillResponse(
        processed_channel_count=result.processed_channel_count,
        created_count=result.created_count,
        existing_count=result.existing_count,
        skipped_count=result.skipped_count,
        outcomes=[_build_scheduler_backfill_channel_response(outcome) for outcome in result.outcomes],
    )


def _build_scheduler_backfill_channel_response(
    outcome: BackfillChannelResult,
) -> SchedulerBackfillChannelResponse:
    return SchedulerBackfillChannelResponse(
        account_key=outcome.account_key,
        channel=outcome.channel,
        backlog_target=outcome.backlog_target,
        existing_future_job_count=outcome.existing_future_job_count,
        eligible_draft_count=outcome.eligible_draft_count,
        planned_slot_count=outcome.planned_slot_count,
        created_job_ids=list(outcome.created_job_ids),
        created_count=outcome.created_count,
        skipped_slot_count=outcome.skipped_slot_count,
    )


def _build_scheduler_publish_due_response(result: PublishDueResult) -> SchedulerPublishDueResponse:
    return SchedulerPublishDueResponse(
        dry_run=result.dry_run,
        processed_count=result.processed_count,
        published_count=result.published_count,
        failed_count=result.failed_count,
        dry_run_count=result.dry_run_count,
        skipped_count=result.skipped_count,
        outcomes=[_build_scheduler_publish_due_outcome_response(outcome) for outcome in result.outcomes],
    )


def _build_scheduler_publish_due_outcome_response(
    outcome: PublishDueOutcome,
) -> SchedulerPublishDueOutcomeResponse:
    return SchedulerPublishDueOutcomeResponse(
        publish_job_id=outcome.publish_job_id,
        status=outcome.status,
        state=outcome.state.value,
        message=outcome.message,
        external_post_id=outcome.external_post_id,
    )


def _build_pending_review_draft_response(row: PendingReviewDraft) -> PendingReviewDraftResponse:
    return PendingReviewDraftResponse(
        draft_id=row.draft_id,
        account_key=row.account_key,
        channel=row.channel,
        variant_index=row.variant_index,
        created_at=row.created_at.isoformat(),
        title=row.title,
        body=row.body,
    )


def _build_review_draft_detail_response(detail) -> ReviewDraftDetailResponse:
    draft = detail.draft
    content_brief = draft.content_brief
    source_item = content_brief.source_item
    article_enrichment = source_item.article_enrichment
    return ReviewDraftDetailResponse(
        draft_id=draft.id,
        account_key=content_brief.account_key,
        channel=draft.channel,
        variant_index=draft.variant_index,
        body=draft.body,
        draft_state=draft.state.value,
        rejection_reason=draft.rejection_reason,
        created_at=draft.created_at.isoformat(),
        reviewed_at=draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        provenance=ReviewDraftProvenanceResponse(
            source_name=draft.source_name,
            source_url=draft.source_url,
            article_url=draft.article_url,
            source_published_at=draft.source_published_at.isoformat()
            if draft.source_published_at
            else None,
            source_policy_mode=draft.source_policy_mode.value if draft.source_policy_mode else None,
        ),
        brief=ReviewDraftBriefResponse(
            brief_id=content_brief.id,
            title=content_brief.title,
            summary=content_brief.summary,
            key_points=list(content_brief.key_points),
            landing_url=content_brief.landing_url,
            tags=list(content_brief.tags),
            angle=content_brief.angle,
            language=content_brief.language,
        ),
        source_item=ReviewDraftSourceItemResponse(
            source_item_id=source_item.id,
            source_key=source_item.source_key,
            external_id=source_item.external_id,
            title=source_item.title,
            summary=source_item.summary,
            source_url=source_item.source_url,
            canonical_url=source_item.canonical_url,
            published_at=source_item.published_at.isoformat() if source_item.published_at else None,
            policy_mode=source_item.policy_mode.value,
            require_attribution=source_item.require_attribution,
        ),
        article_enrichment=_build_review_draft_article_enrichment_response(article_enrichment)
        if article_enrichment
        else None,
        sensitivity=_build_review_draft_sensitivity_response(content_brief),
        review_actions=[_build_review_draft_audit_entry_response(action) for action in detail.review_actions],
        sibling_variants=[
            _build_review_draft_sibling_variant_response(variant) for variant in detail.sibling_variants
        ],
    )


def _build_review_draft_sensitivity_response(content_brief) -> ReviewDraftSensitivityResponse:
    sensitivity = build_domain_sensitivity(
        title=content_brief.title,
        summary=content_brief.summary,
        tags=tuple(content_brief.tags),
    )
    return ReviewDraftSensitivityResponse(
        is_high_risk=sensitivity.is_high_risk,
        domain=sensitivity.domain,
        matched_terms=list(sensitivity.matched_terms),
        review_note=sensitivity.review_note,
        prompt_guidance=sensitivity.prompt_guidance,
    )


def _build_review_draft_article_enrichment_response(
    article_enrichment,
) -> ReviewDraftArticleEnrichmentResponse:
    return ReviewDraftArticleEnrichmentResponse(
        article_enrichment_id=article_enrichment.id,
        source_name=article_enrichment.source_name,
        article_url=article_enrichment.article_url,
        published_at=article_enrichment.published_at.isoformat()
        if article_enrichment.published_at
        else None,
        discovered_at=article_enrichment.discovered_at.isoformat(),
        regenerated_summary=article_enrichment.regenerated_summary,
        regenerated_key_points=list(article_enrichment.regenerated_key_points),
        classification=article_enrichment.classification,
    )


def _build_review_draft_audit_entry_response(action: ReviewAction) -> ReviewDraftAuditEntryResponse:
    return ReviewDraftAuditEntryResponse(
        action_id=action.id,
        action_type=action.action_type.value,
        reviewer=action.reviewer,
        created_at=action.created_at.isoformat(),
        before_text=action.before_text,
        after_text=action.after_text,
        draft_state_before=action.draft_state_before.value,
        draft_state_after=action.draft_state_after.value,
        rejection_reason=action.rejection_reason,
        scheduled_for=action.scheduled_for.isoformat() if action.scheduled_for else None,
        publish_job_id=action.publish_job_id,
    )


def _build_review_draft_sibling_variant_response(draft: DraftVariant) -> ReviewDraftSiblingVariantResponse:
    return ReviewDraftSiblingVariantResponse(
        draft_id=draft.id,
        variant_index=draft.variant_index,
        body=draft.body,
        draft_state=draft.state.value,
        rejection_reason=draft.rejection_reason,
        created_at=draft.created_at.isoformat(),
        reviewed_at=draft.reviewed_at.isoformat() if draft.reviewed_at else None,
    )


def _build_review_action_response(result: ReviewDraftResult) -> ReviewActionResponse:
    return ReviewActionResponse(
        draft_id=result.draft_id,
        reviewer=result.reviewer,
        action_type=result.action_type.value,
        draft_state=result.draft_state.value,
        action_id=result.action_id,
        publish_job_id=result.publish_job_id,
        scheduled_for=result.scheduled_for.isoformat() if result.scheduled_for else None,
    )


def _build_api_error_response(*, status_code: int, error_code: str, message: str) -> JSONResponse:
    payload = ApiErrorResponse(error_code=error_code, message=message)
    return JSONResponse(status_code=status_code, content=payload.model_dump())
