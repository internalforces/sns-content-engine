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
  [[ "$normalized" == ".secrets.baseline" || "$normalized" == *.egg-info/* ]]
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

    CHECK_FILES=()
    if [[ "$#" -gt 0 ]]; then
      FILTERED_FILES=()
      filter_input_files "$@"

      if [[ "${#FILTERED_FILES[@]}" -eq 0 ]]; then
        exit 0
      fi

      CHECK_FILES=("${FILTERED_FILES[@]}")
    else
      TRACKED_FILES=()
      collect_tracked_files
      CHECK_FILES=("${TRACKED_FILES[@]}")
    fi

    tmp_baseline="$(mktemp "${TMPDIR:-/tmp}/sns-content-engine-baseline-check.XXXXXX")"
    trap 'rm -f "$tmp_baseline"' EXIT
    cp "$ROOT_DIR/.secrets.baseline" "$tmp_baseline"

    set +e
    hook_output="$("$HOOK_BIN" --no-verify --baseline "$tmp_baseline" "${CHECK_FILES[@]}" 2>&1)"
    hook_status=$?
    set -e

    trap - EXIT
    rm -f "$tmp_baseline"

    case "$hook_status" in
      0)
        ;;
      1)
        printf '%s\n' "$hook_output" >&2
        exit 1
        ;;
      3)
        cat >&2 <<'EOF'
Secret baseline is out of date for the current tree.
Run 'scripts/scan_secrets.sh refresh-baseline' and commit '.secrets.baseline'.
EOF
        exit 1
        ;;
      *)
        if [[ -n "$hook_output" ]]; then
          printf '%s\n' "$hook_output" >&2
        fi
        exit "$hook_status"
        ;;
    esac
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
