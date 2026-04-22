# First Live Rollout Readiness Autonomous Execution Guide

## Purpose
This document is written for an autonomous coding agent, not just for a human operator.

Use it when you want the agent to read the roadmap in `docs/first-live-rollout-readiness-roadmap.md`, inspect the repository, choose the smallest clean implementation shape for each gap, make code changes, run targeted tests, and report completion with minimal back-and-forth.

The prompts below are intentionally opinionated:
- they build from the current implementation instead of inventing a new product from scratch
- they constrain work so the existing safety model stays intact
- they require reusing current workflows and docs before adding new abstractions
- they preserve the manual-review gate and dry-run-first publish defaults unless a task explicitly expands a surface

Progress for live implementation should be tracked in:
- `docs/first-live-rollout-readiness-progress-tracker.md`

## Generated document naming
When instantiating this template, use filenames that make each document's identity obvious at a glance.

- Roadmap file: `docs/first-live-rollout-readiness-roadmap.md`
- Execution guide file: `docs/first-live-rollout-readiness-execution-guide.md`
- Progress tracker file: `docs/first-live-rollout-readiness-progress-tracker.md`
- Vibe coding prompt file: `docs/first-live-rollout-readiness-vibe-coding-prompt.md`
- Avoid ambiguous names like `todo.md`, `prompt.md`, `guide.md`, or `progress.md` when multiple initiatives may coexist.

## Repository Context
The repository already has:
- a working FastAPI application with `/health` and server-rendered `/console/...` routes
- CLI workflows for `healthcheck`, `scheduler run`, `publish-due`, review actions, and DB bootstrap or upgrade
- environment-based secret handling, provider routing, and checked-in deployment assets for one-server operation
- a completed `single-server-deployment-readiness` doc set that should be reused rather than replaced

Important current files and patterns:
- Core entrypoints: `app/cli.py`, `app/api/app.py`
- Core workflows and services: `app/workflows/generate_drafts.py`, `app/workflows/run_local_pipeline.py`
- Storage and schema logic: `app/storage/database.py`, `app/storage/bootstrap.py`
- Provider routing and env handling: `app/connectors/routing/registry.py`, `app/connectors/llm/resolver.py`, `app/connectors/llm/_env_helpers.py`
- Current rollout gaps: `tests/test_config.py`, `.github/workflows/secret-scan.yml`, `config/providers.yaml`, `.env.production.example`
- Existing operator or deployment docs: `README.md`, `docs/single-server-deployment-guide.md`, `docs/operator-console-guide.md`
- Existing roadmap: `docs/first-live-rollout-readiness-roadmap.md`

High-signal tests already exist and should be reused instead of inventing a new test structure:
- `tests/test_config.py`
- `tests/test_phase6_config_routing.py`
- `tests/test_deploy_assets.py`
- `tests/test_cli.py`
- `tests/test_env.py`
- `tests/test_scheduler.py`
- `tests/test_scripts.py`

