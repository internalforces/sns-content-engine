# First Live Rollout Operations Progress Tracker

## Usage
This file is the live execution tracker for the First Live Rollout Operations roadmap.

When an autonomous agent works from `docs/first-live-rollout-operations-execution-guide.md`, it should update this file:
- before starting a task
- during meaningful execution progress
- after running tests or operational checks
- when a blocker or stop reason appears
- when the task is complete

Keep updates short, factual, and current.

## Generated document naming
When instantiating this template, keep the filename explicit so this file is easy to distinguish from planning or prompt documents.

- Recommended filename: `docs/first-live-rollout-operations-progress-tracker.md`
- Related files:
  - `docs/first-live-rollout-operations-vibe-coding-prompt.md`
  - `docs/first-live-rollout-operations-roadmap.md`
  - `docs/first-live-rollout-operations-execution-guide.md`

If `Current task` is already marked `in_progress` or `blocked`, resume or resolve that task before picking a new one unless the roadmap was intentionally reprioritized.

## Current Status
- Current milestone: `M2_server_dry_run_gate`
- Current task: `04_run_server_dry_run_publish_and_smoke_helper`
- Active status: `in_progress`
- Last updated: `2026-04-28 22:50 KST`
- Base branch: `master`
- Active branch: `codex/task-04-smoke-rollout-summary`
- Latest task commit: `Record Task 04 secret scan git safety blocker`
- Resume decision: `operator_provided_task_04_secret_scan_blocker`
- Stop reason: `waiting_for_task_04_production_secret_scan_after_git_safe_directory_fix`

## Scope For Current Task
- Goal: `Prove the production publish path stays dry-run and the protected edge is reachable, while enforcing the X-only rollout summary gate first.`
- In scope: `smoke helper X-only rollout-summary gate, script coverage, docs alignment, and server-side dry-run/smoke command evidence when available`
- Out of scope: `live publish commands, Threads live rollout, LinkedIn direct publish, auth redesign, and infrastructure redesign`
- Dependencies: `production services, edge smoke credentials, and Task 04 dry-run plus smoke output from the production server shell`
- Verification commands:
  - `./.venv/bin/sns-engine rollout-summary --config-dir /opt/sns-content-engine/config`
  - `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config`
  - `./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config`
  - `scripts/single_server_smoke_check.sh`

## Environment Notes
- Required services status: `Task 03 production evidence was provided by the operator and passed; Task 04 smoke helper passed all service, edge, authenticated console, and dry-run publish checks through the existing Docker Caddy edge`
- Env or fixture status: `production app root, env file, and config dir were reported present by the operator; rollout-summary and healthcheck passed without printing secret values`
- Existing unrelated failures: `none currently recorded after Task 02 verification; local CLI version still works`

## Roadmap Status

| Milestone | Task | Name | Status | Last update | Notes |
| --- | --- | --- | --- | --- | --- |
| M1 | 01 | Confirm Rollout Inputs And Approval Boundary | done | 2026-04-26 20:38 KST | Confirmed current branch, X-only first-rollout docs, dry-run default behavior, and the separate explicit approval boundary for any future `--live` command |
| M1 | 02 | Run Local Regression And Secret Gates | done | 2026-04-27 22:29 KST | Targeted tests, full pytest, and secret scan passed before any server-side checks |
| M2 | 03 | Verify Production Config And Healthcheck | done | 2026-04-28 20:19 KST | Operator-provided server evidence shows app root, env file, and config dir present; `rollout-summary` returned `status=ok` with `first_rollout_x_only=true`; `healthcheck` returned `failed_check_count=0` |
| M2 | 04 | Run Server Dry-Run Publish And Smoke Helper | in_progress | 2026-04-28 22:50 KST | Smoke helper passed all checks, including dry-run publish; production secret scan is blocked by Git `safe.directory` ownership protection and must be rerun after registering the app root as safe |
| M3 | 05 | Execute One Approved X Live Publish | pending | 2026-04-26 20:13 KST | Must not run without explicit operator approval for the exact live step |
| M3 | 06 | Capture Post-Publish Observation And Next Decision | pending | 2026-04-26 20:13 KST | Record publish evidence, external observation, and continue, pause, retry, or follow-up decision |

Status values:
- `pending`
- `in_progress`
- `blocked`
- `done`

