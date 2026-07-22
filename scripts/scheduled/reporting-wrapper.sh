#!/usr/bin/env bash
set -Eeuo pipefail

if (( $# < 2 )); then
  printf '%s\n' 'Usage: reporting-wrapper.sh JOB_NAME COMMAND [ARG ...]' >&2
  exit 2
fi

readonly JOB_NAME="$1"
shift
readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly STATUS_DIR="${REPO_ROOT}/tmp/scheduled-status"
readonly STATUS_FILE="${STATUS_DIR}/${JOB_NAME}.status"

mkdir -p "$STATUS_DIR"
printf 'job=%s state=running timestamp=%s\n' "$JOB_NAME" "$(date --iso-8601=seconds)"

set +e
"$@"
exit_code="$?"
set -e

temp_file="$(mktemp "${STATUS_DIR}/${JOB_NAME}.XXXXXX")"
if (( exit_code == 0 )); then
  printf 'job=%s state=ok timestamp=%s exit_code=0\n' \
    "$JOB_NAME" "$(date --iso-8601=seconds)" >"$temp_file"
else
  printf 'job=%s state=failed timestamp=%s exit_code=%s\n' \
    "$JOB_NAME" "$(date --iso-8601=seconds)" "$exit_code" >"$temp_file"
fi
mv -f "$temp_file" "$STATUS_FILE"
chmod 0644 "$STATUS_FILE"
cat "$STATUS_FILE"
exit "$exit_code"
