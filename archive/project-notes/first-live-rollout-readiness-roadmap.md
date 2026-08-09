# First Live Rollout Readiness Roadmap

## Goal
Extend the current single-server deployment baseline into a first live rollout-ready baseline that:
- restores a fully green repository baseline before rollout
- makes draft-provider and environment behavior explicit, consistent, and operator-safe
- codifies `X` as the only live-publish scope for the first rollout while keeping `LinkedIn` and `Threads` review-first
- adds repeatable CI and preflight gates so the first rollout can happen without guesswork

## Generated document naming
When instantiating this template, use a filename that clearly shows the document identity.

- Roadmap file: `docs/first-live-rollout-readiness-roadmap.md`
- Execution guide file: `docs/first-live-rollout-readiness-execution-guide.md`
- Progress tracker file: `docs/first-live-rollout-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/first-live-rollout-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `plan.md`, or `notes.md` when multiple initiatives may exist.

## Roadmap construction rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- Define only as many milestones and tasks as are needed to reach the goal while keeping each unit safely implementable.
- Choose task and milestone boundaries so the work can be completed without breaking the current architecture, workflow semantics, safety gates, or operator experience.
- Prefer the smallest additive slices that reuse the current structure instead of forcing a broad redesign.
- Split a task when it would otherwise span unrelated surfaces, require unclear rollback, or make testing too broad.
- Merge adjacent tiny tasks when they share the same code path, verification surface, and branch scope.
- If the roadmap shape changes during implementation, update this file and `docs/first-live-rollout-readiness-progress-tracker.md` before continuing.

## Current implementation snapshot

### Already implemented
- The repository already ships the FastAPI app, CLI workflows, scheduler runtime, checked-in `systemd` assets, and Caddy baseline needed for one protected server.
- `config/` is operator-ready for the current manual-source MVP and `healthcheck` passes against a fresh SQLite database.
- The project already has draft-provider routing, environment-based secrets, and a documented single-server deployment guide.
- An offline smoke run using a fake draft provider completes successfully against the current config and schema shape.

### Current limitations relevant to the new goal
- `./.venv/bin/pytest -q` is not green because `tests/test_config.py` still expects RSS-backed source sets while the current default config is manual-only.
- GitHub Actions only runs secret scanning; there is no repository-backed pytest gate for pull requests or pushes.
- `config/providers.yaml`, `.env.production.example`, and README guidance do not yet describe one obvious production draft-provider path.
- Blank provider env values such as `OPENAI_API_KEY=` can be treated as present during route selection and then fail later at provider construction time.
- The first live rollout scope is still easy to misread as multi-channel live publishing even though the current intended live path is `X` first.

## Environment and execution assumptions
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands already available:
  - `./.venv/bin/pytest tests/test_config.py -q`
  - `./.venv/bin/pytest tests/test_phase6_config_routing.py tests/test_env.py -q`
  - `./.venv/bin/pytest tests/test_deploy_assets.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest -q`
- Required local services:
  - `none for docs, config, and most test slices`
  - `live provider credentials only when a task intentionally verifies a real provider path`
- Required env files, secrets, or fixtures:
  - `.env` for local developer overrides when needed
  - `.env.production.example` as the checked-in production template
  - publisher credential bundles only when verifying live publish setup
- Package install policy: `ask_first`

## Target architecture

### Release Baseline
- `default config and tests`
  - one explicit contract for the default `config/` source sets
  - no stale expectations about RSS inputs when the repository ships manual-only source defaults
- `repository-backed CI`
  - secret scanning stays in place
  - pytest becomes a required automated baseline for normal code changes

### Provider And Rollout Safety
1. one explicit production draft-provider path is documented and reflected in checked-in examples
2. blank provider env values are handled safely instead of producing late, ambiguous failures
3. first live rollout scope is documented as `X` live publishing with other channels still review-first
4. preflight commands are easy to run and describe exactly what must pass before rollout

## Milestones
Use as many milestone blocks as needed. Keep each milestone small enough to be completed without breaking the current structure or requiring a broad redesign.

### Milestone M1: Green Release Baseline
- Goal: restore a trustworthy local and CI baseline before touching rollout semantics
- Includes:
  - default config and config-test alignment
  - repository-backed pytest workflow
- Excludes:
  - provider-routing behavior changes
  - rollout-scope documentation changes beyond what the tests require
- Verification target:
  - `./.venv/bin/pytest tests/test_config.py -q`
  - `./.venv/bin/pytest -q`
- Ship when:
  - the default config contract is consistent across code, tests, and docs
  - pull requests have a checked-in pytest gate in addition to secret scanning

### Milestone M2: Provider Hardening
- Goal: make production draft generation configuration obvious and failure-resistant
- Includes:
  - provider strategy alignment across config, env examples, and docs
  - safe handling for blank provider env values
- Excludes:
  - new provider integrations
  - changes to manual review or publish workflow semantics
- Verification target:
  - `./.venv/bin/pytest tests/test_phase6_config_routing.py tests/test_env.py -q`
  - `./.venv/bin/pytest tests/test_cli.py -q`
- Ship when:
  - one production provider path is clearly documented and testable
  - blank env values no longer produce ambiguous provider-resolution behavior

### Milestone M3: First Rollout Guardrails
- Goal: make the first live rollout easy to reason about for one operator
- Includes:
  - `X`-only live rollout scope documentation
  - a short preflight checklist aligned with the checked-in deployment assets
- Excludes:
  - Threads live publish enablement
  - automation beyond the existing smoke and dry-run surfaces
- Verification target:
  - `./.venv/bin/pytest tests/test_deploy_assets.py -q`
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_scripts.py -q`
- Ship when:
  - operators can tell exactly which channels are live in the first rollout
  - the required preflight checks are documented in one explicit place

