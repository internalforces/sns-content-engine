# Finance Local UI Data Contract

## First screen: run overview
The future first screen should be able to show:
- the latest local run timestamp
- overall run status
- counts for discovered items, saved items, enriched items, summaries created, briefs created, drafts created, and failures
- a short list of the latest failure messages

Current connection status:
- Backed by `pipeline_runs` and `pipeline_run_stages`.
- Query path: `app.workflows.history_queries.list_pipeline_runs`.
- Primary repositories: `PipelineRunRepository`, `PipelineRunStageRepository`.

## Article list screen
The future article list screen should be able to show:
- source name
- article title
- original URL
- published time
- discovered time
- enrichment state
- fetch/extract/summarize success flags
- last readable failure message

Current connection status:
- Backed by `source_items` plus `article_enrichments`.
- Query path today is repository-driven (`SourceItemRepository`, `ArticleEnrichmentRepository`) and can be wrapped by a future API without changing stored data.

## Draft review screen
The future draft review screen should be able to show:
- source title
- regenerated summary
- key points
- source name
- source/article link
- generated draft variants
- draft review state

Current connection status:
- Backed by `content_briefs`, `draft_variants`, and review queue workflows.
- `ContentBriefBuilder` now prefers regenerated summaries/key points from `article_enrichments`.
- `XDraftGenerator` now exposes source-aware render context fields (`source_name`, `source_url`, `article_summary`).

## Failure screen
The future failure screen should be able to show:
- failure code
- human-readable failure message
- pipeline stage
- related source/article title
- last attempted run

Current connection status:
- Backed by persisted `article_enrichments.failure_*` fields.
- Query path: `app.workflows.history_queries.list_pipeline_failures`.

## Current model / repository / query mapping
- Run overview
  - Models: `pipeline_runs`, `pipeline_run_stages`
  - Repositories: `PipelineRunRepository`, `PipelineRunStageRepository`
  - Query helper: `list_pipeline_runs`
- Article list
  - Models: `source_items`, `article_enrichments`
  - Repositories: `SourceItemRepository`, `ArticleEnrichmentRepository`
  - Workflow producer: `enrich_articles`
- Draft review
  - Models: `content_briefs`, `draft_variants`, `review_actions`
  - Repositories: `ContentBriefRepository`, `DraftVariantRepository`, `ReviewActionRepository`
  - Workflow producers: `build_content_briefs`, `generate_drafts`, `review_queue`
- Failure screen
  - Models: `article_enrichments`, `pipeline_runs`
  - Repositories: `ArticleEnrichmentRepository`, `PipelineRunRepository`
  - Query helper: `list_pipeline_failures`
