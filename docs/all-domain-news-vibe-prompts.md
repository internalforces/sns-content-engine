# All-Domain News Autonomous Vibe Coding Pack

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in [docs/all-domain-news-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-todo.md), inspect the repository, choose the correct implementation shape, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they tell the agent where to look first,
- they constrain scope so one task does not sprawl,
- they require verification,
- they preserve the existing finance-local MVP unless a task explicitly extends it.

Progress for live implementation should be tracked in:
- [docs/all-domain-news-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-progress.md)

## Repository Context
The repository already has a working finance-local MVP with:
- config-driven source loading,
- source connectors for RSS, sitemap, and manual CSV,
- ingest, enrich, brief, draft, review, scheduler, and history workflows,
- SQLAlchemy ORM persistence,
- Pydantic config schemas,
- a strong targeted unit test pattern.

Important current files and patterns:
- Config schemas: [app/config/schemas.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/schemas.py)
- Config loading: [app/config/loaders.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/loaders.py)
- Source connectors: [app/connectors/sources/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/sources)
- LLM providers: [app/connectors/llm/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/llm)
- Routing: [app/connectors/routing/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/routing)
- Storage models: [app/storage/models.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/models.py)
- Workflows: [app/workflows/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows)
- Existing roadmap: [docs/all-domain-news-todo.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-todo.md)

High-signal tests already exist and should be reused instead of inventing new test structure:
- [tests/test_config.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_config.py)
- [tests/test_source_connectors.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_source_connectors.py)
- [tests/test_ingest_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_ingest_workflow.py)
- [tests/test_storage.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_storage.py)
- [tests/test_enrich_articles_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_enrich_articles_workflow.py)
- [tests/test_phase6_config_routing.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_phase6_config_routing.py)
- [tests/test_prompt_renderer.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_prompt_renderer.py)
- [tests/test_generate_drafts_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_generate_drafts_workflow.py)
- [tests/test_x_draft_generator.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_x_draft_generator.py)
- [tests/test_draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_draft_validation.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)
- [tests/test_history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_history_queries.py)

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the relevant code paths before editing.
- Prefer the smallest implementation that fits existing architecture.
- Keep each task self-contained and merge-friendly.
- Preserve backwards compatibility where existing configs or workflows depend on current defaults.
- Avoid renaming public concepts unless the task requires it.

### Scope control
- Do not do roadmap items that belong to later tasks unless required for a clean implementation.
- If a small supporting change is needed in an adjacent module, make it, but keep it narrowly justified.
- Do not redesign the whole pipeline when an additive change works.

### Safety constraints
- Preserve the current finance-local MVP flow and tests.
- Keep manual review as the default publish gate.
- Do not introduce auto-publish behavior.
- Do not silently weaken validation or review checks.

### Testing rules
- Add or update targeted tests for every behavior change.
- Run the narrowest relevant test set first.
- If a shared abstraction changed, run one broader regression slice too.
- If a test cannot be run, state exactly why.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-source-policy-schema`
  - `codex/task-04-gdelt-discovery-connector`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Use a clear commit message tied to the task outcome, for example:
  - `Add source policy fields to source config`
  - `Add GDELT discovery source connector`
  - `Gate enrichment by source policy`

### Completion rules
- Only finish after code changes and verification are done.
- Report:
  - what changed,
  - why the shape was chosen,
  - tests run,
  - any remaining follow-up intentionally deferred.

## Progress Tracking Rules
The agent must keep [docs/all-domain-news-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-progress.md) updated while implementing this roadmap.

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
1. Task 01: Source policy schema
2. Task 02: Policy persistence
3. Task 03: All-domain example config
4. Task 04: GDELT discovery connector
5. Task 05: Policy-aware enrichment gating
6. Task 06: Codex-Wrapper provider
7. Task 07: Provider routing support
8. Task 08: All-domain prompt profiles
9. Task 09: Provenance visibility
10. Task 10: Domain sensitivity guardrails
11. Task 11: Review scheduling validation
12. Task 12: History query expansion and operator docs

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the all-domain news roadmap in this repository.

Start by reading:
- docs/all-domain-news-todo.md
- docs/all-domain-news-vibe-prompts.md
- docs/all-domain-news-progress.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/all-domain-news-vibe-prompts.md.

Your job:
1. Determine the next unfinished task in the recommended order.
2. Create or switch to a dedicated task branch using the git workflow rules in docs/all-domain-news-vibe-prompts.md.
3. Update docs/all-domain-news-progress.md to mark that task in progress and note the intended scope and active branch.
4. Implement only that task cleanly and completely.
5. Keep docs/all-domain-news-progress.md updated during the work with changed files and key progress notes.
6. Add or update targeted tests.
7. Run relevant tests and record them in docs/all-domain-news-progress.md.
8. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
9. Mark the task complete in docs/all-domain-news-progress.md when verified, including branch and commit details.
10. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve the current finance-local MVP
- keep manual review as the default gate
- avoid broad refactors
- do not spill into later roadmap items unless required for correctness

If the next task is ambiguous, choose the smallest sensible interpretation that matches the roadmap and current codebase.
```