## Implementation roadmap
Repeat the phase and task structure below as needed. Remove unused example blocks.

## Phase 1: Green Release Baseline

### Task 01: Align Default Config And Test Expectations
- Goal: make the repository's default `config/` contract explicit and keep the config tests aligned with it.
- Actions:
  - decide whether the repository default remains manual-only or restores RSS-backed source sets
  - update `config/sources.yaml`, `tests/test_config.py`, and any directly conflicting documentation to match that decision
  - confirm the chosen shape still preserves operator-ready healthcheck behavior
- Dependencies:
  - none
  - existing default config in `config/`
- Verification commands:
  - `./.venv/bin/pytest tests/test_config.py -q`
  - `./.venv/bin/pytest tests/test_cli.py -k healthcheck -q`
- Risk or rollback note:
  - avoid widening scope into source-connector redesign; only the default source-set contract should change here
- Done when:
  - `tests/test_config.py::test_registry_loads_sample_config_directory` matches the actual default config shape
  - any touched docs describe the same default source-set behavior as the code
  - `docs/first-live-rollout-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 02: Add Pytest CI Baseline
- Goal: make green local tests matter in CI by adding one repository-backed pytest workflow.
- Actions:
  - add a GitHub Actions workflow that installs project dependencies and runs `pytest -q`
  - keep the new workflow minimal and consistent with the existing secret-scan workflow
  - document or name the workflow clearly enough that operators can see the intended release gate
- Dependencies:
  - Task `01`
  - existing `.github/workflows/secret-scan.yml`
- Verification commands:
  - `./.venv/bin/pytest -q`
  - `./.venv/bin/pytest tests/test_deploy_assets.py -q`
- Risk or rollback note:
  - avoid introducing matrix builds or environment-heavy jobs until the single baseline job is stable
- Done when:
  - the repository has a checked-in pytest workflow for PRs and pushes
  - the new workflow does not remove or weaken the existing secret-scan job
  - `docs/first-live-rollout-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 2: Provider Hardening

### Task 03: Align Production Provider Strategy
- Goal: make the checked-in provider config, env template, and README describe one obvious production draft-provider path.
- Actions:
  - choose the smallest safe production story, likely `OpenAI`-first for the first rollout
  - align `config/providers.yaml`, `.env.production.example`, and README guidance with that story
  - keep secrets in env only and avoid introducing new provider abstractions
