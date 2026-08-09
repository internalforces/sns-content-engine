# Documentation Map

This page separates current operator documentation from completed initiative records. Runtime behavior is defined by the code, checked-in config, and tests; planning documents are not a promise that every idea described in them is implemented.

## Current Sources Of Truth

- [Project README](../README.md): supported channels, setup, CLI commands, safety defaults, and current boundaries.
- [Operator console guide](operator-console-guide.md): browser review, Ghost/LinkedIn/Threads manual handoff, scheduling, and publish-job outcome recording.
- [Operator control-plane API](operator-control-plane-api.md): JSON read/action routes and their safety model.
- [Single-server deployment guide](single-server-deployment-guide.md): systemd, Caddy, health checks, backup, and rollback.
- [Global country-news long-form strategy](global-country-news-phase-2-longform-platform-strategy.md): implemented Ghost manual-handoff model and original-source social-link decision.
- [Finance Local MVP guide](finance-local-operator-guide.md) and [All-domain news guide](all-domain-news-operator-guide.md): example-config-specific operating guidance.

## Current Runtime Snapshot

| Area | Implemented behavior |
| --- | --- |
| Pipeline | Discover/ingest, policy-aware enrichment, brief generation, and per-channel draft generation |
| Draft channels in active config | `x`, `ghost`, `linkedin`, `threads` |
| Live publishers | X; Threads only when its account config and env credential bundle resolve successfully |
| Manual handoffs | Ghost and LinkedIn always; Threads when no live publisher resolves |
| Long-form | Single-source Ghost drafts, manual publication, and final URL recording |
| Social links | X, Threads, and LinkedIn keep the original article URL |
| Safety | Manual review; `publish-due` dry-run by default; secrets supplied through environment variables |
| Operator surfaces | CLI, FastAPI JSON API, and server-rendered browser console |

## Completed Initiative Records

The following families describe how shipped capabilities were planned and verified. Their progress trackers are audit records; do not treat old "current task," branch, or rollout wording as the current operator contract.

- `implementation-alignment-*`
- `api-operations-readiness-*`
- `operator-control-plane-readiness-*`
- `operator-console-readiness-*`
- `multichannel-manual-publish-readiness-*`
- `threads-api-publish-readiness-*`
- `first-live-rollout-readiness-*` and `first-live-rollout-operations-*`
- `single-server-deployment-readiness-*`
- `global-country-news-phase-0-*`, `global-country-news-phase-1-*`, and `global-country-news-phase-1-5-*`
- `global-country-news-phase-2-longform-publishing-funnel-*`

Some roadmap and execution-guide files retain pre-implementation wording intentionally so the original plan remains auditable. Read the matching progress tracker and the current source-of-truth guides above before acting on them.

## Known Unimplemented Boundaries

- No live Ghost or LinkedIn publisher adapter.
- No multi-source long-form provenance model or daily/weekly brief aggregation.
- No automatic blog-funnel replacement of social source URLs.
- No automatic Substack, beehiiv, Medium, Reddit, or Hacker News publishing.
- No standalone CLI stage for TTS or metadata generation.