## Milestone Prompt
Use this when you want the agent to complete a safe first milestone instead of one isolated unit.

```text
Implement the first safe all-domain review-only milestone described in docs/all-domain-news-todo.md.

Before editing:
- inspect the repository structure and current implementations
- identify which pieces of the milestone are already present and which are missing
- create or switch to a dedicated milestone branch
- update docs/all-domain-news-progress.md with the milestone scope and current active task

Then complete only the missing work needed for this milestone:
- source policy config
- policy persistence
- GDELT discovery-only support
- policy-aware enrichment skips
- Codex-Wrapper draft generation
- codex_wrapper routing support
- manual review still required for every post

Constraints:
- preserve the finance-local MVP
- no auto-publish expansion
- no broad architecture rewrite
- prefer additive changes
- add focused tests for each changed behavior
- keep docs/all-domain-news-progress.md updated as work proceeds
- make intentional commits as milestone slices are completed

At the end, report:
- completed milestone scope
- changed files
- tests run
- branch and commit details
- remaining roadmap items not included
```

## Task 01: Source Policy Schema

### Objective
Add policy metadata to source config so downstream workflows can reason about source reuse and rewrite permissions.

### Relevant code
- [app/config/schemas.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/schemas.py)
- [app/config/loaders.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/loaders.py)
- [tests/test_config.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_config.py)

### Expected result
- every source type can carry policy metadata
- defaults are explicit
- existing config continues to load
- invalid policy values fail clearly

### Autonomous prompt
```text
Implement Task 01 from docs/all-domain-news-todo.md.

Read the current source schema implementation first in app/config/schemas.py and the existing config tests in tests/test_config.py.

Add source-policy metadata to all supported source config variants. Support:
- policy_mode: discovery_only | reusable | restricted
- allow_full_text_fetch: bool
- allow_llm_rewrite: bool
- require_attribution: bool
- notes: optional string

Implementation requirements:
- preserve backward compatibility for existing config files through explicit defaults
- keep the schema style consistent with the rest of the file
- validate string fields the same way nearby config fields are validated
- do not refactor unrelated config structures

Testing requirements:
- update or add focused tests in tests/test_config.py
- cover default behavior, explicit overrides, and invalid policy_mode values
- keep tests aligned with the repository's current fixture style

Finish only when code and tests are complete.
End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 02: Policy Persistence

### Objective
Persist policy metadata and policy decision reasons so later history, review, and operator views can explain why an item was enriched, skipped, or rewrite-blocked.

### Relevant code
- [app/storage/models.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/models.py)
- [app/storage/repositories.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/repositories.py)
- [tests/test_storage.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_storage.py)

### Expected result
- storage captures source policy metadata and policy decisions in a practical place
- retrieval works through existing repository access patterns
- schema remains coherent with current model design

### Autonomous prompt
```text
Implement Task 02 from docs/all-domain-news-todo.md.

Read the current ORM and repository patterns first, especially app/storage/models.py and tests/test_storage.py.

Persist source-policy metadata and policy decision fields with the smallest consistent schema change that supports future review/history visibility.

At minimum, make room for:
- source policy mode
- allow_full_text_fetch
- allow_llm_rewrite
- require_attribution
- policy decision reason

Implementation requirements:
- choose the persistence location intentionally instead of scattering duplicate fields everywhere
- keep naming future UI-friendly
- do not wire unrelated workflow behavior unless needed to support the model cleanly

Testing requirements:
- add or update tests in tests/test_storage.py
- cover insert/read behavior for the new metadata
- cover update or idempotent behavior if relevant to the chosen design

If the schema change affects table expectations, update the relevant tests.
End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 03: All-Domain Example Config

