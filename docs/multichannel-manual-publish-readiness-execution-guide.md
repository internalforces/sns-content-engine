# Multichannel Manual Publish Readiness Autonomous Execution Guide

## Purpose
Use this guide to implement the roadmap in `docs/multichannel-manual-publish-readiness-roadmap.md` with the smallest safe slice possible.

Progress for live implementation should be tracked in:
- `docs/multichannel-manual-publish-readiness-progress-tracker.md`

## Repository Context
The repository already has:
- config-driven draft generation for X, LinkedIn, and Threads
- review queue, publish job, and publish log persistence
- FastAPI control-plane routes plus a server-rendered operator console
- a live X publisher plus browser guidance for manual non-X uploads

High-signal tests to reuse:
- `tests/test_operations.py`
- `tests/test_scripts.py`
- `tests/test_review_queue_workflow.py`
- `tests/test_api.py`
- `tests/test_console.py`
- `tests/test_scheduler.py`

## Execution Environment
- Base branch: `master`
- Project bootstrap commands:
  - `python -m pip install -e ".[dev]"`
  - `./.venv/bin/python -m app.cli healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db`
- Narrow verification commands:
  - `./.venv/bin/pytest tests/test_operations.py tests/test_scripts.py -q`
  - `./.venv/bin/pytest tests/test_api.py tests/test_console.py -q`
- Broader regression commands:
  - `./.venv/bin/pytest tests/test_review_queue_workflow.py tests/test_scheduler.py tests/test_api.py tests/test_console.py -q`
  - `./.venv/bin/pytest -q`

## Global Execution Rules

### Working style
- Inspect the current code path before editing.
- Read `docs/multichannel-manual-publish-readiness-progress-tracker.md` before choosing the next task.
- Prefer reusing workflow and repository logic over duplicating it in new handlers or adapters.
- Keep each task self-contained and merge-friendly.
- Choose additive changes over broad redesigns.

### Resume rules
- If the progress tracker shows a task as `in_progress` or `blocked`, resume or resolve that task before selecting a new one unless the roadmap was intentionally reprioritized.

### Scope control
- Do not expand work into authentication, multi-user permissions, or a full frontend unless the task explicitly requires it.
- Keep migration or schema work modest and practical.

### Safety constraints
- Preserve the current review or approval gate.
- Do not introduce auto-approve, auto-publish, or other safety bypasses.
- Preserve X dry-run-by-default scheduler behavior unless a task explicitly says otherwise.

### Testing rules
- Add or update targeted tests for every behavior change.
- Run the narrowest relevant test set first.
- If a shared surface changes, run one broader regression slice too.

### Git workflow rules
- Create a dedicated branch before making substantive changes for a task.
- Stage only task-relevant files.
- Create a focused commit after tests pass, or record why no commit was created.
- Do not push or open a PR unless explicitly requested.

### Completion rules
- Only finish after code changes, verification, and progress updates are done.
- Report:
  - what changed
  - why that shape was chosen
  - tests run
  - branch and commit details
  - any intentionally deferred follow-up
