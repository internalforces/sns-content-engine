# Finance Local MVP Assumptions

## Source list assumptions
- The production finance source list is intentionally not fixed in this MVP.
- The implementation should support configurable RSS feeds plus example/fixture entries for local testing.
- RSS metadata is discovery input only; article HTML is the preferred source of truth for summaries when fetch and extraction succeed.

## Conservative finance-domain handling
- The MVP should avoid language that looks like investment advice, price targets, or buy/sell recommendations.
- When enrichment is incomplete, the system should prefer skipping summary regeneration or draft creation over making strong unsupported claims.
- Source provenance must remain visible through source name, source URL, and article URL fields so later reviewers can verify context quickly.

## Summary and failure-message assumptions
- Regenerated summaries should be deterministic in tests and local development, even if future OpenAI-backed enrichment is added later.
- Failure records should carry both a machine-readable code and a human-readable message.
- Human-readable failure messages should be understandable by non-developers and safe to show in a future local UI.

## Data-storage assumptions for future UI expansion
- The future UI will need execution history, collected article lists, extraction results, generated summaries/briefs, generated drafts, and failure lists as separate readable units.
- This MVP should store per-stage status so the UI can explain where an item stopped without reconstructing workflow logs.
- Query/repository methods should be easy to reuse in a future backend API without depending on CLI-only output parsing.


## Example-config assumption
- The repository now includes example finance-local config files under `config/examples/finance_local/` as operator samples only.
- Those files are intentionally placeholders and must be copied and edited locally before real use.
