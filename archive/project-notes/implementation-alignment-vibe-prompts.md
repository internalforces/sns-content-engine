# Implementation Alignment Autonomous Vibe Coding Pack

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in [docs/implementation-alignment-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/implementation-alignment-todo.md), inspect the repository, choose the smallest clean fix for each mismatch, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they start from observed gaps, not hypothetical future features,
- they constrain scope so alignment work stays small and surgical,
- they require verification against both runtime behavior and docs,
- they preserve the current finance-local and all-domain behavior unless a task explicitly updates it.

Progress for live implementation should be tracked in:
- [docs/implementation-alignment-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/implementation-alignment-progress.md)

## Repository Context
The repository already has:
- a working finance-local review-first pipeline,
- an all-domain extension with source-policy support, Codex-Wrapper integration, provenance, and history-query expansion,
- CLI workflows for ingest, draft generation, review, scheduler operations, and history views,
- targeted tests around config loading, provider routing, workflows, validation, and CLI output.

Important current files and patterns:
- Config registry/loading: [app/config/registry.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/registry.py), [app/config/loaders.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/loaders.py)
- Provider routing and resolution: [app/connectors/routing/registry.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/routing/registry.py), [app/connectors/llm/resolver.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/llm/resolver.py)
- Draft workflow entrypoints: [app/workflows/generate_drafts.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/generate_drafts.py), [app/workflows/run_local_pipeline.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/run_local_pipeline.py)
- History query and CLI surfaces: [app/workflows/history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/history_queries.py), [app/cli.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/cli.py)
- Current docs to align: [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md), [docs/all-domain-news-operator-guide.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-operator-guide.md), [docs/all-domain-news-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-progress.md)
- Existing roadmap: [docs/implementation-alignment-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/implementation-alignment-todo.md)

High-signal tests already exist and should be reused instead of inventing new test structure:
- [tests/test_phase6_config_routing.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_phase6_config_routing.py)
- [tests/test_openai_llm_provider.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_openai_llm_provider.py)
- [tests/test_generate_drafts_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_generate_drafts_workflow.py)
- [tests/test_run_local_pipeline_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_run_local_pipeline_workflow.py)
- [tests/test_history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_history_queries.py)
- [tests/test_cli.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_cli.py)
- [tests/test_config.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_config.py)

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the relevant runtime path before editing.
- Prefer the smallest implementation that closes the observed mismatch cleanly.
- Keep each task self-contained and merge-friendly.
- Preserve backward compatibility when the mismatch can be resolved additively.
- Prefer fixing runtime truth over weakening documentation, unless the documented behavior is intentionally out of scope.

### Scope control
- Do not broaden alignment work into unrelated roadmap expansion.
- If a mismatch can be solved either in code or docs, choose the path that leaves operator expectations and runtime behavior clearly consistent.
- Avoid refactoring stable subsystems unless the mismatch cannot be resolved otherwise.

### Safety constraints
- Preserve the current review-first publish gate.
- Do not introduce auto-publish behavior.
- Do not silently remove existing provider fallbacks.
- Keep CLI output operator-readable even when adding more detail.

### Testing rules
- Add or update targeted tests for every behavior change.
- Run the narrowest relevant test set first.
- If workflow resolution changes, run one broader regression slice that exercises the real workflow entrypoint.
- If only docs change, say so explicitly and note whether no code-path tests were needed.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-provider-config-runtime-wiring`
  - `codex/task-02-history-cli-parity`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Use a clear commit message tied to the task outcome, for example:
  - `Wire providers config into draft workflow resolution`
  - `Expose policy-aware history fields in CLI output`
  - `Refresh alignment docs and progress metadata`

### Completion rules
- Only finish after code changes and verification are done.
- Report:
  - what changed,
  - why that shape was chosen,
  - tests run,
  - any remaining follow-up intentionally deferred.

## Progress Tracking Rules
The agent must keep [docs/implementation-alignment-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/implementation-alignment-progress.md) updated while implementing this roadmap.

### When to update
- At the start of a task:
  - set the current task
  - mark status as `in_progress`
  - record the intended scope
  - record the active branch
- During implementation:
  - append meaningful progress notes when the implementation shape changes, key files are edited, or a blocker is discovered
  - update the changed-files list as files are touched
- After tests:
  - record test commands and pass/fail status
- At task completion:
  - mark the task `done`
  - summarize the final changed files
  - record the commit SHA and commit message if a commit was created
  - record follow-up items if any remain

### What to track
- current active task
- active branch
- latest commit for the task when available
- overall task status table
- files changed for the active task
- implementation notes
- test execution log
- blockers or follow-up items

### Tracking constraints
- Keep entries short and factual.
- Update the existing progress file instead of creating a new ad hoc log.
- Do not mark a task done before the relevant tests have run, unless testing is impossible and the reason is recorded explicitly.

## Output Contract For The Agent
Unless the caller requests a different format, end each task with:

```text
Summary
- ...

