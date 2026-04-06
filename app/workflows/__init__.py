"""Workflow package exports."""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "BuildContentBriefOutcome": "app.workflows.build_content_briefs",
    "BuildContentBriefsResult": "app.workflows.build_content_briefs",
    "build_content_briefs": "app.workflows.build_content_briefs",
    "DiscoverSourcesResult": "app.workflows.discover_sources",
    "discover_sources": "app.workflows.discover_sources",
    "EnrichArticleOutcome": "app.workflows.enrich_articles",
    "EnrichArticlesResult": "app.workflows.enrich_articles",
    "enrich_articles": "app.workflows.enrich_articles",
    "GenerateDraftOutcome": "app.workflows.generate_drafts",
    "GenerateDraftsResult": "app.workflows.generate_drafts",
    "generate_drafts": "app.workflows.generate_drafts",
    "PipelineFailureHistoryResult": "app.workflows.history_queries",
    "PipelineRunHistoryResult": "app.workflows.history_queries",
    "list_pipeline_failures": "app.workflows.history_queries",
    "list_pipeline_runs": "app.workflows.history_queries",
    "IngestSourcesResult": "app.workflows.ingest_sources",
    "SourceIngestOutcome": "app.workflows.ingest_sources",
    "ingest_sources": "app.workflows.ingest_sources",
    "RunLocalPipelineResult": "app.workflows.run_local_pipeline",
    "run_local_pipeline": "app.workflows.run_local_pipeline",
    "DraftNotFoundError": "app.workflows.review_queue",
    "DraftReviewStateError": "app.workflows.review_queue",
    "DraftScheduleError": "app.workflows.review_queue",
    "DraftValidationFailedError": "app.workflows.review_queue",
    "PendingReviewDraft": "app.workflows.review_queue",
    "PendingReviewDraftsResult": "app.workflows.review_queue",
    "ReviewDraftResult": "app.workflows.review_queue",
    "ReviewQueueError": "app.workflows.review_queue",
    "ReviewerIdentityError": "app.workflows.review_queue",
    "approve_draft": "app.workflows.review_queue",
    "edit_draft": "app.workflows.review_queue",
    "list_pending_review_drafts": "app.workflows.review_queue",
    "reject_draft": "app.workflows.review_queue",
    "resolve_reviewer_identity": "app.workflows.review_queue",
    "schedule_draft": "app.workflows.review_queue",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value
