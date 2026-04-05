# All-Domain News Pipeline TODO

## Goal
Extend the current finance-local MVP into a broader latest-news pipeline that:
- discovers recent news across multiple domains,
- applies source-policy guardrails before article reuse,
- rewrites articles through an LLM layer backed by Codex-Wrapper,
- keeps manual review as the default safety gate before publishing.

## Current implementation snapshot

### Already implemented
- Config-driven source loading via RSS, sitemap, and manual CSV connectors.
- Discovery and ingestion workflow with duplicate blocking.
- Article enrichment workflow:
  - fetch article HTML,
  - extract article text,
  - regenerate summaries,
  - persist readable failure reasons.
- Brief generation that prefers enriched summaries and key points.
- Draft generation for X with configurable prompt profiles.
- Manual review queue with approve, reject, edit, and schedule actions.
- Scheduler/backfill/publish-due operational flow.
- Pipeline run history and failure history queries for future UI/API use.

### Current limitations relevant to the new goal
- The active local MVP is finance-oriented and stops at `pending_review`.
- Example source config still uses placeholder URLs.
- Discovery sources are configured statically; there is no news-aggregator connector yet.
- Provider routing supports `openai`, `anthropic`, and `fake`, but not Codex-Wrapper.
- There is no source-policy layer that distinguishes:
  - discovery-only sources,
  - reusable sources,
  - restricted sources.
- The current prompt guidance is optimized for finance/X drafts, not all-domain news coverage.

## Target architecture

### Source layers
- `discovery_only`
  - Broad discovery sources used to find what is new.
  - Example target: GDELT connector.
- `reusable`
  - Sources whose content can be safely fetched and transformed under their terms.
  - Example target set: official institutions, government agencies, company newsroom/IR feeds, Wikinews.
- `restricted`
  - Sources that may be used for trend detection or short summaries with attribution/linking, but not treated as safe full-text reuse.

### Processing layers
1. Discover recent items from all configured sources.
2. Apply source-policy rules before enrichment.
3. Fetch/extract article text only when allowed by source policy.
4. Rewrite through Codex-Wrapper-backed LLM prompts.
5. Store drafts with provenance and policy metadata.
6. Keep manual review as the default publish gate.

## TODO roadmap

## Phase 1: Source strategy and policy foundation

### 1. Add source-policy metadata to config schemas
- Add per-source policy fields in config:
  - `policy_mode`: `discovery_only | reusable | restricted`
  - `allow_full_text_fetch`: boolean
  - `allow_llm_rewrite`: boolean
  - `require_attribution`: boolean
  - `notes`: optional string
- Update config validation and example config files.
- Done when:
  - schemas parse the new fields,
  - defaults are explicit,
  - tests cover valid/invalid configurations.

### 2. Persist source-policy metadata with source items and enrichments
- Store enough metadata to explain why an item was or was not fetched/reused.
- Candidate additions:
  - source policy mode,
  - reuse mode,
  - attribution requirement,
  - policy decision reason.
- Done when:
  - policy decisions are visible in storage,
  - history/failure queries can expose them later.

### 3. Define default source groups for all-domain operation
- Add operator-facing example configs for:
  - official/government feeds,
  - corporate newsroom/IR feeds,
  - Wikinews,
  - future GDELT discovery-only source.
- Keep these examples clearly marked as samples, not production defaults.
- Done when:
  - a new example config directory exists for all-domain news operation.

## Phase 2: Discovery expansion

### 4. Add a GDELT discovery connector
- Create a connector for recent-news discovery only.
- Normalize output into the existing source item candidate model.
- Mark GDELT-discovered items as `discovery_only` unless paired with a reusable source.
- Done when:
  - the connector can return normalized candidates,
  - the connector is covered by unit tests,
  - operator docs explain how it should be used.

### 5. Add source-specific routing for discovery vs enrichment
- Ensure some sources can participate in discovery without automatic article fetching.
- Update ingest/enrich workflows to respect policy decisions.
- Done when:
  - `enrich_articles` skips blocked items intentionally,
  - skipped cases are stored with readable reasons.

## Phase 3: Codex-Wrapper LLM integration

