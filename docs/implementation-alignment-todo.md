# Implementation Alignment TODO

## Goal
Align the repository's operator-facing documentation, prompt-pack expectations, and actual runtime behavior so the documented capabilities match what the CLI and workflows really do today.

This roadmap focuses on the gaps currently visible between:
- the all-domain and README documentation,
- the workflow/runtime code paths,
- the CLI surfaces that operators actually see.

## Current implementation snapshot

### Already implemented
- Source-policy config, persistence, and policy-aware enrichment skips.
- Codex-Wrapper draft provider and route-registry support.
- All-domain prompt profiles, provenance capture, and schedule-time policy validation.
- Policy-aware history query helpers for future UI/API use.

### Current mismatches to resolve
- `providers.yaml` routing exists as config/schema/registry behavior, but the `generate-drafts` and `run-local` workflow path still resolves draft providers from environment-only defaults.
- `history runs` and `history failures` query helpers expose policy-aware fields, but the CLI currently prints only the older narrow summaries.
- Some docs still describe pre-alignment behavior:
  - GDELT notes still imply policy-aware enrichment skips are not enabled.
  - README draft-generation wording is centered on env auto-detection and does not explain the current config-routing intent clearly.
- The all-domain progress tracker's latest commit metadata is stale relative to the current branch HEAD.

## Target outcome

### Runtime alignment
1. Operator-configured provider routing should affect actual draft-generation runs.
2. CLI history output should expose the same high-value policy fields the query layer already returns.

### Documentation alignment
3. Operator docs and README should describe the post-alignment runtime truth without outdated caveats.
4. Progress and status docs should reflect the latest known branch/commit state when marked complete.

## TODO roadmap

## Phase 1: Runtime behavior parity

### 1. Wire `providers.yaml` into runtime draft-generation resolution
- Load the optional providers config in the workflow path that currently builds the draft provider.
- Ensure `generate-drafts` and `run-local` honor `provider: codex_wrapper` or other configured route chains at runtime, not just in isolated resolver tests.
- Preserve current fallback behavior when `providers.yaml` is absent.
- Done when:
  - config-driven routing changes live workflow provider selection,
  - env-only fallback still works,
  - tests cover the workflow path, not just the route registry.

### 2. Surface policy-aware history fields in CLI output
- Extend `history runs` to print policy-mode counts, skipped-by-policy count, attribution-required count, and rewrite providers when present.
- Extend `history failures` to expose intentional policy skips or add a clearly documented CLI output shape that makes them accessible.
- Keep the output easy to scan for operators.
- Done when:
  - the CLI reflects the same policy-aware data contract already exposed by `history_queries`,
  - tests cover the updated terminal output.

## Phase 2: Documentation and tracker parity

### 3. Refresh README and operator wording to match current runtime behavior
- Remove or update outdated caveats that still describe pre-alignment limitations.
- Clarify how env auto-detection and optional `providers.yaml` routing interact after runtime wiring is complete.
- Update GDELT/discovery wording so it matches the current policy-skip implementation.
- Done when:
  - README and operator docs no longer overstate or understate available behavior,
  - example usage text matches the implemented path.

### 4. Refresh progress metadata and alignment notes
- Update stale progress metadata such as latest commit references when the related task is finalized.
- Add short alignment notes where useful so future roadmap work does not inherit stale assumptions.
- Keep this limited to factual tracking updates, not broad historical rewrites.
- Done when:
  - progress docs reflect the current branch/commit truth,
  - new alignment work has a clear tracked completion point.

## Suggested execution order
1. Runtime provider-config wiring.
2. Policy-aware history CLI parity.
3. README and operator-guide refresh.
4. Progress metadata cleanup.

## Recommended first milestone
Ship a small "operator-visible parity" milestone with:
- real `providers.yaml` runtime support for draft generation,
- richer `history runs` / `history failures` CLI output,
- doc wording updated to match the resulting behavior.

This keeps the work focused on closing the highest-signal gaps before doing any broader feature expansion.
