# First Live Rollout Readiness Vibe Coding Prompt

## Purpose
This document is the kickoff brief for an autonomous coding agent working in an existing repository.

Use it when you want the agent to absorb the product intent quickly, inspect the real codebase, shape the smallest safe implementation slice, and start coding with minimal back-and-forth.

The prompt below is intentionally opinionated:
- it starts from the current repository instead of inventing a blank-slate rewrite
- it prefers additive changes over broad redesigns
- it preserves the manual-review gate, dry-run-first publish defaults, and env-only secret handling
- it turns vague rollout intent into a roadmap, execution guide, progress tracker, and first implementation slice

## Generated document naming
When instantiating this template, keep the document names explicit so each file is easy to identify at a glance.

- Vibe coding prompt file: `docs/first-live-rollout-readiness-vibe-coding-prompt.md`
- Roadmap file: `docs/first-live-rollout-readiness-roadmap.md`
- Execution guide file: `docs/first-live-rollout-readiness-execution-guide.md`
- Progress tracker file: `docs/first-live-rollout-readiness-progress-tracker.md`
- Avoid ambiguous names like `prompt.md`, `brief.md`, `notes.md`, or `plan.md` when multiple initiatives may coexist.

## Initiative Brief
- Initiative name: `First Live Rollout Readiness`
- One-sentence outcome: `Make the current SNS content engine ready for its first protected live rollout by restoring a green baseline, hardening provider setup, and documenting X-only rollout guardrails.`
- Why this matters now:
  - The repository already has the one-server deployment baseline, but a few release blockers still make the first live rollout fragile.
  - The remaining work is narrow enough that it should be handled as a small hardening initiative instead of another broad deployment redesign.
- Primary user, operator, or workflow owner:
  - the solo operator preparing the first live rollout
  - an autonomous coding agent finishing the last hardening slices with minimal supervision
- Core workflow to improve:
  - align default config and tests so the repo is green again
  - make production provider setup explicit and safe
  - clarify that the first live rollout is `X` only
  - run a short preflight before enabling live publishing
- Explicit non-goals:
  - Threads live-publish enablement
  - in-app auth or multi-user permissions
  - Docker, Kubernetes, or broader infrastructure redesign

## Repository Context
The repository already has:
- a FastAPI app, scheduler runtime, CLI workflows, and checked-in one-server deployment assets
- environment-based secret handling and provider-routing logic
- a completed `single-server-deployment-readiness` documentation set
- high-signal tests for config, provider routing, CLI, deployment assets, and scripts

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/api/app.py`
- Existing workflows or services: `app/workflows/generate_drafts.py`, `app/workflows/run_local_pipeline.py`
- Data or schema surfaces: `app/storage/database.py`, `app/storage/bootstrap.py`
- Current placeholder, gap, or friction points: `tests/test_config.py`, `.github/workflows/secret-scan.yml`, `config/providers.yaml`, `.env.production.example`
- Existing tests to reuse first: `tests/test_config.py`, `tests/test_phase6_config_routing.py`, `tests/test_deploy_assets.py`, `tests/test_cli.py`
- Existing docs to align with: `README.md`, `docs/single-server-deployment-guide.md`, `docs/operator-console-guide.md`

## Product Intent And Quality Bar
The desired implementation should:
- make `./.venv/bin/pytest -q` green again
- give operators one unambiguous production provider path
- treat blank provider env values safely instead of failing late
- make the first live rollout checklist short, explicit, and consistent with the checked-in deployment assets

The agent should preserve:
- the manual review gate
- dry-run-first publish semantics
- environment-only secret handling

The agent should avoid:
- a broad deployment redesign
- speculative new provider abstractions
- expanding live-publish scope beyond `X` for this initiative
- unsafe shortcuts that weaken review or rollout safety

## Execution Constraints
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands:
  - `./.venv/bin/pytest tests/test_config.py -q`
  - `./.venv/bin/pytest tests/test_phase6_config_routing.py tests/test_env.py -q`
  - `./.venv/bin/pytest tests/test_deploy_assets.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest -q`
- Required local services:
  - `none for docs, config, and default test work`
  - `real provider credentials only when intentionally verifying live provider selection`
- Required env files, secrets, or fixtures:
  - `.env` for local overrides when needed
  - `.env.production.example` as the production template to keep aligned
  - live provider or publisher credentials only for explicit live-verification tasks
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Expected Agent Behavior
- Inspect the current code path before proposing or making edits.
- Reuse existing repository patterns, workflows, tests, and docs before introducing new abstractions.
- Prefer the smallest clean implementation slice that moves the initiative forward safely.
- Create or refine the roadmap, execution guide, and progress tracker before large implementation work if they do not already exist.
- Update the roadmap and progress tracker when the implementation shape changes materially.
- Keep branch, commit, and staging scope limited to the active task.
- Record blockers clearly instead of forcing completion through unsafe shortcuts.

## First-Pass Definition Of Done
For the first meaningful iteration, aim to finish when:
- `docs/first-live-rollout-readiness-roadmap.md` exists and reflects the current implementation shape
- `docs/first-live-rollout-readiness-execution-guide.md` exists and contains repo-specific execution rules
- `docs/first-live-rollout-readiness-progress-tracker.md` exists and is updated with current task status
- the first implementation slice is complete, or the exact blocker is documented clearly
- targeted tests have run, or the reason testing could not run is recorded explicitly
- the final report explains what changed, why that shape was chosen, and what remains deferred

## Prompt Template
Copy, adapt, and send the block below to the agent when starting or resuming work.

```text
You are working in an existing repository, not a blank project.