## Execution Environment
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli version`
- Narrow verification commands by area:
  - `./.venv/bin/pytest tests/test_config.py -q`
  - `./.venv/bin/pytest tests/test_phase6_config_routing.py tests/test_env.py -q`
  - `./.venv/bin/pytest tests/test_deploy_assets.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest -q`
- Required services:
  - `none for docs, config, and the default test slices`
  - `real provider credentials only if a task explicitly verifies a live provider path`
- Required env files, secrets, or fixtures:
  - `.env` when local overrides are needed
  - `.env.production.example` as the checked-in production template
  - provider or publisher credentials only for explicit live-verification tasks
- Package install policy: `ask_first`
- Push and PR policy: `do_not_push_without_explicit_request`

## Global Execution Rules
The agent should follow these rules for every task in this document.

### Working style
- Inspect the current code path before editing.
- Read `docs/first-live-rollout-readiness-progress-tracker.md` before choosing the next task.
- Prefer reusing current config, docs, provider-routing, and workflow logic over duplicating it in new helpers.
- Keep each task self-contained and merge-friendly.
- Choose additive changes over broad redesigns.
- Preserve current behavior unless a task explicitly updates a shared abstraction.

### Resume rules
- If `docs/first-live-rollout-readiness-progress-tracker.md` shows a current task with status `in_progress` or `blocked`, resume or resolve that task before selecting a new one unless the roadmap was intentionally reprioritized.
- Only choose the next unfinished task when there is no active task that still owns the current branch or implementation state.
- If the active task was blocked by a fixable local issue and the scope is still the same, keep the same task ID and continue instead of creating a new task.

### Roadmap shaping rules
- The number of phases, tasks, and milestones is intentionally not fixed.
- When creating or refining the roadmap, choose only as many milestones and tasks as are needed to make forward progress safely.
- Split work so it can be completed without breaking the current structure, safety model, workflow semantics, or operator experience.
- Prefer the smallest additive slices that fit the existing architecture.
- Split a task or milestone when it would otherwise require a broad redesign, mix unrelated surfaces, or make verification unclear.
- Merge adjacent tiny items when they share the same code path, tests, and commit scope.
- If the roadmap shape changes during implementation, update `docs/first-live-rollout-readiness-roadmap.md` and `docs/first-live-rollout-readiness-progress-tracker.md` before continuing.

### Scope control
- Do not expand work into authentication, multi-user permissions, or a full frontend.
- Do not redesign the publish workflow, scheduler runtime, or database model unless a task explicitly requires it.
- Do not add Docker, Kubernetes, or distributed deployment abstractions for this initiative.
- Keep the first live rollout scope centered on `X` live publishing plus existing review-first behavior for other channels.

### Dirty worktree rules
- Inspect the current branch and working tree before making substantive edits when repository tooling is available.
- Never overwrite, revert, or stage unrelated changes.
- If user or pre-existing changes conflict directly with the active task in the same files, stop, record the conflict in `docs/first-live-rollout-readiness-progress-tracker.md`, and treat the task as blocked until the conflict is resolved.
- Keep branch, staging, and commit scope limited to the active task.

### Safety constraints
- Preserve the current manual-review gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Keep validation and policy blockers intact.
- Keep credentials in env only.
- Keep `publish-due` dry-run as the default path unless a task explicitly works on documentation for live opt-in.

### Blocked-task rules
- Try the smallest reasonable local investigation first when a blocker appears.
- If progress is blocked by missing configuration, unavailable services, missing credentials, conflicting local edits, or unrelated failing tests, record the exact blocker and stop reason in `docs/first-live-rollout-readiness-progress-tracker.md`.
- Mark the task `blocked` when work cannot continue safely inside the intended scope.
- Do not mark blocked work as `done`.
- Do not create a normal task-completion commit for blocked work; only create a checkpoint commit if the partial state is independently safe, intentionally scoped, and clearly documented.

### Testing rules
- Add or update targeted tests for every behavior change.
- Use task-specific verification commands from `docs/first-live-rollout-readiness-roadmap.md` when they are provided.
- Run the narrowest relevant test set first.
- If a shared config, routing, or deployment-doc surface changes, run one broader regression slice too.
- If no explicit test command exists, infer the narrowest relevant command from the repository and record that reasoning in `docs/first-live-rollout-readiness-progress-tracker.md`.
- Distinguish newly introduced failures from pre-existing failures or environment failures.
- If testing cannot run, record the exact command and reason as `not_run` or `pre_existing_failure`.
- If a task is docs-only, say so explicitly and note whether no runtime tests were needed.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Use one task-focused branch at a time.
- Preferred branch format:
  - `codex/task-01-default-config-contract`
  - `codex/task-04-blank-provider-env-safety`
- If continuing an already-started task branch, reuse it instead of creating another branch.
- Do not commit unrelated workspace changes.
- Stage only files relevant to the active task.
- Create a commit after the relevant tests pass, or explicitly record why tests could not run.
- Do not push branches or open pull requests unless explicitly requested.
- Use a clear commit message tied to the task outcome, for example:
  - `Align default config contract with tests`
  - `Add pytest workflow baseline`
  - `Harden blank provider env handling`

### Completion rules
- Only finish after code changes, verification, and progress updates are done.
- Do not mark a task complete until `docs/first-live-rollout-readiness-progress-tracker.md` includes the final status, changed files, test log, and commit details or the reason a commit was not created.
- If the work cannot be finished safely, leave the task as `blocked` with a clear next step instead of forcing completion.
- Report:
  - what changed
  - why that shape was chosen
  - tests run
  - branch and commit details
  - any remaining follow-up intentionally deferred

## Progress Tracking Rules
The agent must keep `docs/first-live-rollout-readiness-progress-tracker.md` updated while implementing this roadmap.

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
  - record test commands and pass or fail status
- At task completion:
  - mark the task `done`
  - summarize the final changed files
  - record the commit SHA and commit message if a commit was created
  - record follow-up items if any remain

### What to track
- current active task
- current active milestone
- base branch
- active branch
- latest commit for the task when available
- resume decision
- overall task status table
- files changed for the active task
- implementation notes
- test execution log
- stop reason or blockers
- open questions
- pre-existing failures or environment constraints
- blockers or follow-up items

### Tracking constraints
- Keep entries short and factual.
- Update the existing progress file instead of creating a new ad hoc log.
- Avoid duplicate log entries when rerunning the same step; update the existing note if it still describes the current state.
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

Branch and commit
- ...

Follow-up
- ...
```