### Objective
Add a sample all-domain configuration set that demonstrates safe source-policy usage without changing the default active config.

### Relevant code
- [config/examples/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/config/examples)
- [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md)
- [tests/test_config.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_config.py)

### Expected result
- a new example config directory exists
- example sources show policy modes clearly
- documentation explains that examples are not production defaults

### Autonomous prompt
```text
Implement Task 03 from docs/all-domain-news-todo.md.

Inspect the existing example config layout first, especially config/examples/finance_local/.

Create a new example config directory for all-domain news operation. It should demonstrate:
- reusable official or government style feeds
- reusable corporate newsroom or investor-relations style feeds
- a Wikinews-style example with attribution-friendly policy settings
- a placeholder future GDELT discovery-only source

Requirements:
- do not replace or mutate the active default config directory
- keep sample URLs obviously non-production where needed
- use the new source policy fields consistently
- add documentation in the most natural place, either a local README or the root README

Testing requirements:
- if the repository validates bundled sample configs, add/update the relevant tests
- otherwise keep validation changes minimal

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 04: GDELT Discovery Connector

### Objective
Add a discovery-only connector for GDELT-style recent news that normalizes items into the existing source candidate flow.

### Relevant code
- [app/connectors/sources/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/sources)
- [app/connectors/sources/registry.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/sources/registry.py)
- [app/config/schemas.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/config/schemas.py)
- [tests/test_source_connectors.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_source_connectors.py)
- [tests/test_ingest_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_ingest_workflow.py)

### Expected result
- a new source type exists
- the connector emits normalized candidates
- error handling matches current connector conventions

### Autonomous prompt
```text
Implement Task 04 from docs/all-domain-news-todo.md.

Read the existing source connectors first, especially the patterns in app/connectors/sources/ and tests/test_source_connectors.py.

Add a GDELT discovery connector as a new source type. It should:
- fetch and parse GDELT-style discovery data
- normalize output into the same candidate model used by current connectors
- remain discovery-only in scope

Requirements:
- register the connector through the existing source registry pattern
- add only the minimum config surface required for this source type
- keep failure reporting readable and consistent with RSS and sitemap connectors
- do not implement article fetching here

Testing requirements:
- add focused tests for successful normalization
- add tests for malformed or empty data
- add registry integration coverage if the current suite expects it

If the exact GDELT payload shape requires an assumption, document the assumption in the task summary.
End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 05: Policy-Aware Enrichment Gating

### Objective
Make enrichment intentionally skip items when policy disallows full-text fetch or rewrite, instead of treating them like ordinary failures.

### Relevant code
- [app/workflows/enrich_articles.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/enrich_articles.py)
- [app/storage/models.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/models.py)
- [tests/test_enrich_articles_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_enrich_articles_workflow.py)

### Expected result
- policy-blocked items are skipped intentionally
- skip reasons are persisted cleanly
- reusable items still enrich as before

### Autonomous prompt
```text
Implement Task 05 from docs/all-domain-news-todo.md.

Inspect the current enrich_articles workflow and its tests first.

Update enrichment so source policy can intentionally block:
- full-text fetch
- rewrite or summary generation when not allowed

Requirements:
- preserve current behavior for allowed reusable sources
- distinguish intentional policy skips from technical failures
- persist human-readable skip reasons
- keep the workflow easy to follow without spreading policy logic into unrelated layers

Testing requirements:
- add or update tests in tests/test_enrich_articles_workflow.py
- cover allowed enrichment
- cover blocked full-text fetch
- cover blocked rewrite
- cover existing completed enrichments remaining stable

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 06: Codex-Wrapper Provider

### Objective
Add a draft-generation LLM provider that talks to an OpenAI-compatible Codex-Wrapper endpoint.

### Relevant code
- [app/connectors/llm/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/llm)
- [app/connectors/llm/resolver.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/llm/resolver.py)
- [tests/test_openai_llm_provider.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_openai_llm_provider.py)
- [tests/test_generate_drafts_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_generate_drafts_workflow.py)

### Expected result
- provider can be instantiated from env
- request building matches current provider abstractions
- errors surface consistently

### Autonomous prompt
```text
Implement Task 06 from docs/all-domain-news-todo.md.

Inspect the existing OpenAI and Anthropic provider implementations first so the new provider matches repository conventions.

