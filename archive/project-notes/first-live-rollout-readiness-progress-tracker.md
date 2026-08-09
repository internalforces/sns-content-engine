# First Live Rollout Readiness Progress Tracker

## Usage
This file is the live implementation tracker for the First Live Rollout Readiness roadmap.

When an autonomous agent works from `docs/first-live-rollout-readiness-execution-guide.md`, it should update this file:
- before starting a task
- during meaningful implementation progress
- after running tests
- when a blocker or stop reason appears
- when the task is complete

Keep updates short, factual, and current.

## Generated document naming
When instantiating this template, keep the filename explicit so this file is easy to distinguish from planning or prompt documents.

- Recommended filename: `docs/first-live-rollout-readiness-progress-tracker.md`
- Related files:
  - `docs/first-live-rollout-readiness-vibe-coding-prompt.md`
  - `docs/first-live-rollout-readiness-roadmap.md`
  - `docs/first-live-rollout-readiness-execution-guide.md`

If `Current task` is already marked `in_progress` or `blocked`, resume or resolve that task before picking a new one unless the roadmap was intentionally reprioritized.

## Current Status
- Current milestone: `M3_first_rollout_guardrails`
- Current task: `06_add_first_rollout_preflight_checklist`
- Active status: `done`
- Last updated: `2026-04-23 17:36 KST`
- Base branch: `master`
- Active branch: `codex/task-01-default-config-contract`
- Latest task commit: `branch_head_contains_completed_readiness_slice`
- Resume decision: `all_current_roadmap_tasks_completed_in_worktree`
- Stop reason: `none`

## Scope For Current Task
- Goal: `Add one short preflight sequence aligned with the checked-in rollout assets and close the remaining first-rollout guardrail gaps.`
- In scope: `README and deployment-facing X-only guardrails, production env template alignment, and one explicit preflight checklist`
- Out of scope: `Threads live enablement, auth redesign, and broader infrastructure changes`
- Dependencies: `completed green baseline work, provider hardening, and checked-in deploy assets`
- Verification commands:
  - `./.venv/bin/pytest -q`
  - `./.venv/bin/pytest tests/test_phase6_config_routing.py tests/test_env.py tests/test_metadata_generator.py -q`
  - `./.venv/bin/pytest tests/test_cli.py -q`

## Environment Notes
- Required services status: `not_running`
- Env or fixture status: `ready for docs and local test work; live provider credentials were not required for any completed task`
- Existing unrelated failures: `none currently recorded after Task 01 verification`

## Roadmap Status

| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Align Default Config And Test Expectations | done | 2026-04-23 17:15 KST | Updated the stale default source-set assertions to match the manual-only checked-in config, clarified the README default-config contract, and reran the focused verification slice successfully |
| M1 | 02 | Add Pytest CI Baseline | done | 2026-04-23 17:16 KST | Added `.github/workflows/pytest.yml` as the minimal repo-backed CI gate and revalidated the full suite plus deploy-asset slice locally |
| M2 | 03 | Align Production Provider Strategy | done | 2026-04-23 17:18 KST | Switched the checked-in `config/providers.yaml` default to OpenAI-first, aligned `.env.production.example`, README, and the deployment guide with that production story, and updated the sample-config assertion |
| M2 | 04 | Harden Blank Provider Env Handling | done | 2026-04-23 17:19 KST | Added shared non-blank env checks so blank provider vars are ignored safely during route selection and metadata resolver fallback, then updated targeted regression coverage |
| M3 | 05 | Document X-Only Live Rollout Scope | done | 2026-04-23 17:21 KST | Clarified in README, the operator console guide, and the production env template that the first protected live rollout keeps `x` as the only live-publish channel while Threads stays deferred |
| M3 | 06 | Add First Rollout Preflight Checklist | done | 2026-04-23 17:22 KST | Added one explicit first-rollout preflight sequence in the single-server deployment guide aligned with `pytest`, `healthcheck`, `scan_secrets.sh`, and `scripts/single_server_smoke_check.sh` |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files For Active Task
- `.env.production.example`
- `.github/workflows/pytest.yml`
- `README.md`
- `app/connectors/_env_helpers.py`
- `app/connectors/llm/text_generation.py`
- `app/connectors/routing/registry.py`
- `config/providers.yaml`
- `docs/first-live-rollout-readiness-progress-tracker.md`
- `docs/operator-console-guide.md`
- `docs/single-server-deployment-guide.md`
- `tests/test_config.py`
- `tests/test_metadata_generator.py`
- `tests/test_openai_llm_provider.py`
- `tests/test_phase6_config_routing.py`

