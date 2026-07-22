#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-family-hero-hub-postgres}"
readonly STANZA="${PGBACKREST_STANZA:-fhh}"
readonly STATUS_DIR="${BACKUP_STATUS_DIR:-${REPO_ROOT}/tmp/backup-status}"
readonly STATUS_FILE="${STATUS_DIR}/backup.json"
readonly LOCK_FILE="${STATUS_DIR}/backup.lock"

mkdir -p "$STATUS_DIR"

write_failure_status() {
  local exit_code="$1"
  local temp_file
  temp_file="$(mktemp "${STATUS_DIR}/backup.json.XXXXXX")"
  jq -n \
    --arg timestamp "$(date --iso-8601=seconds)" \
    --argjson exit_code "$exit_code" \
    '{state:"failed", timestamp:$timestamp, exit_code:$exit_code}' >"$temp_file"
  mv -f "$temp_file" "$STATUS_FILE"
  chmod 0644 "$STATUS_FILE"
}

on_exit() {
  local exit_code="$?"
  if (( exit_code != 0 )); then
    write_failure_status "$exit_code"
  fi
  exit "$exit_code"
}
trap on_exit EXIT

usage() {
  printf '%s\n' \
    'Usage: pgbackrest-backup.sh init|backup [auto|full|diff|incr]|status|dry-run'
}

run_pgbackrest() {
  docker exec --user postgres "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" "$@"
}

require_runtime() {
  command -v docker >/dev/null
  command -v jq >/dev/null
  docker inspect "$CONTAINER_NAME" >/dev/null
  docker exec "$CONTAINER_NAME" sh -ceu '
    test -n "${PGBACKREST_REPO1_CIPHER_PASS:-}"
    test -n "${PGBACKREST_REPO2_CIPHER_PASS:-}"
  '
}

latest_label() {
  local repo="$1"
  run_pgbackrest --repo="$repo" info --output=json \
    | jq -r '.[0].backup[-1].label // "none"'
}

initialize_repositories() {
  run_pgbackrest stanza-create
  run_pgbackrest check
}

choose_type() {
  local requested="${1:-auto}"
  case "$requested" in
    auto)
      if [[ "$(date +%u)" == 7 ]]; then
        printf '%s\n' full
      else
        printf '%s\n' diff
      fi
      ;;
    full|diff|incr) printf '%s\n' "$requested" ;;
    *) usage >&2; return 2 ;;
  esac
}

verify_repository() {
  local repo="$1"
  local info_json
  info_json="$(run_pgbackrest --repo="$repo" info --output=json)"
  jq -e '
    length == 1 and
    .[0].status.code == 0 and
    .[0].repo[0].cipher == "aes-256-cbc" and
    (.[0].backup | length) > 0 and
    .[0].backup[-1].error == false
  ' <<<"$info_json" >/dev/null
}

write_success_status() {
  local backup_type="$1"
  local repo1_json repo2_json temp_file
  repo1_json="$(run_pgbackrest --repo=1 info --output=json)"
  repo2_json="$(run_pgbackrest --repo=2 info --output=json)"
  temp_file="$(mktemp "${STATUS_DIR}/backup.json.XXXXXX")"
  jq -n \
    --arg timestamp "$(date --iso-8601=seconds)" \
    --arg backup_type "$backup_type" \
    --arg repo1_label "$(jq -r '.[0].backup[-1].label' <<<"$repo1_json")" \
    --arg repo2_label "$(jq -r '.[0].backup[-1].label' <<<"$repo2_json")" \
    --argjson repo1_size "$(jq -r '.[0].backup[-1].info.repository.size' <<<"$repo1_json")" \
    --argjson repo2_size "$(jq -r '.[0].backup[-1].info.repository.size' <<<"$repo2_json")" \
    '{state:"ok", timestamp:$timestamp, type:$backup_type,
      local:{label:$repo1_label, repository_bytes:$repo1_size},
      off_host:{label:$repo2_label, repository_bytes:$repo2_size}}' >"$temp_file"
  mv -f "$temp_file" "$STATUS_FILE"
  chmod 0644 "$STATUS_FILE"
  cat "$STATUS_FILE"
}

main() {
  local command="${1:-}"
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    printf '%s\n' 'A backup or repository operation is already running.' >&2
    return 75
  fi

  case "$command" in
    dry-run)
      printf 'repo_root=%s\ncontainer=%s\nstanza=%s\nplanned_type=%s\nrepositories=local,off-host-sftp\n' \
        "$REPO_ROOT" "$CONTAINER_NAME" "$STANZA" "$(choose_type "${2:-auto}")"
      ;;
    init)
      require_runtime
      initialize_repositories
      verify_repository 1 || true
      verify_repository 2 || true
      printf '%s\n' 'Encrypted local and off-host repositories initialized.'
      ;;
    backup)
      require_runtime
      local backup_type before_repo1 before_repo2 after_repo1 after_repo2
      backup_type="$(choose_type "${2:-auto}")"
      before_repo1="$(latest_label 1)"
      before_repo2="$(latest_label 2)"
      run_pgbackrest --repo=1 --type="$backup_type" backup
      run_pgbackrest --repo=2 --type="$backup_type" backup
      run_pgbackrest check
      run_pgbackrest --repo=1 expire
      run_pgbackrest --repo=2 expire
      verify_repository 1
      verify_repository 2
      after_repo1="$(latest_label 1)"
      after_repo2="$(latest_label 2)"
      [[ "$after_repo1" != none && "$after_repo1" != "$before_repo1" ]]
      [[ "$after_repo2" != none && "$after_repo2" != "$before_repo2" ]]
      write_success_status "$backup_type"
      ;;
    status)
      require_runtime
      verify_repository 1
      verify_repository 2
      [[ -s "$STATUS_FILE" ]]
      jq -e '.state == "ok"' "$STATUS_FILE" >/dev/null
      cat "$STATUS_FILE"
      ;;
    *) usage >&2; return 2 ;;
  esac
}

main "$@"