Changed files
- ...

Tests run
- ...

Follow-up
- ...
```

## Recommended Task Order
1. Task 01: Provider config runtime wiring
2. Task 02: Policy-aware history CLI parity
3. Task 03: README and operator wording refresh
4. Task 04: Progress metadata cleanup

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the implementation-alignment roadmap in this repository.

Start by reading:
- docs/implementation-alignment-todo.md
- docs/implementation-alignment-vibe-prompts.md
- docs/implementation-alignment-progress.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/implementation-alignment-vibe-prompts.md.

Your job:
1. Determine the next unfinished task in the recommended order.
2. Create or switch to a dedicated task branch using the git workflow rules in docs/implementation-alignment-vibe-prompts.md.
3. Update docs/implementation-alignment-progress.md to mark that task in progress and note the intended scope and active branch.
4. Implement only that task cleanly and completely.
5. Keep docs/implementation-alignment-progress.md updated during the work with changed files and key progress notes.
6. Add or update targeted tests.
7. Run relevant tests and record them in docs/implementation-alignment-progress.md.
8. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
9. Mark the task complete in docs/implementation-alignment-progress.md when verified, including branch and commit details.
10. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve the current finance-local MVP
- keep manual review as the default gate
- avoid broad refactors
- do not expand scope beyond the observed alignment gap unless required for correctness

If the next task is ambiguous, choose the smallest sensible interpretation that best aligns documented behavior and actual runtime behavior.
```

## Milestone Prompt
Use this when you want the agent to complete the first operator-visible alignment milestone instead of one isolated unit.

```text
Implement the first operator-visible alignment milestone described in docs/implementation-alignment-todo.md.

Before editing:
- inspect the repository structure and current implementations
- identify which pieces of the alignment milestone already exist and which are still missing
- create or switch to a dedicated milestone branch
- update docs/implementation-alignment-progress.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- real providers.yaml runtime support for draft generation
- policy-aware history details visible from the CLI
- README and operator docs updated to match the resulting runtime truth

Constraints:
- preserve the finance-local and all-domain review-first behavior
- no provider-surface redesign beyond what is needed for runtime parity
- no broad architecture rewrite
- prefer additive changes
- add focused tests for each changed behavior
- keep docs/implementation-alignment-progress.md updated as work proceeds
- make intentional commits as milestone slices are completed

At the end, report:
- completed milestone scope
- changed files
- tests run
- branch and commit details
- remaining roadmap items not included
```

## Task 01: Provider Config Runtime Wiring

### Objective
Make live draft-generation workflows honor optional `providers.yaml` routing so runtime behavior matches the route registry, config schema, and existing tests.

### Relevant code
- [app/config/loaders.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/loaders.py)
- [app/config/registry.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/registry.py)
- [app/connectors/llm/resolver.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/llm/resolver.py)
- [app/workflows/generate_drafts.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/generate_drafts.py)
- [tests/test_phase6_config_routing.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_phase6_config_routing.py)
- [tests/test_generate_drafts_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_generate_drafts_workflow.py)

### Expected result
- `providers.yaml` is loaded on the real draft-generation path when present
- env-only fallback still works when the file is absent
- runtime workflow tests prove the configured route actually affects provider selection

