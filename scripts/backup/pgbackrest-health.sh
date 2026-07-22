#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-family-hero-hub-postgres}"
readonly STANZA="${PGBACKREST_STANZA:-fhh}"
readonly MAX_AGE_SECONDS="${BACKUP_MAX_AGE_SECONDS:-108000}"
readonly STATUS_DIR="${BACKUP_STATUS_DIR:-${REPO_ROOT}/tmp/backup-status}"
readonly STATUS_FILE="${STATUS_DIR}/health.json"
readonly LOCK_FILE="${STATUS_DIR}/health.lock"

mkdir -p "$STATUS_DIR"

on_exit() {
  local exit_code="$?"
  if (( exit_code != 0 )); then
    local temp_file
    temp_file="$(mktemp "${STATUS_DIR}/health.json.XXXXXX")"
    jq -n \
      --arg timestamp "$(date --iso-8601=seconds)" \
      --argjson exit_code "$exit_code" \
      '{state:"failed", timestamp:$timestamp, exit_code:$exit_code}' >"$temp_file"
    mv -f "$temp_file" "$STATUS_FILE"
    chmod 0644 "$STATUS_FILE"
  fi
  exit "$exit_code"
}
trap on_exit EXIT

run_pgbackrest() {
  docker exec --user postgres "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" "$@"
}

main() {
  local now repo1_json repo2_json repo1_stop repo2_stop temp_file
  exec 9>"$LOCK_FILE"
  flock -n 9 || { printf '%s\n' 'Health verification is already running.' >&2; return 75; }

  docker inspect "$CONTAINER_NAME" >/dev/null
  repo1_json="$(run_pgbackrest --repo=1 info --output=json)"
  repo2_json="$(run_pgbackrest --repo=2 info --output=json)"
  for info_json in "$repo1_json" "$repo2_json"; do
    jq -e '
      length == 1 and
      .[0].status.code == 0 and
      .[0].repo[0].cipher == "aes-256-cbc" and
      (.[0].backup | length) > 0 and
      .[0].backup[-1].error == false
    ' <<<"$info_json" >/dev/null
  done

  now="$(date +%s)"
  repo1_stop="$(jq -r '.[0].backup[-1].timestamp.stop' <<<"$repo1_json")"
  repo2_stop="$(jq -r '.[0].backup[-1].timestamp.stop' <<<"$repo2_json")"
  (( now - repo1_stop <= MAX_AGE_SECONDS ))
  (( now - repo2_stop <= MAX_AGE_SECONDS ))

  run_pgbackrest check
  curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/api/health >/dev/null

  temp_file="$(mktemp "${STATUS_DIR}/health.json.XXXXXX")"
  jq -n \
    --arg timestamp "$(date --iso-8601=seconds)" \
    --arg repo1_label "$(jq -r '.[0].backup[-1].label' <<<"$repo1_json")" \
    --arg repo2_label "$(jq -r '.[0].backup[-1].label' <<<"$repo2_json")" \
    --argjson repo1_age "$((now - repo1_stop))" \
    --argjson repo2_age "$((now - repo2_stop))" \
    '{state:"ok", timestamp:$timestamp,
      local:{label:$repo1_label, age_seconds:$repo1_age, cipher:"aes-256-cbc"},
      off_host:{label:$repo2_label, age_seconds:$repo2_age, cipher:"aes-256-cbc"},
      application_health:"ok"}' >"$temp_file"
  mv -f "$temp_file" "$STATUS_FILE"
  chmod 0644 "$STATUS_FILE"
  cat "$STATUS_FILE"
}

main "$@"