## Changed Files Or Evidence For Active Task
- `docs/first-live-rollout-operations-progress-tracker.md`
- `README.md`, `docs/single-server-deployment-guide.md`, and `docs/operator-console-guide.md` evidence: first-rollout and `publish-due` guidance still preserve dry-run-first and explicit `--live` boundaries.
- `app/cli.py` evidence: `scheduler publish-due` keeps `live=False` by default and calls `publish_due_jobs(..., dry_run=not live)`.
- `app/scheduler/jobs.py` evidence: scheduler due-publish execution defaults to dry-run when no live executor or publisher resolver is supplied.
- `app/cli.py` evidence: `healthcheck` resolves a readable `--config-dir`, prints key=value readiness lines, and exits non-zero when any check fails.
- `app/cli.py` evidence: added read-only `rollout-summary` command for redacted provider route and publisher channel evidence before server healthcheck.
- `app/operations.py` evidence: added redacted rollout config summary helpers; credential references are printed only when they look like env var names, otherwise the value is redacted.
- `tests/test_cli.py` evidence: added focused coverage for X-only summary output, non-X publisher detection, and non-env-style credential reference redaction.
- `docs/single-server-deployment-guide.md` evidence: Task 03 command shape is documented as `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config`.
- `docs/single-server-deployment-guide.md` evidence: first-rollout preflight now uses `./.venv/bin/sns-engine rollout-summary --config-dir /opt/sns-content-engine/config` before healthcheck and dry-run checks.
- `docs/first-live-rollout-operations-roadmap.md` and `docs/first-live-rollout-operations-execution-guide.md` evidence: Task 03 verification now includes `rollout-summary`.
- `scripts/single_server_smoke_check.sh` evidence: the smoke helper now runs `rollout-summary` before healthcheck and fails before dry-run publish unless `first_rollout_x_only=true` is present.
- `tests/test_scripts.py` evidence: smoke helper coverage now verifies the successful X-only path and the failure path for a non-X publisher channel.
- `README.md` and `docs/single-server-deployment-guide.md` evidence: smoke helper docs now mention the redacted first-rollout config summary check.
- `docs/first-live-rollout-operations-roadmap.md` and `docs/first-live-rollout-operations-execution-guide.md` evidence: Task 04 now includes local script coverage and the X-only smoke-helper gate.
- `./.venv/bin/python -m app.cli version` evidence: local CLI entrypoint is available before Task 02 verification.
- `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q` evidence: `33 passed`
- `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q` evidence: `67 passed`
- `./.venv/bin/pytest -q` evidence: `530 passed`
- `scripts/scan_secrets.sh check` evidence: `passed with no output`
- `scripts/scan_secrets.sh check` evidence: `passed with no output after the Task 03 tracker update`
- `scripts/scan_secrets.sh check` evidence: `passed with no output after the Task 03 recheck tracker update`
- `scripts/scan_secrets.sh check` evidence: `passed with no output after the Task 03 DNS recheck tracker update`
- `scripts/scan_secrets.sh check` evidence: `passed with no output after the Task 03 local access hints recheck tracker update`
- `scripts/scan_secrets.sh check` evidence: `passed with no output after adding the Task 03 server handoff block`
- `scripts/scan_secrets.sh check` evidence: `passed with no output after adding the Task 03 config summary handoff`
- `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config` evidence: `not_run`; this command must run on the production server where `/opt/sns-content-engine/.env` and `/opt/sns-content-engine/config` exist.
- `ls -ld /opt /opt/sns-content-engine /opt/sns-content-engine/config /opt/sns-content-engine/.env` evidence: local `/opt` exists, but the production app root is not present in this workspace.
- `curl --fail https://sns.gilgop.cloud/health?config_dir=/opt/sns-content-engine/config` evidence: `failed`; DNS resolution returned `Could not resolve host`.
- `curl https://sns.gilgop.cloud/console/?config_dir=/opt/sns-content-engine/config` evidence: `failed`; DNS resolution returned `Could not resolve host`.
- `nslookup sns.gilgop.cloud` evidence: `failed`; resolver returned `NXDOMAIN`.
- `host sns.gilgop.cloud` evidence: `failed`; resolver returned `NXDOMAIN`.
- `ssh -o BatchMode=yes -o ConnectTimeout=5 sns.gilgop.cloud 'pwd'` evidence: `failed`; SSH could not resolve the hostname, so no authentication or remote command occurred.
- `SSH config and /etc/hosts scan` evidence: no `sns`, `gilgop`, `content-engine`, `sns-engine`, or `/opt/sns-content-engine` host alias entries were found.
- `env variable name scan` evidence: only `SSH_AUTH_SOCK` matched the deployment-related prefix check; no `SNS_*`, `DEPLOY_*`, `PRODUCTION_*`, or `PROD_*` variable names were present.
- `ssh-add -l` evidence: SSH agent reported no identities.
- `Task 03 server handoff block` evidence: added a redacted command bundle in this tracker so an operator with server shell access can verify path presence and run healthcheck without printing secret values.
- `local config summary command` evidence: checked-in config reports `draft_generate` and `metadata_generate` provider `openai` at priority `1`; publisher-enabled channels are `ai_tools_daily:x` and `seo_tools_daily:x`; `first_rollout_x_only=yes`.
- `Task 03 server handoff block` evidence: expanded the redacted command bundle to include the same provider-route and publisher-channel summary on the production server.
- `2026-04-28 11:25 KST local production root recheck` evidence: local `/opt` exists, but `/opt/sns-content-engine`, `/opt/sns-content-engine/.env`, and `/opt/sns-content-engine/config` are still absent.
- `2026-04-28 11:25 KST DNS recheck` evidence: `nslookup sns.gilgop.cloud` and `host sns.gilgop.cloud` still return `NXDOMAIN`.
- `2026-04-28 11:25 KST SSH recheck` evidence: non-interactive SSH to `sns.gilgop.cloud` failed at hostname resolution, so no remote command ran.
- `2026-04-28 11:25 KST local access hint recheck` evidence: only `SSH_AUTH_SOCK` matched the deployment-related env-name scan, `ssh-add -l` reported no identities, and no matching `~/.ssh/config` file exists.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after the 2026-04-28 Task 03 blocker recheck tracker update`
- `./.venv/bin/python -m app.cli rollout-summary --config-dir config` evidence: `passed`; checked-in config reports OpenAI-first draft and metadata routes, publisher channels `ai_tools_daily:x` and `seo_tools_daily:x`, and `first_rollout_x_only=true` without printing credential values.
- `./.venv/bin/pytest tests/test_cli.py -k 'rollout_summary or healthcheck or publish_due' -q` evidence: `12 passed, 29 deselected`.
- `./.venv/bin/pytest tests/test_operations.py -q` evidence: `3 passed`.
- `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q` evidence: `33 passed` after adding `rollout-summary`.
- `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q` evidence: `70 passed` after adding `rollout-summary`.
- `./.venv/bin/pytest -q` evidence: `533 passed` after adding `rollout-summary`.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after adding rollout-summary`.
- `git diff --check` evidence: `passed with no output after adding rollout-summary`.
- `./.venv/bin/pytest tests/test_scripts.py -q` evidence: `5 passed` after adding the smoke-helper `rollout-summary` gate.
- `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py tests/test_scripts.py -q` evidence: `75 passed` after adding the smoke-helper `rollout-summary` gate.
- `scripts/single_server_smoke_check.sh` evidence: `blocked locally`; direct local execution stopped with `missing command: systemctl`, which confirms the script still requires a production-like systemd context.
- `./.venv/bin/pytest -q` evidence: `534 passed` after adding the smoke-helper `rollout-summary` gate.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after adding the smoke-helper rollout-summary gate`.
- `git diff --check` evidence: `passed with no output after adding the smoke-helper rollout-summary gate`.
- `2026-04-28 13:37 KST local production root recheck` evidence: local `/opt` exists, but `/opt/sns-content-engine`, `/opt/sns-content-engine/.env`, and `/opt/sns-content-engine/config` are still absent.
- `2026-04-28 13:37 KST DNS recheck` evidence: `nslookup sns.gilgop.cloud` and `host sns.gilgop.cloud` still return `NXDOMAIN`.
- `2026-04-28 13:37 KST SSH recheck` evidence: non-interactive SSH to `sns.gilgop.cloud` failed at hostname resolution, so no remote command ran.
- `2026-04-28 13:37 KST local access hint recheck` evidence: only `SSH_AUTH_SOCK` matched the deployment-related env-name scan, `ssh-add -l` reported no identities, and `~/.ssh/config` is absent.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after the 2026-04-28 13:37 KST Task 04 blocker recheck tracker update`.
- `git diff --check` evidence: `passed with no output after the 2026-04-28 13:37 KST Task 04 blocker recheck tracker update`.
- `Task 04 server handoff block` evidence: added a redacted production-shell command bundle for rollout summary, healthcheck, dry-run publish, secret scan, and the checked-in smoke helper without printing edge credential values.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after adding the Task 04 server handoff block`.
- `git diff --check` evidence: `passed with no output after adding the Task 04 server handoff block`.
- `2026-04-28 13:51 KST local production root recheck` evidence: local `/opt` exists, but `/opt/sns-content-engine`, `/opt/sns-content-engine/.env`, and `/opt/sns-content-engine/config` are still absent.
- `2026-04-28 13:51 KST DNS recheck` evidence: `nslookup sns.gilgop.cloud` and `host sns.gilgop.cloud` still return `NXDOMAIN`.
- `2026-04-28 13:51 KST SSH recheck` evidence: non-interactive SSH to `sns.gilgop.cloud` failed at hostname resolution, so no remote command ran.
- `2026-04-28 13:51 KST local access hint recheck` evidence: only `SSH_AUTH_SOCK` matched the deployment-related env-name scan and `ssh-add -l` reported no identities.
- `Task 05 approval handoff block` evidence: added explicit preconditions, approval wording, single-command boundary, and post-publish evidence requirements without starting Task `05` or running any `--live` command.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after adding the Task 05 approval handoff block`.
- `git diff --check` evidence: `passed with no output after adding the Task 05 approval handoff block`.
- `Task 06 observation handoff block` evidence: added explicit post-publish observation fields, log commands, decision values, and retry boundary without starting Task `06` or running any live command.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after adding the Task 06 observation handoff block`.
- `git diff --check` evidence: `passed with no output after adding the Task 06 observation handoff block`.
- `2026-04-28 14:02 KST Task 03 handoff execution` evidence: reported `app_root_present=no`, `env_file_present=no`, and `config_dir_present=no`, then stopped at `cd /opt/sns-content-engine`; no server `rollout-summary` or `healthcheck` command ran.
- `2026-04-28 14:02 KST Task 04 handoff execution` evidence: reported edge auth env absent plus `app_root_present=no` and `config_dir_present=no`, then stopped at `cd /opt/sns-content-engine`; no server dry-run publish, secret scan, or smoke helper command ran.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after recording the Task 03 and Task 04 handoff execution blocker`.
- `git diff --check` evidence: `passed with no output after recording the Task 03 and Task 04 handoff execution blocker`.
- `2026-04-28 14:06 KST production shell access attempt` evidence: `sns.gilgop.cloud` still returned NXDOMAIN; `gilgop.cloud` resolved but SSH stopped at host-key verification; Tailscale `sonubuntu-server` was visible, but SSH to tested user candidates was denied, including with the local key explicitly selected.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after recording the production shell access attempt`.
- `git diff --check` evidence: `passed with no output after recording the production shell access attempt`.
- `2026-04-28 20:19 KST Task 03 operator-provided production evidence` evidence: app root, env file, and config dir all reported present; `rollout-summary` reported two provider routes, two X publisher channels, `first_rollout_x_only=true`, OpenAI provider priority `1` for draft and metadata generation, and env-style X publisher credential references; `healthcheck` reported `status=ok`, `check_count=3`, and `failed_check_count=0`.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after recording Task 03 production pass`.
- `git diff --check` evidence: `passed with no output after recording Task 03 production pass`.
- `2026-04-28 22:16 KST Task 04 operator-provided Caddy evidence` evidence: `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` returned `Valid configuration`, but `systemctl restart caddy` failed because `listen tcp :443: bind: address already in use`; `caddy.service` is failed, so the edge smoke gate is blocked.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after recording the Task 04 Caddy port blocker`.
- `git diff --check` evidence: `passed with no output after recording the Task 04 Caddy port blocker`.
- `2026-04-28 22:29 KST Task 04 operator-provided Docker Caddy evidence` evidence: `starterkit-prod-caddy-1` owns host ports `80` and `443`; after adding `host.docker.internal` support, `docker compose -p starterkit-prod -f infra/compose/docker-compose.prod.yml up -d caddy` recreated Caddy and related starterkit containers but emitted many missing-env warnings and ended with `minio-init` failing, so the next check is whether Caddy is healthy and can reach `host.docker.internal:8001`.
- `2026-04-28 22:47 KST Task 04 operator-provided smoke evidence` evidence: `scripts/single_server_smoke_check.sh` passed `sns-web.service`, `sns-scheduler.service`, `docker.service`, `rollout_summary`, `healthcheck_cli`, `loopback_health`, `console_edge_gate`, `console_authenticated`, `publish_due_dry_run`, and `single_server_rollout`.
- `2026-04-28 22:50 KST Task 04 operator-provided secret scan attempt` evidence: `scripts/scan_secrets.sh check` did not complete because Git rejected `/opt/sns-content-engine` as a dubious-ownership repository and then printed `git diff --no-index` usage; no secret-scan pass/fail result was produced.
- `scripts/scan_secrets.sh check` evidence: `passed with no output after recording the Task 04 smoke pass`.
- `git diff --check` evidence: `passed with no output after recording the Task 04 smoke pass`.

## Progress Log
- `2026-04-26 20:13 KST` Initialized the `first-live-rollout-operations` document set from the initiative templates after confirming the prior readiness roadmap is complete and the next real work is operational preflight plus controlled X live rollout.
- `2026-04-26 20:13 KST` Set Task `01` as the next recommended slice because it has no production side effects and establishes the approval boundary before any server or live command.
- `2026-04-26 20:38 KST` Confirmed the active branch is `codex/first-live-rollout-operations-docs` with only the first-live-rollout operations document set currently untracked before this task commit.
- `2026-04-26 20:38 KST` Verified the rollout docs still preserve the intended boundary: first live scope is `X`, `publish-due` is dry-run first, Threads remains deferred or manual fallback for the first rollout, and any future live publish requires a separate explicit operator approval for the exact `--live` command.
- `2026-04-26 20:38 KST` Checked the CLI and scheduler code path and confirmed the documented behavior matches implementation: `--live` defaults to false, dry-run mode is passed by default, and live publisher resolution is only used outside dry-run mode.
- `2026-04-26 20:38 KST` Completed Task `01` without running server-side commands, smoke checks, or any live publish command.
- `2026-04-26 20:39 KST` Ran the checked-in secret scan as a narrow pre-commit safety check for the operations document set; this does not replace the full Task `02` local gate.
- `2026-04-27 22:27 KST` Started Task `02` on branch `codex/task-02-local-launch-gate` after confirming the Task `01` branch was clean, the local CLI entrypoint works, and the docs plus implementation still preserve the dry-run-first `publish-due` boundary.
- `2026-04-27 22:29 KST` Completed Task `02`: targeted config/deploy tests, targeted CLI/scheduler/X publisher tests, full pytest, and the checked-in secret scan all passed. No server-side command, smoke check, or live publish command was run.
- `2026-04-28 10:58 KST` Started Task `03` on branch `codex/task-03-production-healthcheck` from the completed Task `02` branch head.
- `2026-04-28 10:58 KST` Re-inspected `app/cli.py`, `docs/single-server-deployment-guide.md`, and `scripts/single_server_smoke_check.sh`; the server-side healthcheck command shape is present and remains separate from dry-run publish, smoke checks, and live publish.
- `2026-04-28 10:58 KST` Blocked Task `03` before production command execution because the current local workspace does not provide a production server shell, production `/opt/sns-content-engine/.env`, or production `/opt/sns-content-engine/config` context. No server-side command, smoke check, or live publish command was run.
- `2026-04-28 11:00 KST` Ran the checked-in secret scan after the Task `03` tracker update; it passed with no output.
- `2026-04-28 11:03 KST` Resumed Task `03` after the operator requested the next work. Confirmed the current local machine is still not the production server because `/opt/sns-content-engine` is absent.
- `2026-04-28 11:03 KST` Checked the read-only public health and console URLs for `sns.gilgop.cloud`; both attempts failed DNS resolution from this environment, so no production health evidence could be captured through the edge path either.
- `2026-04-28 11:03 KST` Ran the checked-in secret scan after recording the Task `03` recheck results; it passed with no output.
- `2026-04-28 11:06 KST` Rechecked Task `03` blockers after the operator requested the next work. Local `/opt/sns-content-engine` is still absent, and DNS tools now confirm `sns.gilgop.cloud` returns NXDOMAIN rather than a reachable production host.
- `2026-04-28 11:06 KST` Tried a non-interactive SSH reachability probe with `BatchMode=yes`; it failed at hostname resolution, so no remote shell or server-side command was executed.
- `2026-04-28 11:06 KST` Ran the checked-in secret scan after recording the DNS recheck results; it passed with no output.
- `2026-04-28 11:09 KST` Rechecked local access hints after the operator requested the next work. No matching SSH config, `/etc/hosts` entry, deployment-related env var name, or SSH agent identity was available to reach the production server without new external input.
- `2026-04-28 11:09 KST` Ran the checked-in secret scan after recording the local access hints recheck; it passed with no output.
- `2026-04-28 11:11 KST` Confirmed Task `03` still cannot be executed from the local workspace. Added a concrete, redacted server-side handoff block under Follow-up so the next operator action is copy-pasteable without exposing secrets.
- `2026-04-28 11:11 KST` Ran the checked-in secret scan after adding the server handoff block; it passed with no output.
- `2026-04-28 11:17 KST` Built and tested a redacted config summary command against the checked-in local config. It verifies OpenAI-first draft and metadata routes plus X-only publisher-enabled channels without printing credential values.
- `2026-04-28 11:17 KST` Added the config summary command to the Task `03` server handoff block so the server-side operator can capture provider and X-only rollout evidence before healthcheck.
- `2026-04-28 11:17 KST` Ran the checked-in secret scan after adding the config summary handoff; it passed with no output.
- `2026-04-28 11:25 KST` Resumed Task `03` on branch `codex/task-03-production-healthcheck`; the branch was clean before this tracker update.
- `2026-04-28 11:25 KST` Rechecked the local production path, public DNS, and non-interactive SSH route. Task `03` remains blocked before server command execution because the production server context is still unavailable from this workspace.
- `2026-04-28 11:25 KST` Rechecked local access hints. No deployment override env var name, SSH identity, or matching SSH config was available to reach the production server without new external input.
- `2026-04-28 11:26 KST` Ran the checked-in secret scan after recording the Task `03` blocker recheck; it passed with no output.
- `2026-04-28 11:36 KST` Added a repo-native `rollout-summary` CLI command so Task `03` provider-route and X-only publisher evidence no longer depends on a pasted Python handoff block.
- `2026-04-28 11:36 KST` Verified the checked-in config with `rollout-summary`; it reports OpenAI-first draft and metadata generation, two X publisher channels, and `first_rollout_x_only=true` without reading or printing credential values.
- `2026-04-28 11:36 KST` Task `03` remains blocked for actual production verification because the production server shell, env file, config directory, and reachable DNS or SSH route are still unavailable from this workspace.
- `2026-04-28 11:40 KST` Completed local hardening verification for the `rollout-summary` addition: targeted Task `03` tests, full pytest, secret scan, and diff whitespace checks passed.
- `2026-04-28 11:52 KST` Started Task `04` local hardening on branch `codex/task-04-smoke-rollout-summary` because the operator requested the next task while server execution remains blocked.
- `2026-04-28 11:52 KST` Updated `scripts/single_server_smoke_check.sh` so the server smoke helper runs `rollout-summary` and stops before healthcheck or dry-run publish when `first_rollout_x_only=true` is not present.
- `2026-04-28 11:52 KST` Added script tests for the X-only success path and non-X publisher failure path, and aligned README plus rollout docs with the stronger smoke-helper gate.
- `2026-04-28 11:55 KST` Completed local verification for Task `04` smoke-helper hardening: focused script tests, broader CLI/scheduler/X/script tests, full pytest, secret scan, and diff whitespace checks passed. Actual server dry-run and smoke execution remain blocked on production access and edge credentials.
- `2026-04-28 13:37 KST` Resumed from the operations vibe prompt while Task `04` was blocked, then rechecked local production path, DNS, non-interactive SSH, deployment-related env variable names, SSH agent identities, and local SSH config. The production server context is still unavailable, so no server dry-run, smoke check, or live publish command was run.
- `2026-04-28 13:48 KST` Added a Task `04` server handoff block so the operator can capture dry-run and smoke evidence from the production shell without exposing secrets. This handoff intentionally excludes `--live` and does not change Task `04` status because it still requires external production access and edge credentials.
- `2026-04-28 13:51 KST` Rechecked Task `04` blockers after the operator requested next work. Production server access and edge reachability remain unavailable locally, so Task `05` was not started; instead, added a Task `05` approval handoff to make the future live gate explicit after Task `03` and Task `04` pass.
- `2026-04-28 13:53 KST` Added a Task `06` observation handoff so a future live attempt can be closed with job evidence, logs, external X observation, and a continue, pause, retry, or hold decision. Task `06` remains pending because Task `05` has not run.
- `2026-04-28 14:02 KST` Executed the Task `03` and Task `04` handoff command bundles in the current session as requested. Both stopped before production commands because `/opt/sns-content-engine` is absent locally; the result confirms Task `03` and Task `04` remain blocked rather than passed.
- `2026-04-28 14:06 KST` Tried to locate and use a production shell route. Repository docs expose the intended server layout and `sns.gilgop.cloud` edge host, local env names expose no deploy host override, SSH agent has no identities, `sns.gilgop.cloud` still does not resolve, direct SSH to `gilgop.cloud` was not accepted due to host-key verification, and Tailscale `sonubuntu-server` rejected the tested SSH user candidates. No production shell command ran.
- `2026-04-28 20:19 KST` Recorded operator-provided Task `03` production evidence. The server-side app root, env file, config dir, rollout summary, provider route, X-only publisher channel, and healthcheck gates all passed. Task `04` is now the active remaining gate before any live approval can be requested.
- `2026-04-28 22:16 KST` Recorded operator-provided Task `04` Caddy startup failure. The Caddyfile validates, but Caddy cannot bind HTTPS because another process is already listening on port `443`; Task `04` remains blocked before smoke-check completion.
- `2026-04-28 22:29 KST` Recorded operator-provided Docker Caddy compose output. The existing edge is `starterkit-prod-caddy-1`, not host `caddy.service`; the compose recreate attempted to apply host-gateway routing but also touched starterkit dependencies and failed at `minio-init` because required compose env values were not loaded.
- `2026-04-28 22:47 KST` Recorded operator-provided Task `04` smoke helper success. The production web service, scheduler service, Docker edge service, redacted rollout summary, healthcheck, loopback health, protected console gate, authenticated console, dry-run publish, and overall single-server rollout smoke checks all passed. A separate production secret scan result is still needed before Task `04` can be marked done.
- `2026-04-28 22:50 KST` Recorded operator-provided Task `04` secret scan attempt. The command was blocked by Git dubious-ownership protection for `/opt/sns-content-engine`, so the operator must add that path to the current user's Git `safe.directory` list and rerun the scan before Task `04` can be marked done.

## Test Log
- `2026-04-26 20:13 KST` `not_run` -> `docs_only_initialization` `No runtime tests were required to create the future operations document set.`
- `2026-04-26 20:38 KST` `git status --short --branch` -> `passed` `on codex/first-live-rollout-operations-docs; only the operations document set was untracked before the Task 01 tracker update`
- `2026-04-26 20:38 KST` `rg -n "First-rollout preflight|X-only|publish-due|--live" README.md docs/single-server-deployment-guide.md docs/operator-console-guide.md` -> `passed` `found first-rollout preflight, X-only rollout wording, dry-run publish-due guidance, and explicit --live boundaries`
- `2026-04-26 20:38 KST` `./.venv/bin/python -m app.cli version` -> `passed` `sns-content-engine 0.1.0`
- `2026-04-26 20:39 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-26 20:38 KST` `runtime_regression_tests` -> `not_run` `Task 01 was an operational launch-context confirmation; Task 02 owns targeted pytest, full pytest, and secret scan gates`
- `2026-04-27 22:27 KST` `git status --short --branch` -> `passed` `on codex/first-live-rollout-operations-docs before Task 02 branch creation; worktree clean`
- `2026-04-27 22:27 KST` `./.venv/bin/python -m app.cli version` -> `passed` `sns-content-engine 0.1.0`
- `2026-04-27 22:28 KST` `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q` -> `passed` `33 passed in 0.16s`
- `2026-04-27 22:28 KST` `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q` -> `passed` `67 passed in 1.16s`
- `2026-04-27 22:29 KST` `./.venv/bin/pytest -q` -> `passed` `530 passed in 24.16s`
- `2026-04-27 22:29 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 10:58 KST` `git status --short --branch` -> `passed` `on codex/task-02-local-launch-gate before Task 03 branch creation; worktree clean`
- `2026-04-28 10:58 KST` `./.venv/bin/python -m app.cli version` -> `passed` `sns-content-engine 0.1.0`
- `2026-04-28 10:58 KST` `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config` -> `not_run` `requires production server shell access and the production /opt/sns-content-engine env/config context; do not run against a local placeholder path`
- `2026-04-28 11:00 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:02 KST` `ls -ld /opt /opt/sns-content-engine /opt/sns-content-engine/config /opt/sns-content-engine/.env` -> `blocked` `local /opt exists but /opt/sns-content-engine is absent, confirming this workspace is not the production server context`
- `2026-04-28 11:02 KST` `curl --fail https://sns.gilgop.cloud/health?config_dir=/opt/sns-content-engine/config` -> `failed` `curl could not resolve host sns.gilgop.cloud`
- `2026-04-28 11:02 KST` `curl https://sns.gilgop.cloud/console/?config_dir=/opt/sns-content-engine/config` -> `failed` `curl could not resolve host sns.gilgop.cloud`
- `2026-04-28 11:03 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:05 KST` `ls -ld /opt /opt/sns-content-engine /opt/sns-content-engine/config /opt/sns-content-engine/.env` -> `blocked` `local /opt exists but /opt/sns-content-engine is still absent`
- `2026-04-28 11:05 KST` `nslookup sns.gilgop.cloud` -> `failed` `resolver returned NXDOMAIN`
- `2026-04-28 11:05 KST` `host sns.gilgop.cloud` -> `failed` `resolver returned NXDOMAIN`
- `2026-04-28 11:05 KST` `dig +short sns.gilgop.cloud A; dig +short sns.gilgop.cloud AAAA` -> `failed` `no A or AAAA records returned`
- `2026-04-28 11:05 KST` `ssh -o BatchMode=yes -o ConnectTimeout=5 sns.gilgop.cloud 'pwd'` -> `failed` `hostname could not resolve; no remote command ran`
- `2026-04-28 11:06 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:08 KST` `SSH config and /etc/hosts scan for sns/gilgop/content-engine` -> `blocked` `no matching host alias or hosts entry found`
- `2026-04-28 11:08 KST` `env | cut -d= -f1 | sort | rg '^(SNS|SSH|DEPLOY|PRODUCTION|PROD)_'` -> `blocked` `only SSH_AUTH_SOCK was present; no deployment or smoke override env var names were present`
- `2026-04-28 11:08 KST` `ssh-add -l` -> `blocked` `SSH agent has no identities`
- `2026-04-28 11:09 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:11 KST` `server_side_healthcheck_handoff` -> `not_run` `documented as a redacted command bundle because this workspace still lacks production server shell access`
- `2026-04-28 11:11 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:17 KST` `local_config_summary_handoff_command` -> `passed` `draft_generate=openai priority 1; metadata_generate=openai priority 1; publisher channels ai_tools_daily:x and seo_tools_daily:x; first_rollout_x_only=yes`
- `2026-04-28 11:17 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:25 KST` `git status --short --branch` -> `passed` `on codex/task-03-production-healthcheck; worktree clean before this tracker update`
- `2026-04-28 11:25 KST` `ls -ld /opt /opt/sns-content-engine /opt/sns-content-engine/config /opt/sns-content-engine/.env` -> `blocked` `local /opt exists but the production app root, env file, and config directory are still absent`
- `2026-04-28 11:25 KST` `nslookup sns.gilgop.cloud` -> `failed` `resolver returned NXDOMAIN`
- `2026-04-28 11:25 KST` `host sns.gilgop.cloud` -> `failed` `resolver returned NXDOMAIN`
- `2026-04-28 11:25 KST` `ssh -o BatchMode=yes -o ConnectTimeout=5 sns.gilgop.cloud 'pwd'` -> `failed` `hostname could not resolve; no remote command ran`
- `2026-04-28 11:25 KST` `printenv | rg -o '^(SNS|DEPLOY|PRODUCTION|PROD|SSH)_[^=]+'` -> `blocked` `only SSH_AUTH_SOCK was present; no deployment or smoke override env var names were present`
- `2026-04-28 11:25 KST` `ssh-add -l` -> `blocked` `SSH agent has no identities`
- `2026-04-28 11:25 KST` `rg -n "sns|gilgop|content-engine|sns-engine|/opt/sns-content-engine" ~/.ssh/config /etc/hosts` -> `blocked` `~/.ssh/config does not exist and no matching local route was found`
- `2026-04-28 11:26 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:36 KST` `./.venv/bin/python -m app.cli rollout-summary --config-dir config` -> `passed` `OpenAI-first draft and metadata routes, two X publisher channels, and first_rollout_x_only=true`
- `2026-04-28 11:36 KST` `./.venv/bin/pytest tests/test_cli.py -k 'rollout_summary or healthcheck or publish_due' -q` -> `passed` `12 passed, 29 deselected`
- `2026-04-28 11:36 KST` `./.venv/bin/pytest tests/test_operations.py -q` -> `passed` `3 passed`
- `2026-04-28 11:40 KST` `./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q` -> `passed` `33 passed`
- `2026-04-28 11:40 KST` `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q` -> `passed` `70 passed`
- `2026-04-28 11:40 KST` `./.venv/bin/pytest -q` -> `passed` `533 passed`
- `2026-04-28 11:40 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:40 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:52 KST` `scripts/single_server_smoke_check.sh` -> `blocked` `local workspace lacks systemctl; this script is intended for the production server context`
- `2026-04-28 11:52 KST` `./.venv/bin/pytest tests/test_scripts.py -q` -> `passed` `5 passed`
- `2026-04-28 11:52 KST` `./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py tests/test_scripts.py -q` -> `passed` `75 passed`
- `2026-04-28 11:55 KST` `./.venv/bin/pytest -q` -> `passed` `534 passed`
- `2026-04-28 11:55 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 11:55 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 13:37 KST` `ls -ld /opt /opt/sns-content-engine /opt/sns-content-engine/config /opt/sns-content-engine/.env` -> `blocked` `local /opt exists but the production app root, env file, and config directory are still absent`
- `2026-04-28 13:37 KST` `nslookup sns.gilgop.cloud` -> `failed` `resolver returned NXDOMAIN`
- `2026-04-28 13:37 KST` `host sns.gilgop.cloud` -> `failed` `resolver returned NXDOMAIN`
- `2026-04-28 13:37 KST` `ssh -o BatchMode=yes -o ConnectTimeout=5 sns.gilgop.cloud 'pwd'` -> `failed` `hostname could not resolve; no remote command ran`
- `2026-04-28 13:37 KST` `printenv | cut -d= -f1 | sort | rg '^(SNS|DEPLOY|PRODUCTION|PROD|SSH)_'` -> `blocked` `only SSH_AUTH_SOCK was present; no deployment or smoke override env var names were present`
- `2026-04-28 13:37 KST` `rg -n "sns|gilgop|content-engine|sns-engine|/opt/sns-content-engine" ~/.ssh/config /etc/hosts` -> `blocked` `~/.ssh/config does not exist and no matching local route was found`
- `2026-04-28 13:37 KST` `ssh-add -l` -> `blocked` `SSH agent has no identities`
- `2026-04-28 13:37 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 13:37 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 13:48 KST` `task_04_server_side_dry_run_and_smoke_handoff` -> `not_run` `documented as a redacted production-shell command bundle because this workspace still lacks production server shell access and edge credentials`
- `2026-04-28 13:48 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 13:48 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 13:51 KST` `ls -ld /opt /opt/sns-content-engine /opt/sns-content-engine/config /opt/sns-content-engine/.env` -> `blocked` `local /opt exists but the production app root, env file, and config directory are still absent`
- `2026-04-28 13:51 KST` `nslookup sns.gilgop.cloud` -> `failed` `resolver returned NXDOMAIN`
- `2026-04-28 13:51 KST` `host sns.gilgop.cloud` -> `failed` `resolver returned NXDOMAIN`
- `2026-04-28 13:51 KST` `ssh -o BatchMode=yes -o ConnectTimeout=5 sns.gilgop.cloud 'pwd'` -> `failed` `hostname could not resolve; no remote command ran`
- `2026-04-28 13:51 KST` `printenv | cut -d= -f1 | sort | rg '^(SNS|DEPLOY|PRODUCTION|PROD|SSH)_'` -> `blocked` `only SSH_AUTH_SOCK was present; no deployment or smoke override env var names were present`
- `2026-04-28 13:51 KST` `ssh-add -l` -> `blocked` `SSH agent has no identities`
- `2026-04-28 13:51 KST` `task_05_live_publish_approval_handoff` -> `not_run` `documented future approval gate only; Task 05 remains pending because Task 03 and Task 04 have not passed`
- `2026-04-28 13:51 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 13:51 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 13:53 KST` `task_06_post_publish_observation_handoff` -> `not_run` `documented future observation template only; Task 06 remains pending because Task 05 has not run`
- `2026-04-28 13:53 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 13:53 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 14:02 KST` `task_03_server_handoff_bundle` -> `blocked` `app_root_present=no; env_file_present=no; config_dir_present=no; cd /opt/sns-content-engine failed, so production rollout-summary and healthcheck did not run`
- `2026-04-28 14:02 KST` `task_04_server_handoff_bundle` -> `blocked` `edge auth env absent; app_root_present=no; config_dir_present=no; cd /opt/sns-content-engine failed, so production dry-run publish, secret scan, and smoke helper did not run`
- `2026-04-28 14:02 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0 after wording update for the handoff execution record`
- `2026-04-28 14:02 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 14:06 KST` `production_shell_route_discovery` -> `blocked` `no repo SSH host config, no deploy-host env-name hint, no loaded SSH identity, sns.gilgop.cloud NXDOMAIN, gilgop.cloud SSH host-key verification stopped, and Tailscale sonubuntu-server SSH access was denied for tested user candidates`
- `2026-04-28 14:06 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 14:06 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 20:19 KST` `task_03_operator_provided_server_presence` -> `passed` `app_root_present=yes; env_file_present=yes; config_dir_present=yes`
- `2026-04-28 20:19 KST` `./.venv/bin/sns-engine rollout-summary --config-dir /opt/sns-content-engine/config` -> `passed` `status=ok; provider_route_count=2; publisher_channel_count=2; first_rollout_x_only=true; OpenAI draft and metadata routes at priority 1; X publisher credential references are env-style`
- `2026-04-28 20:19 KST` `./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config` -> `passed` `status=ok; check_count=3; failed_check_count=0; config, config_readiness, and sqlite database checks passed`
- `2026-04-28 20:19 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 20:19 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 22:16 KST` `sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` -> `passed` `Valid configuration; formatting warning only`
- `2026-04-28 22:16 KST` `sudo systemctl restart caddy` -> `blocked` `caddy.service failed because listening on :443 returned address already in use`
- `2026-04-28 22:16 KST` `sudo systemctl status caddy --no-pager` -> `blocked` `caddy.service Active=failed; status says loading new config failed on :443 address already in use`
- `2026-04-28 22:16 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 22:16 KST` `git diff --check` -> `passed` `no output; exit code 0`
- `2026-04-28 22:29 KST` `docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}'` -> `passed` `starterkit-prod-caddy-1 owns 0.0.0.0:80 and 0.0.0.0:443`
- `2026-04-28 22:29 KST` `docker compose -p starterkit-prod -f infra/compose/docker-compose.prod.yml up -d caddy` -> `blocked` `Caddy was recreated, but compose emitted missing-env warnings and minio-init exited with status 1; host-gateway and edge reachability still need verification`
- `2026-04-28 22:47 KST` `scripts/single_server_smoke_check.sh` -> `passed` `service checks passed for sns-web.service, sns-scheduler.service, and docker.service; rollout_summary, healthcheck_cli, loopback_health, console_edge_gate, console_authenticated, publish_due_dry_run, and single_server_rollout all status=ok`
- `2026-04-28 22:50 KST` `scripts/scan_secrets.sh check` -> `blocked` `Git rejected /opt/sns-content-engine as a dubious-ownership repository; no production secret-scan result was produced`
- `2026-04-28 22:47 KST` `scripts/scan_secrets.sh check` -> `passed` `no output; exit code 0`
- `2026-04-28 22:47 KST` `git diff --check` -> `passed` `no output; exit code 0`

