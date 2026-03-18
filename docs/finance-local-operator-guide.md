# Finance Local MVP Operator Guide

## What this local MVP does
- Finds new RSS items.
- Saves only new items after duplicate checks.
- Opens each article page and fetches HTML.
- Extracts article text.
- Regenerates a summary from the article body.
- Builds briefs and X drafts.
- Stops at `pending_review` without publishing.

## What this local MVP does not do
- It does not auto-approve drafts.
- It does not auto-publish posts.
- It does not ship with a production finance feed list.

## Recommended local setup
1. Copy the example files from `config/examples/finance_local/` into your own local config directory.
2. Replace the example RSS URL and landing URL values with your local test values.
3. Initialize a fresh database with `sns-engine db init`.
4. Run the pipeline with `sns-engine run-local`.
5. Inspect results with `sns-engine history runs`, `sns-engine history failures`, and `sns-engine review list`.

## Local command sequence
```bash
sns-engine db init --database-url sqlite:///data/sns_content_engine.db
sns-engine run-local --config-dir config/examples/finance_local --database-url sqlite:///data/sns_content_engine.db
sns-engine history runs --database-url sqlite:///data/sns_content_engine.db
sns-engine history failures --database-url sqlite:///data/sns_content_engine.db
sns-engine review list --database-url sqlite:///data/sns_content_engine.db
```

## How to read failures
- `fetch_blocked`: the site blocked article access.
- `extract_failed`: the article body could not be read.
- `content_too_short`: the article was too short to summarize safely.
- `summary_failed`: the body did not produce enough stable points for a summary.

## Future UI entry points
- Recent run summaries come from `pipeline_runs` and `pipeline_run_stages`.
- Article-level status comes from `article_enrichments` linked to `source_items`.
- Reviewable drafts come from `content_briefs`, `draft_variants`, and the review queue.