Add app/connectors/llm/codex_wrapper_provider.py for draft generation using an OpenAI-compatible endpoint such as /v1/chat/completions.

Support environment variables such as:
- CODEX_WRAPPER_BASE_URL
- CODEX_WRAPPER_API_KEY
- CODEX_WRAPPER_MODEL
- optional timeout or reasoning settings if they fit the existing provider style

Requirements:
- keep the implementation scoped to draft generation
- follow current provider error handling patterns
- avoid breaking OpenAI, Anthropic, or Fake paths

Testing requirements:
- add focused unit tests for environment-based setup
- cover request payload construction
- cover upstream failure mapping

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 07: Provider Routing Support

### Objective
Allow `provider: codex_wrapper` in routing and provider resolution for draft generation.

### Relevant code
- [app/connectors/llm/resolver.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/llm/resolver.py)
- [app/connectors/routing/registry.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/connectors/routing/registry.py)
- [config/providers.yaml](/Users/sonmyeong-gwan/Desktop/sns-content-engine/config/providers.yaml)
- [tests/test_phase6_config_routing.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_phase6_config_routing.py)

### Expected result
- codex_wrapper routes resolve correctly
- fallback chains still work
- sample config remains valid and readable

### Autonomous prompt
```text
Implement Task 07 from docs/all-domain-news-todo.md.

Inspect the existing route registry and LLM resolver first, especially how openai, anthropic, and fake are recognized.

Add support for provider: codex_wrapper in routing and resolution.

Requirements:
- update any credential-detection logic needed to recognize Codex-Wrapper
- preserve current fallback ordering behavior
- keep backward compatibility with openai, anthropic, and fake
- update config/providers.yaml only if it improves the sample configuration story

Testing requirements:
- add or update routing tests in tests/test_phase6_config_routing.py
- cover config-driven codex_wrapper resolution
- cover fallback chains that include codex_wrapper
- keep unknown provider failures clear

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 08: All-Domain Prompt Profiles

### Objective
Create neutral all-domain prompt profiles that support factual news rewriting with attribution-aware guidance.

### Relevant code
- [config/prompts.yaml](/Users/sonmyeong-gwan/Desktop/sns-content-engine/config/prompts.yaml)
- [config/examples/finance_local/prompts.yaml](/Users/sonmyeong-gwan/Desktop/sns-content-engine/config/examples/finance_local/prompts.yaml)
- [app/services/prompt_renderer.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/prompt_renderer.py)
- [tests/test_prompt_renderer.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_prompt_renderer.py)

### Expected result
- neutral news prompt profiles exist
- the renderer supports any new metadata variables required
- finance-local prompts remain intact

### Autonomous prompt
```text
Implement Task 08 from docs/all-domain-news-todo.md.

Inspect the current prompt profiles and prompt rendering tests first.

Add all-domain prompt profiles for:
- general news summary
- factual X post
- attribution-first short post

Requirements:
- do not remove or regress the current finance-local prompt behavior
- only add renderer variables that are actually needed by the new templates
- keep prompts practical, concise, and aligned with review-first operation
- remove finance-specific assumptions from the all-domain example path, not from the whole repository

Testing requirements:
- add or update tests in tests/test_prompt_renderer.py for any new variables or rendering behavior

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 09: Provenance Visibility

### Objective
Ensure generated drafts carry enough provenance for reviewers to understand origin without log inspection.

### Relevant code
- [app/workflows/generate_drafts.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/generate_drafts.py)
- [app/services/x_draft_generator.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/x_draft_generator.py)
- [app/storage/models.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/storage/models.py)
- [tests/test_generate_drafts_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_generate_drafts_workflow.py)
- [tests/test_x_draft_generator.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_x_draft_generator.py)

### Expected result
- drafts and stored metadata retain source and policy provenance
- review-facing context improves without redesigning the review system

