# Global Country News Phase 1 Country News MVP Roadmap

## Goal
Extend the current placeholder-backed AI/SEO config into a real Korea/Japan global news MVP that:
- creates `korea_global_news` and `japan_global_news` accounts
- uses real RSS sources for each country
- generates independent X, Threads, and LinkedIn drafts from original article URLs
- verifies one controlled X live publish per account only after manual review and dry-run

## Generated Document Naming
- Roadmap file: `docs/global-country-news-phase-1-country-news-mvp-roadmap.md`
- Execution guide file: `docs/global-country-news-phase-1-country-news-mvp-execution-guide.md`
- Progress tracker file: `docs/global-country-news-phase-1-country-news-mvp-progress-tracker.md`
- Vibe coding prompt file: `docs/global-country-news-phase-1-country-news-mvp-vibe-coding-prompt.md`

## Current Implementation Snapshot

### Already Implemented
- RSS discovery and normalized source ingestion.
- `run-local` pipeline through draft generation.
- All-domain news example config and prompts.
- Manual review, approve, schedule, and dry-run publish.
- X live publisher and manual LinkedIn handoff behavior.

### Current Limitations Relevant To The New Goal
- Active config currently targets AI/SEO accounts.
- Active default source rows are manual CSV placeholders.
- No dedicated Korea/Japan country-news config exists.
- The first live publish proved the publisher path but not the content-source quality.

## Environment And Execution Assumptions
- Base branch: `master`
- New config path: `config/global_country_news`
- Narrow verification commands:
  - `rg -n 'example\\.com|example\\.org|example\\.net' config/global_country_news`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config/global_country_news`
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_phase1.db`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_config.py tests/test_discover_workflow.py tests/test_run_local_pipeline_workflow.py -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Required env:
  - draft provider credentials for live LLM draft generation
  - no publisher credentials are required until the controlled live gate

## Target Architecture

### Config Layer
- `config/global_country_news/sources.yaml`
  - Korea RSS source definitions
  - Japan RSS source definitions
  - `korea_global_primary` and `japan_global_primary` source sets
- `config/global_country_news/accounts.yaml`
  - `korea_global_news`
  - `japan_global_news`
  - X, LinkedIn, and Threads channel definitions
- `config/global_country_news/prompts.yaml`
  - shared global country news explainer profile
  - optional per-country style hints if needed
- `config/global_country_news/providers.yaml`
  - reuse OpenAI-first draft route from current production pattern

### Workflow Layer
1. RSS discovery stores real article URLs.
2. Source matching routes items to the country account.
3. Brief generation uses `landing.strategy: source`.
4. Draft generation creates independent X, Threads, and LinkedIn drafts.
5. Manual review gates approval and scheduling.

## Milestones

### Milestone M1: Config Baseline
- Goal: create a real source-backed country-news config.
- Includes:
  - accounts, sources, prompts, providers
  - placeholder-free healthcheck
- Excludes:
  - live publishing
  - blog or funnel behavior
- Ship when:
  - `healthcheck` passes
  - placeholder scan is clean

### Milestone M2: Reviewable Drafts
- Goal: prove the config can produce human-reviewable drafts.
- Includes:
  - `run-local`
  - review list inspection
  - source URL and attribution check
- Excludes:
  - approval automation
  - live publish
- Ship when:
  - both accounts have reviewable drafts or blockers are recorded

### Milestone M3: Controlled X Live Verification
- Goal: verify one X live post for Korea and one for Japan.
- Includes:
  - manual approval
  - schedule
  - dry-run due-job confirmation
  - one explicit live command per account
- Excludes:
  - automatic recurring live publish
  - LinkedIn or Threads live rollout
- Ship when:
  - both country accounts have one externally confirmed X result

## Implementation Roadmap

## Phase 1: Country News MVP

### Task 01: Create Global Country News Config Skeleton
- Goal: add a new config directory without disturbing the existing default config.
- Actions:
  - create `config/global_country_news/`
  - add initial `accounts.yaml`, `sources.yaml`, `prompts.yaml`, and `providers.yaml`
  - keep X, LinkedIn, and Threads channel definitions
- Dependencies:
  - Phase 0 pause decision
