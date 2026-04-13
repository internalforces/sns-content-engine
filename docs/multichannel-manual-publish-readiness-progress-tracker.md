# Multichannel Manual Publish Readiness Progress Tracker

## Usage
This file is the live implementation tracker for the Multichannel Manual Publish Readiness roadmap.

When an autonomous agent works from `docs/multichannel-manual-publish-readiness-execution-guide.md`, it should update this file:
- before starting a task
- during meaningful implementation progress
- after running tests
- when a blocker or stop reason appears
- when the task is complete

## Current Status
- Current milestone: `M1_stability_baseline`
- Current task: `01_restore_healthcheck_and_smoke_baseline`
- Active status: `done`
- Last updated: `2026-04-13 18:20 KST`
- Base branch: `master`
- Active branch: `codex/task-01-healthcheck-baseline`
- Latest task commit: `not_created`
- Resume decision: `pick_next_task`
- Stop reason: `task_complete`

## Scope For Current Task
- Goal: `Restore a clean readiness baseline so the next multichannel publishing work starts from a green repository state`
- In scope: `Healthcheck regression cleanup, sample-config expectation alignment, and focused readiness verification`
- Out of scope: `New publish workflow behavior, non-X handoff features, and broad documentation rewrites`
- Verification commands:
  - `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest tests/test_cli.py -k healthcheck -q`

## Environment Notes
- Required services status: `running (none required beyond local SQLite fixtures)`
- Env or fixture status: `ready (.venv, temp-db fixtures, and test configs are already present)`
- Existing unrelated failures: `none confirmed on this branch after targeted and full-suite verification`

## Roadmap Status
| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Restore healthcheck and smoke baseline | done | 2026-04-13 18:20 KST | Restored smoke healthcheck expectation, stabilized workflow package exports, and confirmed full `pytest` passes |
| M1 | 02 | Refresh stale roadmap and TODO docs | pending | 2026-04-13 18:00 KST | Several older TODO docs still describe already-completed work as active next steps |
| M2 | 03 | Define non-X manual publish handoff model | pending | 2026-04-13 18:00 KST | Approved LinkedIn and Threads drafts still stop at manual guidance only |
| M2 | 04 | Add manual publish outcome workflow and persistence | pending | 2026-04-13 18:00 KST | No operator-safe mutation path exists for non-X manual publish success or failure |
| M3 | 05 | Expose manual handoff controls through API and console | pending | 2026-04-13 18:00 KST | Existing review and publish pages show context but not a full non-X handoff lifecycle |
| M3 | 06 | Document multichannel handoff flow and expand regressions | pending | 2026-04-13 18:00 KST | Operator docs and linked regressions need to reflect the shipped non-X handoff behavior |

## Changed Files For Active Task
- `app/workflows/__init__.py`
- `tests/test_scripts.py`
- `docs/multichannel-manual-publish-readiness-vibe-coding-prompt.md`
- `docs/multichannel-manual-publish-readiness-roadmap.md`
- `docs/multichannel-manual-publish-readiness-execution-guide.md`
- `docs/multichannel-manual-publish-readiness-progress-tracker.md`

## Progress Log
- `2026-04-13 18:00 KST` Created the Multichannel Manual Publish Readiness initiative after the previous readiness, control-plane, all-domain, and console initiatives were all found complete but the repository still lacked a clean baseline and a real non-X publish lifecycle.
- `2026-04-13 18:00 KST` Chose a next-stage scope centered on baseline cleanup first, then explicit manual publish handoff support for LinkedIn and Threads, because multichannel drafts already exist while only X has a supported live publish path.
- `2026-04-13 18:13 KST` Created the missing initiative documents on the task branch because they were present on the prior branch context but absent from `master`.
- `2026-04-13 18:13 KST` Reproduced the two baseline failures. `tests/test_operations.py` still expects bundled sample config to mention placeholder URLs even though `config/examples/all_domain_news` now uses live URLs, and `tests/test_scripts.py` still writes a placeholder RSS URL into the smoke config so CLI healthcheck fails by design.
- `2026-04-13 18:16 KST` Corrected the Task `01` diagnosis after switching to `master`. The bundled sample config still intentionally uses placeholder URLs, so no readiness assertion change was needed there; the real stale smoke issue was the placeholder RSS URL and old healthcheck check-count expectation in `tests/test_scripts.py`.
- `2026-04-13 18:18 KST` Broader `pytest` revealed a separate pre-existing full-suite blocker: `app.workflows` could expose `discover_sources` and `enrich_articles` as module objects instead of callables when same-named submodules were imported earlier in the test process.
- `2026-04-13 18:19 KST` Replaced the lazy workflow package export shim with explicit re-exports in `app/workflows/__init__.py`, which restored stable callable imports across the full test suite.

## Test Log
- `2026-04-13 18:00 KST` `./.venv/bin/pytest -q` -> `pre_existing_failure` `2 failed, 463 passed; current failures are test_run_healthcheck_flags_bundled_sample_config_directory and test_operations_smoke_cli_flow`
- `2026-04-13 18:13 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q` -> `failed` `2 failed, 4 passed; confirmed stale bundled-sample assertion and placeholder-URL smoke fixture`
- `2026-04-13 18:16 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q` -> `passed` `6 passed`
- `2026-04-13 18:16 KST` `./.venv/bin/pytest tests/test_cli.py -k healthcheck -q` -> `passed` `5 passed, 31 deselected`
- `2026-04-13 18:18 KST` `./.venv/bin/pytest -q` -> `failed` `10 failed, 427 passed; discovered package export shadowing in app.workflows`
- `2026-04-13 18:19 KST` `./.venv/bin/pytest tests/test_discover_workflow.py tests/test_enrich_articles_workflow.py -q` -> `passed` `10 passed`
- `2026-04-13 18:19 KST` `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py tests/test_cli.py -k healthcheck -q` -> `passed` `7 passed, 35 deselected`
- `2026-04-13 18:20 KST` `./.venv/bin/pytest -q` -> `passed` `437 passed`

## Open Questions
- `Should non-X manual handoff creation happen at explicit operator action time after approval, or should approval itself create the first tracked handoff record?`

## Blockers
- `None currently`

## Follow-up
- `If the manual handoff model proves too limiting later, a separate initiative can add direct LinkedIn or Threads platform adapters without reopening this baseline roadmap`

## Completion Summary
- `Task 01 is complete. The smoke CLI fixture now uses a non-placeholder source URL, the healthcheck expectation reflects the current three-check output, and workflow package exports are stable across the full test suite.`
- `No local commit was created in this turn; the branch contains a clean task-ready diff for review or a follow-up commit if desired.`
