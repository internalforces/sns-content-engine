# Global Country News Phase 2 Longform Platform Strategy

## Decision
As of `2026-05-10 21:24 KST`, select `Ghost` as the primary owned long-form home for the first Phase 2 path.

Use `WordPress` as the owned-home fallback if the operator prioritizes the WordPress plugin ecosystem, existing WordPress hosting, or SEO workflows over Ghost's simpler publication model.

The first rollout mode is `manual_handoff_first`:
- generate long-form drafts inside this repository
- keep every draft pending review until an operator approves it
- copy or export approved content to Ghost manually for the first slice
- record the final external article URL only after the operator confirms it
- add a Ghost dry-run adapter later, before any live Ghost API publishing

Do not add platform credentials during Task 01. Future Ghost or WordPress credentials must be referenced only through environment variables.

## Platform Roles
| Platform | Phase 2 role | Decision | Reason |
| --- | --- | --- | --- |
| `Ghost` | Primary blog/newsletter home | `selected_primary` | Owned canonical URL, focused publishing workflow, documented Admin API for content management, and a natural later path from manual handoff to dry-run adapter. |
| `WordPress` | Fallback owned blog home | `selected_fallback` | Mature REST post endpoints and broad SEO/plugin ecosystem, but more operational surface area than the first slice needs. |
| `Substack` | Newsletter and reader-network distribution | `manual_distribution_only` | Current official developer API is profile-lookup oriented, so it is not a safe first programmatic posting target. |
| `beehiiv` | Newsletter growth/monetization alternative | `later_distribution_candidate` | It has post APIs, but the create-post endpoint is beta and Enterprise-gated, so it should not become the canonical first path. |
| `LinkedIn Newsletter` | Professional distribution | `manual_handoff_only` | Keep the existing review-led manual handoff pattern; no direct LinkedIn article/newsletter automation in this slice. |
| `Medium` | Optional cross-post | `manual_cross_post_only` | Use only after human editing; Ghost remains canonical. |
| `Reddit` / `Hacker News` | Community testing | `manual_only` | No automated posting, vote manipulation, or repeated community distribution. |

## Evidence Checked
- [Ghost Admin API documentation](https://docs.ghost.org/admin-api/) describes content management through the Admin API, server-side token authentication, and integration-oriented publishing workflows.
- [WordPress REST API posts documentation](https://developer.wordpress.org/rest-api/reference/posts/) exposes post creation and update endpoints, including draft, pending, publish, future, and private statuses.
- [Substack's official Developer API documentation](https://support.substack.com/hc/en-us/articles/45099095296916-Substack-Developer-API) currently describes public profile lookup by LinkedIn handle, not programmatic post creation.
- [beehiiv's create-post documentation](https://developers.beehiiv.com/api-reference/posts/create) includes post creation support, but the create endpoint is marked beta and Enterprise-only.

## First Implementation Slice
Task 02 model decision:
- use the existing `DraftVariant` table for the first single-source Ghost article draft slice
- represent Ghost as a manual-only `ghost` channel
- reuse existing `PublishJob` and `PublishLog` rows for manual Ghost handoff and final URL recording
- keep multi-source daily briefs out of this first schema shape until a later task can add explicit multi-source provenance

This first model stays within these constraints:
- start from review-led manual handoff, not live platform publishing
- preserve source provenance for every source item used in a long-form draft
- keep approval separate from publication or URL recording
- support `single_story_explainer` first, with `country_daily_brief` deferred until multi-source provenance has an explicit model
- store a canonical external URL only after manual Ghost publication is confirmed
- keep X, Threads, and LinkedIn drafts pointed at the original article URL rather than the recorded Ghost URL

The smallest safe path is:
1. Generate a long-form draft from one or more country-news briefs.
2. Show source attribution and source URLs in review context.
3. Let an operator approve, reject, or edit the long-form draft.
4. Create a manual Ghost handoff record for approved drafts.
5. Let the operator record the final Ghost URL after publishing outside the app.

Implemented first slice:
- `ghost` is configured for Korea/Japan country-news accounts with a 12,000 character cap, 8-link review allowance, and `backlog_target: 0`.
- `ghost` drafts use long-form prompt constraints and stay in `pending_review`.
- approving a `ghost` draft creates a manual handoff publish job.
- scheduler/backfill live publishing does not pick up `ghost` handoffs.

## Explicit Boundaries
- No live Ghost or WordPress API publish happens in Task 01 or Task 02.
- No Substack, beehiiv, Medium, Reddit, or Hacker News automation is added.
- Existing X, Threads, and LinkedIn behavior stays independent and source-linked.
- X, Threads, and LinkedIn continue to link to original source URLs; blog-funnel mode is not part of this phase.
- Any future adapter must support dry-run behavior before live posting.

## Task 02 Starting Assumptions
- Prefer a schema-backed long-form model if multi-source provenance cannot be represented cleanly by the existing one-source `content_briefs` table.
- Reuse the existing review and manual publish-job patterns where they fit, but avoid forcing long-form articles into short-form channel validators.
- Use `ghost` or `ghost_blog` as a publishing destination name only after the model design chooses the storage shape.
- Keep all platform-specific request payloads out of YAML until an adapter task explicitly needs them.