### 6. Add a Codex-Wrapper draft generation provider
- Implement `app/connectors/llm/codex_wrapper_provider.py`.
- Target the wrapper's OpenAI-compatible endpoints such as `/v1/chat/completions`.
- Support environment/config values such as:
  - `CODEX_WRAPPER_BASE_URL`
  - `CODEX_WRAPPER_API_KEY`
  - `CODEX_WRAPPER_MODEL`
  - optional timeout/reasoning controls if needed
- Done when:
  - draft generation can run through Codex-Wrapper,
  - provider errors are surfaced like existing LLM providers,
  - tests cover request building and failure handling.

### 7. Extend provider routing to support Codex-Wrapper
- Update routing config and resolver logic so `provider: codex_wrapper` is valid.
- Keep fallback behavior compatible with existing `openai`, `anthropic`, and `fake`.
- Done when:
  - `config/providers.yaml` can route draft generation to Codex-Wrapper,
  - resolver tests cover mixed fallback chains.

### 8. Decide whether summary regeneration should also use Codex-Wrapper
- Current summary regeneration is deterministic and local-friendly.
- Decide between:
  - keeping deterministic summary generation for reliability, or
  - adding optional LLM-backed rewrite/summarize steps behind config flags.
- Recommended first step:
  - keep current summary regeneration,
  - use Codex-Wrapper first for draft rewriting only.

## Phase 4: Prompt and content-policy generalization

### 9. Create all-domain prompt profiles
- Add non-finance prompt profiles for:
  - general news summary,
  - factual X post,
  - attribution-first short post.
- Remove finance-specific assumptions from the all-domain example path.
- Done when:
  - prompt profiles exist for multiple neutral news styles,
  - tests verify prompt rendering with source metadata.

### 10. Add content-policy guardrails by domain sensitivity
- Add simple classification or rule flags for domains like:
  - politics,
  - finance,
  - health,
  - crime / disasters.
- Enforce stricter phrasing rules and review requirements by domain.
- Done when:
  - high-risk topics are clearly flagged for manual review,
  - prompts include domain-aware caution where needed.

### 11. Improve provenance in generated drafts
- Ensure drafts and stored metadata retain:
  - source name,
  - source URL,
  - article URL,
  - published timestamp,
  - policy mode.
- Done when:
  - reviewers can see where every draft came from without log inspection.

## Phase 5: Review and publishing safety

### 12. Keep manual review as the default gate
- Preserve the current `pending_review` stop as the default mode.
- Add optional future policies like:
  - only reusable sources may be scheduled,
  - restricted sources always require a human reviewer,
  - high-risk domains always require manual approval.
- Done when:
  - review workflow checks source policy before scheduling/publishing.

### 13. Add policy-aware validation before publish scheduling
- Extend validation to block or warn on:
  - missing attribution,
  - restricted-source full-text reuse,
  - missing provenance data.
- Done when:
  - invalid drafts cannot be scheduled silently.

## Phase 6: Operator and UI readiness

### 14. Add operator documentation for all-domain news runs
- Document:
  - which sources are discovery-only,
  - which sources are reusable,
  - what Codex-Wrapper is used for,
  - what must still be reviewed manually.
- Done when:
  - a new operator guide exists for the broader pipeline.

### 15. Extend history queries for policy visibility
- Add future query fields that support UI/API views such as:
  - policy mode,
  - skipped-by-policy count,
  - rewrite-provider used,
  - attribution-required count.
- Done when:
  - a future dashboard can explain not only failures, but also intentional skips.

## Suggested execution order
1. Source-policy config and storage changes.
2. GDELT discovery connector.
3. Enrichment workflow policy gating.
4. Codex-Wrapper provider implementation.
5. Provider routing/config updates.
6. All-domain prompt profiles and provenance improvements.
7. Review/publish policy enforcement.
8. Operator docs and UI-facing query expansion.

## Recommended first milestone
Ship a safe "all-domain review-only" milestone with:
- reusable-source config examples,
- GDELT discovery-only support,
- Codex-Wrapper draft generation,
- policy-aware enrichment skips,
- manual review still required for every post.

This keeps the project aligned with the current architecture while expanding coverage without removing the existing safety model.