Read this document first:
- docs/first-live-rollout-readiness-vibe-coding-prompt.md

Then inspect and use these companion docs when they exist:
- docs/first-live-rollout-readiness-roadmap.md
- docs/first-live-rollout-readiness-execution-guide.md
- docs/first-live-rollout-readiness-progress-tracker.md

Your job is to turn the initiative into the smallest clean implementation slice that can be shipped safely.

Initiative brief
- Name: First Live Rollout Readiness
- Outcome: Make the current SNS content engine ready for its first protected live rollout by restoring a green baseline, hardening provider setup, and documenting X-only rollout guardrails.
- Why now:
  - The one-server deployment baseline already exists, so the remaining work is narrow and high leverage.
  - A stale config test, missing pytest CI, and provider-env ambiguity still make the first live rollout riskier than it should be.
- Core workflow to improve:
  - align default config and tests
  - harden provider and env behavior
  - document X-only live rollout scope
  - add a short preflight checklist
- Explicit non-goals:
  - Threads live rollout
  - auth or infrastructure redesign

Repository context
- Existing capabilities:
  - FastAPI app, scheduler runtime, CLI workflows, and checked-in single-server deployment assets already exist
  - provider routing and env-based secret handling already exist
  - deployment and operator docs already cover the one-server baseline
- Important files and patterns:
  - app/cli.py
  - app/connectors/routing/registry.py
  - app/connectors/llm/resolver.py
  - tests/test_config.py
  - tests/test_phase6_config_routing.py
  - README.md

Quality bar
- Preserve:
  - manual review
  - dry-run-first publish behavior
  - env-only secret handling
- Prefer:
  - additive changes
  - repo-backed tests and docs
- Avoid:
  - broad redesigns
  - expanding live-publish scope beyond X

Execution expectations
- Inspect the current implementation before editing.
- Reuse existing workflows, tests, and schema shapes where possible.
- Choose the smallest additive slice that satisfies the goal safely.
- Create or refine the roadmap, execution guide, and progress tracker if they are missing or stale.
- Update the progress tracker while working.
- Run the narrowest relevant tests first, then one broader regression slice if shared behavior changed.
- Do not push or open a PR unless explicitly asked.

Environment constraints
- Base branch: master
- Bootstrap commands:
  - python -m pip install -e ".[dev]"
  - ./.venv/bin/python -m app.cli version
- Narrow verification commands:
  - ./.venv/bin/pytest tests/test_config.py -q
  - ./.venv/bin/pytest tests/test_phase6_config_routing.py tests/test_env.py -q
  - ./.venv/bin/pytest tests/test_deploy_assets.py -q
- Broader regression commands:
  - ./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_scripts.py -q
  - ./.venv/bin/pytest -q
- Required services:
  - none by default
- Required env or fixtures:
  - .env only when needed
  - .env.production.example must stay aligned with docs
- Package install policy: ask_first
- Push and PR policy: do_not_push_without_explicit_request

Definition of done
- The next implementation slice is complete or blocked for a clearly recorded reason.
- Relevant docs are updated to match reality.
- Targeted tests are run, or the exact reason they could not run is documented.
- The final report includes:
  - what changed
  - why that implementation shape was chosen
  - tests run
  - branch and commit details
  - any intentionally deferred follow-up
```

## Recommended Instantiation Order
When using this template set for a new initiative, the usual order is:

1. Create `docs/first-live-rollout-readiness-vibe-coding-prompt.md`
2. Create `docs/first-live-rollout-readiness-roadmap.md`
3. Create `docs/first-live-rollout-readiness-execution-guide.md`
4. Create `docs/first-live-rollout-readiness-progress-tracker.md`

If some of these files already exist, refine them instead of creating duplicates.