### Autonomous prompt
```text
Implement Task 09 from docs/all-domain-news-todo.md.

Inspect current draft-generation inputs, stored draft metadata, and reviewer-visible fields first.

Improve provenance so generated drafts retain and expose:
- source name
- source URL
- article URL
- published timestamp
- policy mode

Requirements:
- follow the current generate_drafts and x_draft_generator patterns
- prefer additive metadata over broad schema churn
- do not redesign review_queue or CLI UX unless required

Testing requirements:
- add or update focused tests in tests/test_generate_drafts_workflow.py and/or tests/test_x_draft_generator.py
- verify provenance survives through generation and storage

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 10: Domain Sensitivity Guardrails

### Objective
Add lightweight high-risk domain guardrails for areas like politics, finance, health, and crime or disasters.

### Relevant code
- [app/services/prompt_renderer.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/prompt_renderer.py)
- [app/services/draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/draft_validation.py)
- [app/workflows/generate_drafts.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/generate_drafts.py)
- [tests/test_prompt_renderer.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_prompt_renderer.py)
- [tests/test_draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_draft_validation.py)

### Expected result
- high-risk topics are flagged
- prompts or validation become stricter where needed
- manual review remains the safety net

### Autonomous prompt
```text
Implement Task 10 from docs/all-domain-news-todo.md.

Inspect the current prompt rendering and draft validation flow first.

Add simple domain-sensitivity guardrails for:
- politics
- finance
- health
- crime or disasters

Requirements:
- prefer lightweight rule flags over complex classifiers
- keep the current product scope modest
- manual review must remain the default backstop
- stricter phrasing guidance or validation should only appear where justified

Testing requirements:
- add focused tests for at least one high-risk topic path
- add a neutral-topic test showing no unnecessary regression

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 11: Review Scheduling Validation

### Objective
Prevent silent scheduling of drafts that violate attribution, restriction, or provenance policy requirements.

### Relevant code
- [app/workflows/review_queue.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/review_queue.py)
- [app/services/draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/services/draft_validation.py)
- [tests/test_review_queue_workflow.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_review_queue_workflow.py)
- [tests/test_draft_validation.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_draft_validation.py)

### Expected result
- blocked policy states cannot be scheduled silently
- validation messages explain the reason clearly

### Autonomous prompt
```text
Implement Task 11 from docs/all-domain-news-todo.md.

Inspect current review_queue scheduling validation and draft validation behavior first.

Extend review and scheduling validation so drafts cannot be silently scheduled when policy requirements are violated.

Cover cases such as:
- missing attribution when required
- restricted-source full-text reuse
- missing provenance needed for safe review

Requirements:
- integrate with existing validation and review_queue flow
- preserve the current manual review semantics
- keep operator-facing messages readable and actionable

Testing requirements:
- add or update focused tests in tests/test_review_queue_workflow.py and/or tests/test_draft_validation.py
- cover at least one blocking case and one allowed case

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Task 12: History Query Expansion And Operator Docs

### Objective
Expose policy-aware history data for future UI/API usage and document how the all-domain pipeline should be operated safely.

### Relevant code
- [app/workflows/history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/app/workflows/history_queries.py)
- [tests/test_history_queries.py](/Users/sonmyeong-gwan/Desktop/sns-content-engine/tests/test_history_queries.py)
- [README.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/README.md)
- [docs/](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs)

### Expected result
- history queries can surface policy-aware information
- operator docs explain intentional skips and source-policy categories

### Autonomous prompt
```text
Implement Task 12 from docs/all-domain-news-todo.md.

Inspect the current history query helpers and operator-facing docs first.

Code goal:
- extend history query output so future UI or API layers can expose useful policy-aware fields such as policy mode, skipped-by-policy counts, rewrite provider used, and attribution-required counts where that fits the current query design

Docs goal:
- document:
  - discovery_only vs reusable vs restricted
  - when enrichment is intentionally skipped
  - what Codex-Wrapper is used for
  - why manual review still remains required

Requirements:
- keep query shapes practical and coherent with existing helpers
- avoid speculative API design
- prefer updating current docs over scattering small fragments unless a new guide is clearly cleaner

Testing requirements:
- add or update focused tests in tests/test_history_queries.py for any new query fields

End with the standard summary format from docs/all-domain-news-vibe-prompts.md.
```

## Suggested Working Pattern
When using this document operationally:
1. Run the Master Prompt to let the agent pick the next unfinished task.
2. If tighter control is needed, run a single task prompt directly.
3. Keep work scoped to one task per branch or commit when possible.
4. During active implementation, keep [docs/all-domain-news-progress.md](/Users/sonmyeong-gwan/Desktop/sns-content-engine/docs/all-domain-news-progress.md) current.
5. After each completed task, update the roadmap or progress notes.

## Operator Note
If you want the agent to continue through multiple tasks without asking each time, pair the Master Prompt with a simple instruction such as:

```text
Continue task-by-task in roadmap order. After each task, commit only if tests pass and the scope is still clean.
```
