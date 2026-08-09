"""Pydantic request and response contracts for the operator API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthcheckCheckResponse(_ApiModel):
    name: str
    status: str
    message: str


class HealthcheckResponse(_ApiModel):
    status: str
    failed_check_count: int
    checks: list[HealthcheckCheckResponse]


class PipelineRunResponse(_ApiModel):
    run_id: int
    workflow_name: str
    status: str
    trigger_mode: str
    started_at: str
    completed_at: str | None
    discovered_count: int
    saved_count: int
    enriched_count: int
    brief_count: int
    draft_count: int
    failure_count: int
    latest_error_code: str | None
    policy_mode_counts: dict[str, int]
    policy_skipped_count: int
    attribution_required_count: int
    rewrite_providers: list[str]


class PipelineRunsResponse(_ApiModel):
    runs: list[PipelineRunResponse]


class PipelineFailureResponse(_ApiModel):
    source_item_id: int
    article_enrichment_id: int
    title: str
    source_name: str | None
    article_url: str
    source_policy_mode: str
    require_attribution: bool
    failure_stage: str | None
    failure_code: str
    failure_message: str
    updated_at: str


class PipelinePolicySkipResponse(_ApiModel):
    source_item_id: int
    article_enrichment_id: int
    title: str
    source_name: str | None
    article_url: str
    source_policy_mode: str
    require_attribution: bool
    skipped_stage: str
    policy_decision_reason: str
    updated_at: str


class PipelineFailuresResponse(_ApiModel):
    failures: list[PipelineFailureResponse]
    policy_skips: list[PipelinePolicySkipResponse]


class ArticleStatusResponse(_ApiModel):
    source_item_id: int
    article_enrichment_id: int | None
    source_name: str
    title: str
    original_url: str
    article_url: str | None
    published_at: str | None
    discovered_at: str
    enrichment_state: str
    fetch_status: str
    extract_status: str
    summarize_status: str
    last_failure_message: str | None


class ArticleStatusesResponse(_ApiModel):
    articles: list[ArticleStatusResponse]


class PublishJobRowResponse(_ApiModel):
    publish_job_id: int
    draft_id: int
    brief_id: int
    account_key: str
    channel: str
    state: str
    scheduled_for: str | None
    published_at: str | None
    created_at: str
    updated_at: str
    attempt_count: int
    external_post_id: str | None
    last_error: str | None
    variant_index: int
    draft_state: str
    brief_title: str
    source_title: str


class PublishJobsResponse(_ApiModel):
    jobs: list[PublishJobRowResponse]


class PendingReviewDraftResponse(_ApiModel):
    draft_id: int
    account_key: str
    channel: str
    variant_index: int
    created_at: str
    title: str
    body: str


class PendingReviewDraftsResponse(_ApiModel):
    pending_count: int
    drafts: list[PendingReviewDraftResponse]


class ReviewDraftProvenanceResponse(_ApiModel):
    source_name: str | None
    source_url: str | None
    article_url: str | None
    source_published_at: str | None
    source_policy_mode: str | None


class ReviewDraftBriefResponse(_ApiModel):
    brief_id: int
    title: str
    summary: str | None
    key_points: list[str]
    landing_url: str
    tags: list[str]
    angle: str
    language: str


class ReviewDraftSourceItemResponse(_ApiModel):
    source_item_id: int
    source_key: str
    external_id: str
    title: str
    summary: str | None
    source_url: str
    canonical_url: str
    published_at: str | None
    policy_mode: str
    require_attribution: bool


class ReviewDraftArticleEnrichmentResponse(_ApiModel):
    article_enrichment_id: int
    source_name: str | None
    article_url: str
    published_at: str | None
    discovered_at: str
    regenerated_summary: str | None
    regenerated_key_points: list[str]
    classification: str | None


class ReviewDraftSensitivityResponse(_ApiModel):
    is_high_risk: bool
    domain: str | None
    matched_terms: list[str]
    review_note: str | None
    prompt_guidance: str | None


class ReviewDraftAuditEntryResponse(_ApiModel):
    action_id: int
    action_type: str
    reviewer: str
    created_at: str
    before_text: str
    after_text: str
    draft_state_before: str
    draft_state_after: str
    rejection_reason: str | None
    scheduled_for: str | None
    publish_job_id: int | None


class ReviewDraftSiblingVariantResponse(_ApiModel):
    draft_id: int
    variant_index: int
    body: str
    draft_state: str
    rejection_reason: str | None
    created_at: str
    reviewed_at: str | None


class ReviewDraftDetailResponse(_ApiModel):
    draft_id: int
    account_key: str
    channel: str
    variant_index: int
    body: str
    draft_state: str
    rejection_reason: str | None
    created_at: str
    reviewed_at: str | None
    provenance: ReviewDraftProvenanceResponse
    brief: ReviewDraftBriefResponse
    source_item: ReviewDraftSourceItemResponse
    article_enrichment: ReviewDraftArticleEnrichmentResponse | None
    sensitivity: ReviewDraftSensitivityResponse
    review_actions: list[ReviewDraftAuditEntryResponse]
    sibling_variants: list[ReviewDraftSiblingVariantResponse]


class PublishJobDraftResponse(_ApiModel):
    draft_id: int
    variant_index: int
    body: str
    draft_state: str
    rejection_reason: str | None
    created_at: str
    reviewed_at: str | None


class PublishJobLogEntryResponse(_ApiModel):
    log_id: int
    event_type: str
    message: str
    payload: dict[str, Any] | None
    created_at: str


class PublishJobDetailResponse(_ApiModel):
    publish_job_id: int
    account_key: str
    channel: str
    state: str
    scheduled_for: str | None
    published_at: str | None
    created_at: str
    updated_at: str
    attempt_count: int
    external_post_id: str | None
    last_error: str | None
    draft: PublishJobDraftResponse
    provenance: ReviewDraftProvenanceResponse
    brief: ReviewDraftBriefResponse
    source_item: ReviewDraftSourceItemResponse
    publish_logs: list[PublishJobLogEntryResponse]


class SchedulerDiscoverResponse(_ApiModel):
    discovered_count: int
    processed_sources: list[str]
    failure_count: int
    failure_messages: list[str]


class SchedulerBackfillChannelResponse(_ApiModel):
    account_key: str
    channel: str
    backlog_target: int
    existing_future_job_count: int
    eligible_draft_count: int
    planned_slot_count: int
    created_job_ids: list[int]
    created_count: int
    skipped_slot_count: int


class SchedulerBackfillResponse(_ApiModel):
    processed_channel_count: int
    created_count: int
    existing_count: int
    skipped_count: int
    outcomes: list[SchedulerBackfillChannelResponse]


class SchedulerPublishDueOutcomeResponse(_ApiModel):
    publish_job_id: int
    status: str
    state: str
    message: str
    external_post_id: str | None


class SchedulerPublishDueResponse(_ApiModel):
    dry_run: bool
    processed_count: int
    published_count: int
    failed_count: int
    dry_run_count: int
    skipped_count: int
    outcomes: list[SchedulerPublishDueOutcomeResponse]


class SchedulerActionContextRequest(_ApiModel):
    config_dir: str = "config"


class SchedulerPublishDueRequest(SchedulerActionContextRequest):
    live: bool = False


class ReviewActionContextRequest(_ApiModel):
    reviewer: str | None = None
    config_dir: str = "config"


class ApproveDraftRequest(ReviewActionContextRequest):
    pass


class RejectDraftRequest(ReviewActionContextRequest):
    reason: str


class EditDraftRequest(ReviewActionContextRequest):
    body: str


class ScheduleDraftRequest(ReviewActionContextRequest):
    scheduled_for: str


class ReviewActionResponse(_ApiModel):
    draft_id: int
    reviewer: str
    action_type: str
    draft_state: str
    action_id: int
    publish_job_id: int | None = None
    scheduled_for: str | None = None


class ManualPublishActionRequest(_ApiModel):
    operator: str | None = None


class CompleteManualPublishRequest(ManualPublishActionRequest):
    external_post_id: str | None = None


class FailManualPublishRequest(ManualPublishActionRequest):
    error_message: str


class CancelManualPublishRequest(ManualPublishActionRequest):
    reason: str | None = None


class ManualPublishOutcomeResponse(_ApiModel):
    publish_job_id: int
    channel: str
    operator: str
    previous_state: str
    publish_job_state: str
    external_post_id: str | None = None
    last_error: str | None = None
    published_at: str | None = None


class ApiErrorResponse(_ApiModel):
    error_code: str
    message: str
