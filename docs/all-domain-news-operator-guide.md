# All-Domain News Operator Guide

## What this all-domain path is for
- Discover fresh items across broader news domains without removing the current manual-review safety model.
- Apply source-policy rules before fetching or rewriting article text.
- Use Codex-Wrapper only for draft rewriting, not for auto-publish decisions.
- Keep every generated post in `pending_review` until a human approves it.

## Source-policy categories
- `discovery_only`
  Use these sources to detect that something new happened. Recommended default: `allow_full_text_fetch: false`, `allow_llm_rewrite: false`, `require_attribution: true`.
- `reusable`
  Use these sources when your terms review says article text can be fetched and transformed safely. Keep `require_attribution: true` whenever the source should still be cited in the draft or review context.
- `restricted`
  Use these sources for trend detection, attribution-first summaries, or operator review context. Do not treat them as safe full-text rewrite sources, and keep scheduling blocked when provenance or attribution rules are not satisfied.

## When intentional skips happen
- The enrich step intentionally skips an item when source policy blocks full-text fetch.
- The enrich step also intentionally skips after fetch when policy allows article access but blocks LLM rewrite.
- These are not connector or parser failures. They are expected policy decisions recorded so operators can explain why an item stopped.
- `sns-engine history runs` shows the stored policy-aware counts and any rewrite providers used during draft generation.
- `sns-engine history failures` now prints both ordinary `type=failure` rows and intentional `type=policy_skip` rows with source-policy metadata and readable skip reasons.

## How draft provider routing works
- If `<config-dir>/providers.yaml` exists, `generate-drafts` and `run-local` use its `draft_generate` route chain at runtime.
- Credentials still come from environment variables only; the YAML file controls route order and optional model overrides.
- If `providers.yaml` is absent, draft generation falls back to environment-based auto-detection in this order: OpenAI, Anthropic, then Codex-Wrapper.
- `history runs` records the provider names that actually produced drafts during the run.

## What Codex-Wrapper is used for
- Codex-Wrapper is the draft-generation rewrite layer for `generate_drafts` and `run_local`.
- It is not used to bypass source policy checks.
- It is not used to auto-approve, auto-schedule, or auto-publish posts.
- If routing is configured with fallbacks, history stores the provider names that actually produced drafts during the run.

## Why manual review still stays required
- Source policy does not guarantee headline accuracy, context completeness, or safe phrasing for sensitive topics.
- Attribution and provenance still need a human check before scheduling.
- Restricted and high-risk topics are intentionally kept behind reviewer judgment.
- The safe default remains: generate drafts, inspect them, then explicitly approve or schedule.

## Recommended operating sequence
```bash
sns-engine db init --database-url sqlite:///data/sns_content_engine.db
sns-engine run-local --config-dir config/examples/all_domain_news --database-url sqlite:///data/sns_content_engine.db
sns-engine history runs --database-url sqlite:///data/sns_content_engine.db
sns-engine history failures --database-url sqlite:///data/sns_content_engine.db
sns-engine review list --database-url sqlite:///data/sns_content_engine.db
```

## Operator checklist
- Start from `config/examples/all_domain_news/`, then replace sample URLs with operator-approved sources.
- Keep discovery-only sources in separate source sets when you want discovery coverage without treating them as reusable full-text sources.
- Read `history failures` as a mixed operator feed: `type=failure` rows are technical problems, and `type=policy_skip` rows are intentional policy decisions.
- Schedule only drafts that keep provenance intact and satisfy attribution requirements.