## Progress Log
- `2026-04-22 22:49 KST` Created the `first-live-rollout-readiness` initiative doc set to capture the remaining work between the completed single-server deployment baseline and the first safe live rollout.
- `2026-04-22 22:49 KST` Recorded the current highest-signal blockers: one stale config test failure, missing pytest CI, provider strategy ambiguity, blank env handling risk, and missing X-only rollout wording.
- `2026-04-22 22:49 KST` Chose Task `01` as the next recommended slice because it restores the local green baseline before provider and rollout hardening.
- `2026-04-23 17:13 KST` Switched from the stale `codex/task-05-rollout-runbook` branch back to `master`, created `codex/task-01-default-config-contract`, and confirmed the default `config/sources.yaml` source sets are manual-only.
- `2026-04-23 17:13 KST` Re-ran `tests/test_config.py` and confirmed the only failure is the stale `ai_tools_primary` / `seo_tools_primary` expectation in `test_registry_loads_sample_config_directory`.
- `2026-04-23 17:15 KST` Completed Task `01` by aligning the default source-set assertions in `tests/test_config.py` and clarifying in `README.md` that the checked-in default config stays manual CSV-only for the first rollout baseline.
- `2026-04-23 17:16 KST` Completed Task `02` by adding `.github/workflows/pytest.yml` with the same Python and install shape as `secret-scan.yml`, keeping the CI gate intentionally minimal.
- `2026-04-23 17:18 KST` Completed Task `03` by making the checked-in provider sample OpenAI-first for `draft_generate` and `metadata_generate`, then aligning README, `.env.production.example`, and the single-server deployment guide with that production story.
- `2026-04-23 17:19 KST` Completed Task `04` by adding a connector-level non-blank env helper, using it in route selection plus metadata resolver fallback, and updating focused tests so blank provider vars now degrade safely instead of surfacing late provider-construction errors.
- `2026-04-23 17:21 KST` Completed Task `05` by removing first-rollout ambiguity from README, the operator console guide, and `.env.production.example`; the docs now keep `x` as the only intended first-rollout live channel and defer Threads live enablement.
- `2026-04-23 17:22 KST` Completed Task `06` by adding a short first-rollout preflight section to the single-server deployment guide with the exact `pytest`, `healthcheck`, `scheduler publish-due`, `scan_secrets.sh`, and smoke-check commands to run before the first live `x` publish.
- `2026-04-23 17:22 KST` Re-ran the full suite after the provider and rollout-doc changes, fixed one stale OpenAI resolver expectation to match the new blank-env contract, and confirmed the repository is green again.
- `2026-04-23 17:36 KST` Received an explicit commit request, rechecked the branch diff, and staged the completed readiness slice to be recorded as the current branch head.

## Test Log
- `2026-04-22 22:49 KST` `./.venv/bin/pytest tests/test_config.py -q` -> `pre_existing_failure` `1 failed, 26 passed; stale RSS expectations in tests/test_config.py do not match the current manual-only default config`
- `2026-04-22 22:49 KST` `./.venv/bin/python -m app.cli version` -> `passed` `environment and local CLI entrypoint available`
- `2026-04-23 17:13 KST` `./.venv/bin/pytest tests/test_config.py -q` -> `pre_existing_failure` `1 failed, 26 passed; only the default source-set assertion still expects ai_tools_rss and seo_tools_rss`
- `2026-04-23 17:15 KST` `./.venv/bin/pytest tests/test_config.py -q` -> `passed` `27 passed`
- `2026-04-23 17:15 KST` `./.venv/bin/pytest tests/test_cli.py -k healthcheck -q` -> `passed` `5 passed, 33 deselected`
- `2026-04-23 17:16 KST` `./.venv/bin/pytest tests/test_deploy_assets.py -q` -> `passed` `6 passed`
- `2026-04-23 17:16 KST` `./.venv/bin/pytest -q` -> `passed` `525 passed`
- `2026-04-23 17:19 KST` `./.venv/bin/pytest tests/test_phase6_config_routing.py tests/test_env.py tests/test_metadata_generator.py -q` -> `passed` `94 passed`
- `2026-04-23 17:19 KST` `./.venv/bin/pytest tests/test_cli.py -q` -> `passed` `38 passed`
- `2026-04-23 17:21 KST` `./.venv/bin/pytest -q` -> `pre_existing_failure_during_iteration` `1 failed, 529 passed; stale expectation in tests/test_openai_llm_provider.py still expected blank OPENAI_API_KEY to raise instead of falling back safely`
- `2026-04-23 17:22 KST` `./.venv/bin/pytest -q` -> `passed` `530 passed`

## Open Questions
- `None; the active roadmap tasks for the first protected live rollout slice are complete in the current worktree.`

## Blockers
- `None.`

## Follow-up
- `Optional later work only: a separate Threads live-rollout initiative can reuse the documented deferred setup path after the X-only first rollout is complete.`

## Completion Summary
- `Tasks 01 through 06 are complete in the current worktree. The repository is green at 530 passing tests, the checked-in provider path is OpenAI-first, blank provider env vars are ignored safely, the first protected live rollout is documented as X-only, and the single-server deployment guide now includes one explicit preflight sequence. The completed slice is ready to live at branch head on codex/task-01-default-config-contract.`