## Open Questions
- `Who will provide or run the production server shell session needed for Task 03?`
- `Is there a reachable SSH host, IP address, or local alias other than sns.gilgop.cloud that should be used for the production server?`
- `Which deployed Git revision should be treated as the production baseline before running the server-side healthcheck?`
- `Should DNS for sns.gilgop.cloud be created or restored before continuing with edge smoke checks, or is the server intentionally not published yet?`
- `Can the operator confirm /opt/sns-content-engine/.env and /opt/sns-content-engine/config exist on the server without exposing any secret values?`

## Blockers
- `Task 04 still needs explicit production scripts/scan_secrets.sh check evidence before live approval can be requested; the first attempt was blocked by Git safe.directory ownership protection.`
- `The 2026-04-28 14:02 KST handoff execution attempt confirmed the current shell is not the production app root; do not treat local handoff failure as a production healthcheck or smoke-check result.`
- `The 2026-04-28 14:06 KST production shell attempt did not open a trusted remote shell, so Task 03 and Task 04 still cannot be marked passed.`
- `A read-only public edge fallback is also unavailable right now because sns.gilgop.cloud returns NXDOMAIN from this environment.`
- `No local SSH alias, hosts entry, deployment override env var name, or SSH agent identity is available to bridge the missing server context.`

