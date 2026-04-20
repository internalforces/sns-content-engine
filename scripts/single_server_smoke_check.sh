#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${SNS_SMOKE_APP_ROOT:-/opt/sns-content-engine}"
CONFIG_DIR="${SNS_SMOKE_CONFIG_DIR:-$APP_ROOT/config}"
DATABASE_URL="${SNS_SMOKE_DATABASE_URL:-}"
SNS_ENGINE_BIN="${SNS_SMOKE_ENGINE_BIN:-$APP_ROOT/.venv/bin/sns-engine}"
SYSTEMCTL_BIN="${SNS_SMOKE_SYSTEMCTL_BIN:-systemctl}"
CURL_BIN="${SNS_SMOKE_CURL_BIN:-curl}"
WEB_SERVICE="${SNS_SMOKE_WEB_SERVICE:-sns-web.service}"
SCHEDULER_SERVICE="${SNS_SMOKE_SCHEDULER_SERVICE:-sns-scheduler.service}"
EDGE_SERVICE="${SNS_SMOKE_EDGE_SERVICE:-caddy.service}"
LOCAL_HEALTH_URL="${SNS_SMOKE_LOCAL_HEALTH_URL:-http://127.0.0.1:8000/health?config_dir=$CONFIG_DIR}"
PUBLIC_CONSOLE_URL="${SNS_SMOKE_PUBLIC_CONSOLE_URL:-https://sns.gilgop.cloud/console/?config_dir=$CONFIG_DIR}"
EDGE_USER="${SNS_SMOKE_EDGE_USER:-}"
EDGE_PASSWORD="${SNS_SMOKE_EDGE_PASSWORD:-}"
CONSOLE_MARKER="${SNS_SMOKE_CONSOLE_MARKER:-sns-content-engine}"

require_command() {
  local command_name="$1"

  if [[ "$command_name" == */* ]]; then
    if [[ ! -x "$command_name" ]]; then
      printf 'missing executable: %s\n' "$command_name" >&2
      exit 1
    fi
    return 0
  fi

  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'missing command: %s\n' "$command_name" >&2
    exit 1
  fi
}

fail_check() {
  local label="$1"
  local message="${2:-}"

  printf '%s status=failed\n' "$label" >&2
  if [[ -n "$message" ]]; then
    printf '%s\n' "$message" >&2
  fi
  exit 1
}

pass_check() {
  local label="$1"
  printf '%s status=ok\n' "$label"
}

run_and_capture() {
  local label="$1"
  shift

  local output
  if ! output="$("$@" 2>&1)"; then
    fail_check "$label" "$output"
  fi
  printf '%s\n' "$output"
}

check_service() {
  local service_name="$1"
  local label="smoke_check=service service=$service_name"

  if ! "$SYSTEMCTL_BIN" is-active --quiet "$service_name"; then
    fail_check "$label" "service is not active"
  fi
  pass_check "$label"
}

require_command "$SYSTEMCTL_BIN"
require_command "$CURL_BIN"
require_command "$SNS_ENGINE_BIN"

if [[ -z "$EDGE_USER" || -z "$EDGE_PASSWORD" ]]; then
  fail_check \
    "smoke_check=edge_credentials" \
    "set SNS_SMOKE_EDGE_USER and SNS_SMOKE_EDGE_PASSWORD for the protected console check"
fi

check_service "$WEB_SERVICE"
check_service "$SCHEDULER_SERVICE"
check_service "$EDGE_SERVICE"

healthcheck_args=("$SNS_ENGINE_BIN" healthcheck --config-dir "$CONFIG_DIR")
publish_due_args=("$SNS_ENGINE_BIN" scheduler publish-due --config-dir "$CONFIG_DIR")
if [[ -n "$DATABASE_URL" ]]; then
  healthcheck_args+=(--database-url "$DATABASE_URL")
  publish_due_args+=(--database-url "$DATABASE_URL")
fi

healthcheck_output="$(run_and_capture "smoke_check=healthcheck_cli" "${healthcheck_args[@]}")"
if ! grep -Fq "status=ok" <<<"$healthcheck_output"; then
  fail_check "smoke_check=healthcheck_cli" "$healthcheck_output"
fi
pass_check "smoke_check=healthcheck_cli"

if ! "$CURL_BIN" --silent --show-error --fail "$LOCAL_HEALTH_URL" >/dev/null; then
  fail_check "smoke_check=loopback_health" "failed to fetch $LOCAL_HEALTH_URL"
fi
pass_check "smoke_check=loopback_health"

anonymous_console_status="$("$CURL_BIN" --silent --show-error --output /dev/null --write-out "%{http_code}" "$PUBLIC_CONSOLE_URL")"
if [[ "$anonymous_console_status" != "401" && "$anonymous_console_status" != "403" ]]; then
  fail_check \
    "smoke_check=console_edge_gate" \
    "expected 401 or 403 from anonymous console request, got $anonymous_console_status"
fi
pass_check "smoke_check=console_edge_gate"

console_html="$("$CURL_BIN" --silent --show-error --fail --user "$EDGE_USER:$EDGE_PASSWORD" "$PUBLIC_CONSOLE_URL")"
if ! grep -Fq "$CONSOLE_MARKER" <<<"$console_html"; then
  fail_check \
    "smoke_check=console_authenticated" \
    "authenticated console response did not include '$CONSOLE_MARKER'"
fi
pass_check "smoke_check=console_authenticated"

publish_due_output="$(run_and_capture "smoke_check=publish_due_dry_run" "${publish_due_args[@]}")"
if ! grep -Fq "executor mode: fake dry-run (no state changes)" <<<"$publish_due_output"; then
  fail_check "smoke_check=publish_due_dry_run" "$publish_due_output"
fi
if grep -Fq "executor mode: live publish via configured publishers" <<<"$publish_due_output"; then
  fail_check "smoke_check=publish_due_dry_run" "publish-due unexpectedly reported live mode"
fi
pass_check "smoke_check=publish_due_dry_run"

pass_check "smoke_check=single_server_rollout"
