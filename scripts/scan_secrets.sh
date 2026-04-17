#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

find_bin() {
  local venv_bin="$1"
  local fallback_bin="$2"

  if [[ -x "$ROOT_DIR/.venv/bin/$venv_bin" ]]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/$venv_bin"
    return 0
  fi

  command -v "$fallback_bin"
}

HOOK_BIN="$(find_bin detect-secrets-hook detect-secrets-hook)"
SCAN_BIN="$(find_bin detect-secrets detect-secrets)"
MODE="${1:-check}"

if [[ "$MODE" == "check" || "$MODE" == "refresh-baseline" ]]; then
  shift || true
fi

tracked_files_cmd=(git ls-files -z)

case "$MODE" in
  check)
    if [[ ! -f "$ROOT_DIR/.secrets.baseline" ]]; then
      echo "Missing .secrets.baseline. Run 'scripts/scan_secrets.sh refresh-baseline' first." >&2
      exit 1
    fi

    if [[ "$#" -gt 0 ]]; then
      "$HOOK_BIN" --no-verify --baseline "$ROOT_DIR/.secrets.baseline" "$@"
    else
      "${tracked_files_cmd[@]}" | xargs -0 "$HOOK_BIN" --no-verify --baseline "$ROOT_DIR/.secrets.baseline"
    fi
    ;;
  refresh-baseline)
    tmp_file="$(mktemp "${TMPDIR:-/tmp}/sns-content-engine-secrets.XXXXXX")"
    trap 'rm -f "$tmp_file"' EXIT
    "${tracked_files_cmd[@]}" | xargs -0 "$SCAN_BIN" scan --no-verify > "$tmp_file"
    mv "$tmp_file" "$ROOT_DIR/.secrets.baseline"
    trap - EXIT
    ;;
  *)
    echo "Usage: scripts/scan_secrets.sh [check|refresh-baseline] [files...]" >&2
    exit 1
    ;;
esac
