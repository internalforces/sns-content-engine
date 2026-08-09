# Global Country News Phase 1 Country News MVP Vibe Coding Prompt

## Purpose
This document is the kickoff brief for building the first production-ready country news config using two accounts: `korea_global_news` and `japan_global_news`.

Use it when you want an autonomous coding agent to replace the sample AI/SEO CSV path with real Korea/Japan news RSS sources while preserving the current multichannel draft structure.

## Generated Document Naming
- Vibe coding prompt file: `docs/global-country-news-phase-1-country-news-mvp-vibe-coding-prompt.md`
- Roadmap file: `docs/global-country-news-phase-1-country-news-mvp-roadmap.md`
- Execution guide file: `docs/global-country-news-phase-1-country-news-mvp-execution-guide.md`
- Progress tracker file: `docs/global-country-news-phase-1-country-news-mvp-progress-tracker.md`

## Initiative Brief
- Initiative name: `Global Country News Phase 1 Country News MVP`
- One-sentence outcome: `Create and validate a Korea/Japan global news config that generates reviewable English drafts from real RSS sources with no placeholder URLs.`
- Why this matters now:
  - The live publisher path works, but the first content source was placeholder sample data.
  - The product direction is now country news explained for global readers, not AI/SEO tool snippets.
- Primary owner:
  - single-server operator
  - autonomous agent implementing config and docs
- Core workflow to improve:
  - ingest real Korea/Japan RSS items
  - generate channel-specific English drafts for X, Threads, and LinkedIn
  - approve and live-publish exactly one X draft per account after dry-run
- Explicit non-goals:
  - no blog publishing
  - no X-to-Threads or X-to-LinkedIn funnel
  - no auto-approval
  - no automatic LinkedIn live publish
  - no broad scheduler redesign

## Repository Context
The repository already has:
- RSS, sitemap, manual CSV, and GDELT source connectors
- `run-local` for ingest, enrich, brief creation, and draft generation
- prompt profiles for all-domain news examples
- manual review and scheduling
- X live publisher and Threads live adapter, with LinkedIn manual handoff only

Important files and patterns:
- Core entrypoints: `app/cli.py`, `app/scheduler/runtime.py`
- Workflows/services: `app/workflows/run_local_pipeline.py`, `app/workflows/generate_drafts.py`, `app/services/x_draft_generator.py`
- Config examples: `config/examples/all_domain_news/accounts.yaml`, `config/examples/all_domain_news/sources.yaml`, `config/examples/all_domain_news/prompts.yaml`
- Active current config: `config/accounts.yaml`, `config/sources.yaml`, `config/prompts.yaml`, `config/providers.yaml`
- Tests to reuse first: `tests/test_config.py`, `tests/test_discover_workflow.py`, `tests/test_run_local_pipeline_workflow.py`, `tests/test_cli.py`
- Docs to align with: `README.md`, `docs/all-domain-news-operator-guide.md`, `docs/operator-console-guide.md`

## Product Intent And Quality Bar
The desired implementation should:
- create `korea_global_news` and `japan_global_news` accounts
- use real RSS URLs, not sample CSV rows
- keep `landing.strategy: source` so every draft links to the original article
- generate independent drafts for X, Threads, and LinkedIn from the same source brief
- keep X live publishing behind manual approval and dry-run

The agent should preserve:
- dry-run-first scheduler behavior
- manual review before schedule or publish
- LinkedIn manual handoff behavior
- Threads manual fallback unless a separate later rollout enables live Threads

The agent should avoid:
- adding blog behavior in Phase 1
- making X a funnel to other channels
- scraping full article text by default from restricted publisher sources
- weakening attribution and provenance validation

## Source Candidates
Korea first-pass source candidates:
- `https://world.kbs.co.kr/rss/rss_news.htm?lang=e`
- `https://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=Po`
- `https://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=Ec`
- `https://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=Dm`
- `https://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=Cu`
- `https://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=Sc`
- `https://en.yna.co.kr/RSS/news.xml`
- `https://www.koreaherald.com/rss/newsAll`
- `https://www.koreaherald.com/rss/kh_National`
- `https://www.korea.net/koreanet/rss/news/2`

Japan first-pass source candidates:
- `https://www.japantimes.co.jp/feed/`
- `https://japantoday.com/feed/atom`
- `https://japannews.yomiuri.co.jp/feed/`
- `http://www3.nhk.or.jp/rj/podcast/rss/english.xml`

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `./.venv/bin/python -m app.cli version`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config`
- Narrow verification commands:
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config/global_country_news`
  - `./.venv/bin/python -m app.cli run-local --config-dir config/global_country_news --database-url sqlite:///data/global_country_news_phase1.db`
  - `./.venv/bin/python -m app.cli review list --database-url sqlite:///data/global_country_news_phase1.db`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_config.py tests/test_discover_workflow.py tests/test_run_local_pipeline_workflow.py -q`
  - `scripts/scan_secrets.sh check`
  - `git diff --check`
- Required local services:
  - network access for RSS discovery tests or operator smoke runs
- Required env files, secrets, or fixtures:
  - `OPENAI_API_KEY` or configured draft provider for live draft generation
  - X publisher credentials only for the later production live gate
- Package install policy: `not_allowed`
- Push and PR policy: `do_not_push_without_explicit_request`

## First-Pass Definition Of Done
- `config/global_country_news/` exists with accounts, sources, prompts, and providers.
- Placeholder scan over the new config returns no `example.*` URLs.
- `run-local` creates reviewable drafts from real RSS items.
- X, Threads, and LinkedIn drafts remain independent channel drafts.
- No live publish command runs during config creation.

## Prompt Template
```text
You are implementing Global Country News Phase 1 in this repository.

Read:
- docs/global-country-news-phase-1-country-news-mvp-vibe-coding-prompt.md
- docs/global-country-news-phase-1-country-news-mvp-roadmap.md
- docs/global-country-news-phase-1-country-news-mvp-execution-guide.md
- docs/global-country-news-phase-1-country-news-mvp-progress-tracker.md

Create the smallest safe country-news config slice for `korea_global_news` and `japan_global_news`.
Preserve the current structure: X, Threads, and LinkedIn are independent drafts from the same original source URL.
Do not build blog publishing or a social funnel in this phase.
Do not run `scheduler publish-due --live` unless the task is the explicit one-post production rollout and the operator has approved the exact command.
```