- Dependencies:
  - Task `01`
  - current provider routing in `app/connectors/routing/registry.py`
- Verification commands:
  - `./.venv/bin/pytest tests/test_phase6_config_routing.py -q`
  - `./.venv/bin/pytest tests/test_env.py tests/test_cli.py -q`
- Risk or rollback note:
  - do not break offline fake-provider behavior or the optional nature of `providers.yaml`
- Done when:
  - operators reading the checked-in examples can tell which provider path to use in production
  - config, env examples, and docs no longer point in conflicting directions
  - `docs/first-live-rollout-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 04: Harden Blank Provider Env Handling
- Goal: make provider selection robust when env keys exist but are blank.
- Actions:
  - update provider route-selection or env-validation logic so blank values are ignored or failed early in a clear way
  - add focused regression coverage for blank env, missing credentials, and production config combinations
  - keep the current fake-provider fallback and manual-review model intact
- Dependencies:
  - Task `03`
  - existing provider env helpers and route registry
- Verification commands:
  - `./.venv/bin/pytest tests/test_phase6_config_routing.py tests/test_env.py -q`
  - `./.venv/bin/pytest tests/test_cli.py -q`
- Risk or rollback note:
  - avoid changing provider priority semantics except where necessary to handle blank values safely
- Done when:
  - blank provider env values no longer lead to late, ambiguous runtime failures
  - targeted tests cover the new env-handling behavior
  - `docs/first-live-rollout-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Phase 3: First Rollout Guardrails

### Task 05: Document X-Only Live Rollout Scope
- Goal: remove ambiguity about which channels are live in the first rollout.
- Actions:
  - update README and deployment-facing docs so `X` is the only live-publish path for the first rollout
  - keep `LinkedIn` and `Threads` described as review-first or manual-fallback surfaces unless a later initiative expands them
  - align terminology across deployment and operator docs
- Dependencies:
  - Task `03`
  - existing deployment and operator docs
- Verification commands:
  - `./.venv/bin/pytest tests/test_deploy_assets.py -q`
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py -q`
- Risk or rollback note:
  - avoid promising new live publish capabilities that are not yet covered by config, tests, and operator guidance
- Done when:
  - the first rollout scope is clearly `X` live publish only
  - deployment-facing docs no longer imply immediate live Threads or LinkedIn publishing
  - `docs/first-live-rollout-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

### Task 06: Add First Rollout Preflight Checklist
- Goal: give operators one short, explicit preflight sequence for the first live rollout.
- Actions:
  - add a concise checklist covering pytest, healthcheck, dry-run publish verification, and the checked-in smoke helper
  - place the checklist in the most discoverable deployment-facing doc location
  - keep the commands copyable and aligned with the current one-server baseline
- Dependencies:
  - Task `02`
  - Task `05`
- Verification commands:
  - `./.venv/bin/pytest tests/test_deploy_assets.py -q`
  - `./.venv/bin/pytest tests/test_scripts.py tests/test_cli.py tests/test_scheduler.py -q`
- Risk or rollback note:
  - avoid adding a second conflicting deployment checklist in a different doc
- Done when:
  - operators have one short preflight sequence to follow before the first live rollout
  - the checklist references only commands and assets that already exist in the repository
  - `docs/first-live-rollout-readiness-progress-tracker.md` is updated with tests, changed files, and final status
  - a focused commit is created for the task, or the reason no commit was created is recorded explicitly

## Suggested execution order
List only the tasks that actually exist in dependency order. Add or remove lines as needed.

1. Task `01`
2. Task `02`
3. Task `03`
4. Task `04`
5. Task `05`
6. Task `06`

## Initial milestone recommendation
Start with the smallest milestone that:
- restores the failing config baseline first
- makes `pytest -q` a trustworthy local command again
- adds one CI gate before rollout-specific hardening
- can be implemented and verified without breaking the current structure

This keeps the next stage focused on making the repository green and enforceable before expanding into provider-hardening and operator-rollout guardrails.