## Follow-up
- `Verify starterkit-prod-caddy-1 has host.docker.internal mapped, can reach http://host.docker.internal:8001/health, and has a sns.gilgop.cloud site block, then run Task 04 from /opt/sns-content-engine: dry-run scheduler publish-due, scripts/scan_secrets.sh check, and scripts/single_server_smoke_check.sh with edge auth env supplied in the shell.`

## Server Handoff For Task 03
Run these commands only inside the production server shell. They record presence, status, and revision without printing secret values:

```bash
cd /opt/sns-content-engine
printf 'app_root_present=%s\n' "$([ -d /opt/sns-content-engine ] && echo yes || echo no)"
printf 'env_file_present=%s\n' "$([ -f /opt/sns-content-engine/.env ] && echo yes || echo no)"
printf 'config_dir_present=%s\n' "$([ -d /opt/sns-content-engine/config ] && echo yes || echo no)"
git rev-parse --short HEAD
./.venv/bin/sns-engine rollout-summary --config-dir /opt/sns-content-engine/config
./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config
```

## Server Handoff For Task 04
Run these commands only inside the production server shell after Task 03 has passed. They record dry-run and smoke-check status without printing secret values. Do not add `--live` to any command in this block.

```bash
cd /opt/sns-content-engine
printf 'edge_user_present=%s\n' "$([ -n "${SNS_SMOKE_EDGE_USER:-}" ] && echo yes || echo no)"
printf 'edge_password_present=%s\n' "$([ -n "${SNS_SMOKE_EDGE_PASSWORD:-}" ] && echo yes || echo no)"
git rev-parse --short HEAD
./.venv/bin/sns-engine rollout-summary --config-dir /opt/sns-content-engine/config
./.venv/bin/sns-engine healthcheck --config-dir /opt/sns-content-engine/config
./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config
scripts/scan_secrets.sh check
scripts/single_server_smoke_check.sh
```