- Verification commands:
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config/global_country_news`
  - `rg -n 'example\\.com|example\\.org|example\\.net' config/global_country_news`
- Risk or rollback note:
  - config-only addition; rollback is deleting the new directory
- Done when:
  - healthcheck passes for the new config
  - no placeholder URLs exist in the new config

### Task 02: Add Korea And Japan RSS Sources
- Goal: define approved country news sources and source sets.
- Actions:
  - add Korea sources from KBS World, Yonhap English, Korea Herald, and Korea.net
  - add Japan sources from Japan Times, Japan Today, The Japan News, and NHK World Radio as a secondary source
  - set conservative source policy for publisher content
- Dependencies:
  - Task 01 config skeleton
- Verification commands:
  - `./.venv/bin/python -m app.cli discover --config-dir config/global_country_news`
  - `./.venv/bin/pytest tests/test_config.py -q`
- Risk or rollback note:
  - some feeds may reject requests or produce non-article entries; record and prune before live use
- Done when:
  - discovery returns normalized items or documented source-specific blockers

### Task 03: Add Global Reader Prompt Profile
- Goal: generate drafts that explain country news to global English-speaking readers.
- Actions:
  - add `global_country_news_explainer` prompt profile
  - require source attribution
  - emphasize what happened, why it matters, and local context
- Dependencies:
  - Task 01 config skeleton
- Verification commands:
  - `./.venv/bin/pytest tests/test_prompt_renderer.py tests/test_x_draft_generator.py -q`
  - `git diff --check`
- Risk or rollback note:
  - prompt can be refined without schema changes
- Done when:
  - prompts render successfully through existing generator tests or targeted fixture checks

### Task 04: Generate Reviewable Drafts Locally
- Goal: run the new config through the pipeline and inspect draft quality before any scheduling.
- Actions:
  - initialize or reuse a local test DB
  - run `run-local`
  - inspect `history runs`, `history failures`, and `review list`
- Dependencies:
  - Tasks 01 through 03
- Verification commands:
  - `./.venv/bin/python -m app.cli db init --database-url sqlite:///data/global_country_news_phase1.db`
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_phase1.db`
- Risk or rollback note:
  - local DB can be discarded if source quality is poor
- Done when:
  - drafts contain real source URLs and no placeholders
  - drafts remain pending review

### Task 05: Production Dry-Run Handoff
- Goal: prepare production commands for one-account-at-a-time dry-run verification.
- Actions:
  - document server commands for healthcheck, run-local, review, approve, schedule, and dry-run
  - require service account DB access
  - require exactly one due X job before live approval
- Dependencies:
  - Task 04 local reviewable drafts
- Verification commands:
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Risk or rollback note:
  - handoff is docs-only and must not include `--live`
- Done when:
  - operator can run a safe production dry-run sequence

### Task 06: Controlled Korea X Live Publish
- Goal: publish exactly one approved `korea_global_news/x` draft after dry-run confirms the intended job.
- Actions:
  - record deployed revision
  - record dry-run due-job count, account, channel, and job id
  - require explicit one-command live approval
  - record external X observation
- Dependencies:
  - Task 05 production dry-run handoff
- Verification commands:
  - `sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config/global_country_news`
  - explicit approved `sns-engine scheduler publish-due --live ...`
- Risk or rollback note:
  - do not run if more than one due job exists
- Done when:
  - one Korea X post is externally confirmed

### Task 07: Controlled Japan X Live Publish
- Goal: publish exactly one approved `japan_global_news/x` draft after dry-run confirms the intended job.
- Actions:
  - repeat the Korea process with Japan account scope
  - record source URL and external X observation
  - do not batch with Korea
- Dependencies:
  - Task 06 Korea result and operator decision
- Verification commands:
  - `sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config/global_country_news`
  - explicit approved `sns-engine scheduler publish-due --live ...`
- Risk or rollback note:
  - no second live command without new approval
- Done when:
  - one Japan X post is externally confirmed

## Suggested Execution Order
1. Task 01: Create Global Country News Config Skeleton
2. Task 02: Add Korea And Japan RSS Sources
3. Task 03: Add Global Reader Prompt Profile
4. Task 04: Generate Reviewable Drafts Locally
5. Task 05: Production Dry-Run Handoff
6. Task 06: Controlled Korea X Live Publish
7. Task 07: Controlled Japan X Live Publish

## Initial Milestone Recommendation
Start with M1 config baseline. It is additive, does not disturb current production config, and can be verified without running any live publish.
