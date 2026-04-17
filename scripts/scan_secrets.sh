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

is_excluded_file() {
  local normalized="${1#./}"
  [[ "$normalized" == ".secrets.baseline" ]]
}

collect_tracked_files() {
  local file

  while IFS= read -r -d '' file; do
    if ! is_excluded_file "$file"; then
      TRACKED_FILES+=("$file")
    fi
  done < <(git ls-files -z)
}

filter_input_files() {
  local file

  for file in "$@"; do
    if ! is_excluded_file "$file"; then
      FILTERED_FILES+=("$file")
    fi
  done
}

case "$MODE" in
  check)
    if [[ ! -f "$ROOT_DIR/.secrets.baseline" ]]; then
      echo "Missing .secrets.baseline. Run 'scripts/scan_secrets.sh refresh-baseline' first." >&2
      exit 1
    fi

    if [[ "$#" -gt 0 ]]; then
      FILTERED_FILES=()
      filter_input_files "$@"

      if [[ "${#FILTERED_FILES[@]}" -eq 0 ]]; then
        exit 0
      fi

      "$HOOK_BIN" --no-verify --baseline "$ROOT_DIR/.secrets.baseline" "${FILTERED_FILES[@]}"
    else
      TRACKED_FILES=()
      collect_tracked_files
      "$HOOK_BIN" --no-verify --baseline "$ROOT_DIR/.secrets.baseline" "${TRACKED_FILES[@]}"
    fi
    ;;
  refresh-baseline)
    tmp_file="$(mktemp "${TMPDIR:-/tmp}/sns-content-engine-secrets.XXXXXX")"
    trap 'rm -f "$tmp_file"' EXIT
    TRACKED_FILES=()
    collect_tracked_files
    "$SCAN_BIN" scan --no-verify "${TRACKED_FILES[@]}" > "$tmp_file"
    mv "$tmp_file" "$ROOT_DIR/.secrets.baseline"
    trap - EXIT
    ;;
  *)
    echo "Usage: scripts/scan_secrets.sh [check|refresh-baseline] [files...]" >&2
    exit 1
    ;;
esac