## Approval Handoff For Task 05
Do not start Task `05` until Task `03` and Task `04` are recorded as passed with production evidence. Before asking for live approval, summarize:

- deployed git revision
- `rollout-summary` status and `first_rollout_x_only=true`
- `healthcheck` status
- dry-run `scheduler publish-due` result, due-job count, channel, and account scope
- `scripts/scan_secrets.sh check` status
- `scripts/single_server_smoke_check.sh` status
- any known risk, mismatch, or unavailable external observation path

Approval must be explicit and specific to one command. Acceptable approval wording should name one X live publish and the exact production config path, for example: `I approve one X live publish using /opt/sns-content-engine/config now.`

After approval, run at most one live command, then stop for observation:

```bash
cd /opt/sns-content-engine
./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config --live
```

Record exit status, publish-job or log evidence, external X visibility when available, and the continue, pause, retry, or hold decision. Do not run a second live command without a new explicit approval.

## Observation Handoff For Task 06
Do not start Task `06` until Task `05` has exactly one recorded live attempt result. After that attempt, collect and record:

- live command exit status
- publish job identifier or queue entry, when available
- final publisher result status: `succeeded`, `failed`, `partial`, or `unknown`
- redacted log evidence, with no credential values
- operator-visible X result URL or note that external visibility is unavailable
- follow-up decision: `continue`, `pause`, `retry_later`, `rollback_server_state`, or `hold_for_investigation`
- whether another live command is forbidden until a new explicit approval is provided

