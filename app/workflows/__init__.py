"""Workflow package exports.

Explicit re-exports keep callable workflow entrypoints stable even when
same-named submodules are imported elsewhere first.
"""

from __future__ import annotations

from app.workflows.build_content_briefs import (
    BuildContentBriefOutcome,
    BuildContentBriefsResult,
    build_content_briefs,
)
from app.workflows.discover_sources import DiscoverSourcesResult, discover_sources
from app.workflows.enrich_articles import (
    EnrichArticleOutcome,
    EnrichArticlesResult,
    enrich_articles,
)
from app.workflows.generate_drafts import (
    GenerateDraftOutcome,
    GenerateDraftsResult,
    generate_drafts,
)
from app.workflows.history_queries import (
    ArticleStatusResult,
    ArticleStatusRow,
    PipelineFailureHistoryResult,
    PipelineRunHistoryResult,
    PublishJobDetailResult,
    PublishJobListResult,
    PublishJobListRow,
    PublishJobNotFoundError,
    get_publish_job_detail,
    list_article_statuses,
    list_pipeline_failures,
    list_pipeline_runs,
    list_publish_jobs,
)
from app.workflows.ingest_sources import IngestSourcesResult, SourceIngestOutcome, ingest_sources
from app.workflows.review_queue import (
    DraftNotFoundError,
    DraftReviewStateError,
    DraftScheduleError,
    DraftValidationFailedError,
    ManualPublishError,
    ManualPublishOutcomeResult,
    ManualPublishStateError,
    PendingReviewDraft,
    PendingReviewDraftsResult,
    ReviewDraftResult,
    ReviewerIdentityError,
    ReviewQueueError,
    approve_draft,
    cancel_manual_publish_handoff,
    complete_manual_publish_handoff,
    edit_draft,
    fail_manual_publish_handoff,
    list_pending_review_drafts,
    reject_draft,
    resolve_reviewer_identity,
    schedule_draft,
)
from app.workflows.run_local_pipeline import RunLocalPipelineResult, run_local_pipeline

__all__ = [
    "ArticleStatusResult",
    "ArticleStatusRow",
    "BuildContentBriefOutcome",
    "BuildContentBriefsResult",
    "DiscoverSourcesResult",
    "DraftNotFoundError",
    "DraftReviewStateError",
    "DraftScheduleError",
    "DraftValidationFailedError",
    "EnrichArticleOutcome",
    "EnrichArticlesResult",
    "GenerateDraftOutcome",
    "GenerateDraftsResult",
    "IngestSourcesResult",
    "ManualPublishError",
    "ManualPublishOutcomeResult",
    "ManualPublishStateError",
    "PendingReviewDraft",
    "PendingReviewDraftsResult",
    "PipelineFailureHistoryResult",
    "PipelineRunHistoryResult",
    "PublishJobDetailResult",
    "PublishJobListResult",
    "PublishJobListRow",
    "PublishJobNotFoundError",
    "ReviewDraftResult",
    "ReviewQueueError",
    "ReviewerIdentityError",
    "RunLocalPipelineResult",
    "SourceIngestOutcome",
    "approve_draft",
    "build_content_briefs",
    "cancel_manual_publish_handoff",
    "complete_manual_publish_handoff",
    "discover_sources",
    "edit_draft",
    "enrich_articles",
    "fail_manual_publish_handoff",
    "generate_drafts",
    "get_publish_job_detail",
    "ingest_sources",
    "list_article_statuses",
    "list_pending_review_drafts",
    "list_pipeline_failures",
    "list_pipeline_runs",
    "list_publish_jobs",
    "reject_draft",
    "resolve_reviewer_identity",
    "run_local_pipeline",
    "schedule_draft",
]
