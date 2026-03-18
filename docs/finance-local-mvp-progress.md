# Finance Local MVP Progress

## Overall goal
Build a local one-run finance content pipeline that discovers new RSS items, fetches article HTML, extracts article bodies, regenerates summaries, builds briefs, generates X drafts, and stops at `pending_review` without auto-publishing.

## Assumptions snapshot
- Production finance source feeds are not fixed yet, so this MVP will use example config and fixtures instead of hard-coded production feeds.
- RSS is used only for discovery; the article web page becomes the primary content source when enrichment succeeds.
- If a source blocks HTML fetch or extraction, the pipeline should store a readable failure and continue with the next item.
- Existing publish flows must remain unchanged; the new local pipeline must stop before approval or publishing.

## Task log
| Task | Name | Branch | Commit SHA | Done | Verification | Remaining work | Known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | Progress docs and repo audit | `codex/task-01-progress-docs` | `038f341` | Done | Docs created and repo structure audited | Start article enrichment persistence work | No finance pipeline code yet |
| 02 | Article enrichment models | `codex/task-02-article-enrichment-models` | `8ce1b22` | Done | `python -m pytest tests/test_storage.py tests/test_cli.py` | Add pipeline run history persistence | Database schema now includes article enrichment tables |
| 03 | Run history models | `codex/task-03-run-history-models` | `db1cb95` | Done | `python -m pytest tests/test_storage.py tests/test_cli.py` | Add HTML/article services | Run history persistence is modeled but not wired into workflows yet |
| 04 | HTML fetcher | `codex/task-04-html-fetcher` | `0c17270` | Done | `python -m pytest tests/test_article_fetcher.py tests/test_storage.py tests/test_cli.py` | Add article extraction service | Fetcher exists but is not wired into workflows yet |
| 05 | Article extractor | `codex/task-05-article-extractor` | `df5f050` | Done | `python -m pytest tests/test_article_extractor.py tests/test_article_fetcher.py tests/test_storage.py tests/test_cli.py` | Add summary regeneration service | Extraction exists but is not wired into workflows yet |
| 06 | Summary regenerator | `codex/task-06-summary-regenerator` | `aa57947` | Done | `python -m pytest tests/test_summary_regenerator.py tests/test_article_extractor.py tests/test_article_fetcher.py tests/test_storage.py tests/test_cli.py` | Add enrichment workflow | Regeneration exists but is not wired into workflows yet |
| 07 | Enrichment workflow | `codex/task-07-enrichment-workflow` | `bea34d0` | Done | `python -m pytest tests/test_enrich_articles_workflow.py tests/test_summary_regenerator.py tests/test_article_extractor.py tests/test_article_fetcher.py tests/test_storage.py tests/test_cli.py` | Integrate regenerated summaries into brief creation | Workflow currently targets ingested items and stores step-level failures/results |
| 08 | Brief summary integration | `codex/task-08-brief-summary-integration` | `c9775b8` | Done | `python -m pytest tests/test_build_content_briefs_workflow.py tests/test_storage.py tests/test_cli.py` | Add draft source/safety integration | Briefs now prefer regenerated summaries, key points, and enrichment tags when available |
| 09 | Draft safety and source context | `codex/task-09-draft-safety-and-source-context` | `6867a25` | Done | `python -m pytest tests/test_x_draft_generator.py tests/test_generate_drafts_workflow.py tests/test_storage.py tests/test_cli.py` | Add run-local CLI | X draft prompts now include finance safety guidance plus source metadata/context hooks |
| 10 | Run-local CLI | `codex/task-10-run-local-cli` | `453e068` | Done | `python -m pytest tests/test_run_local_pipeline_workflow.py tests/test_enrich_articles_workflow.py tests/test_build_content_briefs_workflow.py tests/test_generate_drafts_workflow.py tests/test_cli.py tests/test_storage.py` | Add readable run/failure queries | `sns-engine run-local` now orchestrates ingest, enrich, brief, and draft stages into pending review |
| 11 | Failure history queries | `codex/task-11-readable-failure-history` | `1ae37c5` | Done | `python -m pytest tests/test_history_queries.py tests/test_cli.py tests/test_run_local_pipeline_workflow.py` | Finalize docs and operator guide | Readable run/failure history now has workflow query helpers and CLI access paths |
| 12 | Docs and operator guide | `codex/task-12-docs` | `0f3b55a` | Done | README, operator guide, and example config updated | Final regression and PR creation remain | Example finance config still uses placeholder URLs |

## Remaining work
- Prepare the final PR summary and merge metadata.

## Known limitations
- Example finance config files use placeholder feed and landing URLs; operators must replace them locally.
- HTML extraction is intentionally lightweight and may need source-specific tuning for complex publisher layouts.
- The repository still keeps older AI/SEO sample config alongside the new finance-local example.