## Recommended Task Order
List the actual tasks defined in `docs/first-live-rollout-readiness-roadmap.md` in dependency order.

1. Task `01`: Align Default Config And Test Expectations
2. Task `02`: Add Pytest CI Baseline
3. Task `03`: Align Production Provider Strategy
4. Task `04`: Harden Blank Provider Env Handling
5. Task `05`: Document X-Only Live Rollout Scope
6. Task `06`: Add First Rollout Preflight Checklist

## Master Prompt
Use this when you want the agent to autonomously pick the next unfinished unit and implement it.

```text
You are implementing the First Live Rollout Readiness roadmap in this repository.

Start by reading:
- docs/first-live-rollout-readiness-roadmap.md
- docs/first-live-rollout-readiness-execution-guide.md
- docs/first-live-rollout-readiness-progress-tracker.md

Then inspect the current code before editing. Use the task boundaries and rules in docs/first-live-rollout-readiness-execution-guide.md.

Your job:
1. Determine whether docs/first-live-rollout-readiness-progress-tracker.md already shows an active task. If it is `in_progress` or `blocked`, resume or resolve that task unless the roadmap was intentionally reprioritized.
2. If there is no active task, determine the next unfinished task in the recommended order.
3. If the roadmap shape is incomplete, too large, or unsafe to execute cleanly, refine the task or milestone boundaries using the smallest additive slices that preserve the current structure, then update docs/first-live-rollout-readiness-roadmap.md and docs/first-live-rollout-readiness-progress-tracker.md before coding.
4. Create or switch to a dedicated task branch using the git workflow rules in docs/first-live-rollout-readiness-execution-guide.md.
5. Update docs/first-live-rollout-readiness-progress-tracker.md to mark that task in progress and note the intended scope, branch, and verification plan.
6. Implement only that task cleanly and completely.
7. Keep docs/first-live-rollout-readiness-progress-tracker.md updated during the work with changed files, progress notes, blockers, or stop reasons.
8. Add or update targeted tests.
9. Run the task verification commands from docs/first-live-rollout-readiness-roadmap.md, plus one broader regression slice if shared surfaces changed, and record the results in docs/first-live-rollout-readiness-progress-tracker.md.
10. Stage only the task-relevant files and create a focused commit after tests pass, or explicitly record why a commit was not created.
11. Mark the task complete in docs/first-live-rollout-readiness-progress-tracker.md when verified, including branch and commit details, or leave it `blocked` with a clear next step if it cannot be finished safely.
12. Summarize changes, tests, branch, commit, and follow-up.

Critical constraints:
- preserve the manual-review gate
- keep dry-run-first publish as the default gate
- avoid broad architecture rewrites
- keep `X` as the only first-rollout live-publish scope unless a task explicitly expands it
- do not push or open a PR unless explicitly requested

If the next task is ambiguous, choose the smallest sensible interpretation that best restores a green baseline, reduces operator ambiguity, or advances the stated milestone without changing workflow semantics.
```