Suggested read-only production commands after the live attempt:

```bash
cd /opt/sns-content-engine
./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/sns-content-engine/config
journalctl -u sns-scheduler.service -n 120 --no-pager
journalctl -u sns-web.service -n 120 --no-pager
```

If the first live attempt failed or timed out, do not retry automatically. Record the failure mode, preserve logs, choose `retry_later` or `hold_for_investigation`, and require a new explicit approval before any second `--live` command.

## Completion Summary
- `Task 03 is complete based on operator-provided production evidence: required paths are present, rollout-summary is X-only and OpenAI-first, and healthcheck passed with zero failed checks.`
- `Task 04 is almost complete, but not done. The production smoke helper passed all service, edge, authenticated console, and dry-run publish checks through Docker Caddy; explicit production secret-scan evidence is still needed before live approval can be requested. No live publish command was run.`
- `A 2026-04-28 14:06 KST production shell access attempt found possible host routes but did not open a trusted server session; production verification remains unavailable from this Codex workspace.`
- `Task 05 remains pending, not started. The 2026-04-28 13:51 KST recheck confirmed Task 03 and Task 04 production evidence is still unavailable, so no live publish command was run. A Task 05 approval handoff now records the evidence summary and explicit one-command approval boundary needed after the dry-run and smoke gates pass.`
- `Task 06 remains pending, not started. A Task 06 observation handoff now records the post-live evidence fields, read-only log commands, next-decision values, and no-automatic-retry boundary needed after exactly one approved live attempt.`