### Autonomous prompt
```text
Implement Task 01 from docs/implementation-alignment-todo.md.

Read the current runtime path first in:
- app/config/registry.py
- app/connectors/llm/resolver.py
- app/workflows/generate_drafts.py

The mismatch to fix is:
- providers.yaml routing exists in schema/registry/resolver tests
- but generate_drafts() still resolves draft providers without using config-driven routes

Make the smallest clean change that lets the workflow honor optional providers.yaml config while preserving env-only fallback when the file is absent.

Requirements:
- keep the public workflow API stable unless a very small additive parameter is clearly justified
- preserve existing fake-provider fallback behavior
- add focused tests for the real workflow path
- run at least one broader regression slice after the narrow tests

Do not expand into unrelated provider or scheduler changes.
```

## Task 02: Policy-Aware History CLI Parity

### Objective
Bring CLI-visible history output closer to the richer policy-aware data already returned by the history-query layer.

### Relevant code
- [app/workflows/history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/history_queries.py)
- [app/cli.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/cli.py)
- [tests/test_history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_history_queries.py)
- [tests/test_cli.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_cli.py)

### Expected result
- `history runs` shows policy-aware summary details when available
- `history failures` exposes intentional policy skips or another clearly documented equivalent
- CLI output remains readable for operators

### Autonomous prompt
```text
Implement Task 02 from docs/implementation-alignment-todo.md.

Inspect:
- app/workflows/history_queries.py
- app/cli.py
- tests/test_cli.py

The mismatch to fix is:
- the query layer already returns policy-aware fields
- but the CLI still prints only the older narrow summaries

Choose the smallest operator-friendly output shape that closes this gap. Prefer additive output over a CLI redesign.

Requirements:
- keep the commands easy to scan in a terminal
- add or update focused CLI tests
- preserve backward compatibility as much as practical
- explicitly account for policy skips, not only technical failures

Do not redesign the entire history command group.
```

## Task 03: README And Operator Wording Refresh

### Objective
Update docs so they describe the actual post-alignment runtime behavior without stale caveats or pre-alignment wording.

### Relevant code
- [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md)
- [docs/all-domain-news-operator-guide.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-operator-guide.md)
- [docs/finance-local-ui-data-contract.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/finance-local-ui-data-contract.md)
- [docs/implementation-alignment-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/implementation-alignment-todo.md)

### Expected result
- no outdated wording about policy-aware enrichment skips being unavailable
- provider-resolution documentation matches the implemented runtime path
- operator docs and README tell the same story

### Autonomous prompt
```text
Implement Task 03 from docs/implementation-alignment-todo.md.

Read the current wording in:
- README.md
- docs/all-domain-news-operator-guide.md
- any nearby docs touched by the final runtime behavior

Refresh only the wording needed to match the implemented behavior after Tasks 01 and 02.

Requirements:
- prefer factual wording over aspirational wording
- keep the docs concise and operator-facing
- avoid broad documentation rewrites
- if behavior differs by workflow, say that explicitly

If no code changes are required, state that clearly and record any tests or validation you did not need to run.
```

## Task 04: Progress Metadata Cleanup

### Objective
Refresh stale progress metadata and alignment notes so the repository's status documents do not contradict the current branch history.

### Relevant code
- [docs/all-domain-news-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-progress.md)
- [docs/implementation-alignment-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/implementation-alignment-progress.md)
- [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md)

### Expected result
- progress trackers reference the correct latest commit/task state when marked done
- alignment notes are updated only where facts are stale
- no historical rewrite beyond what is necessary for consistency

### Autonomous prompt
```text
Implement Task 04 from docs/implementation-alignment-todo.md.

Inspect the current progress and status docs and compare them against the actual branch HEAD and the work completed by prior alignment tasks.

Update only stale factual metadata such as:
- latest task commit
- active branch/task status
- small completion notes that would otherwise contradict the repository state

Requirements:
- keep edits factual and minimal
- do not rewrite the whole historical log
- preserve the existing progress-file structure

If there is a subtle tradeoff between perfect historical preservation and current factual accuracy, prefer factual accuracy and note the choice briefly.
```
