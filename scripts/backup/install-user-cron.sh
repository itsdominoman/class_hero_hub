#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly START_MARKER='# BEGIN class-hero-hub-backup-ops001'
readonly END_MARKER='# END class-hero-hub-backup-ops001'

install_cron() {
  local current filtered temp_file
  current="$(crontab -l 2>/dev/null || true)"
  filtered="$(sed "/^${START_MARKER}$/,/^${END_MARKER}$/d" <<<"$current")"
  temp_file="$(mktemp)"
  trap 'rm -f "$temp_file"' RETURN
  {
    printf '%s\n' "$filtered"
    printf '%s\n' "$START_MARKER"
    printf '15 2 * * * %q/scripts/scheduled/reporting-wrapper.sh chh-backup %q/scripts/backup/pgbackrest-backup.sh backup auto 2>&1 | /usr/bin/logger -t chh-backup\n' "$REPO_ROOT" "$REPO_ROOT"
    printf '15 6 * * * %q/scripts/scheduled/reporting-wrapper.sh chh-backup-health %q/scripts/backup/pgbackrest-health.sh 2>&1 | /usr/bin/logger -t chh-backup-health\n' "$REPO_ROOT" "$REPO_ROOT"
    printf '15 7 1 * * %q/scripts/scheduled/reporting-wrapper.sh chh-restore-rehearsal %q/scripts/backup/pgbackrest-restore-rehearsal.sh 2>&1 | /usr/bin/logger -t chh-restore-rehearsal\n' "$REPO_ROOT" "$REPO_ROOT"
    printf '%s\n' "$END_MARKER"
  } >"$temp_file"
  crontab "$temp_file"
}

case "${1:-}" in
  install) install_cron ;;
  status)
    crontab -l 2>/dev/null | sed -n "/^${START_MARKER}$/,/^${END_MARKER}$/p"
    ;;
  *) printf '%s\n' 'Usage: install-user-cron.sh install|status' >&2; exit 2 ;;
esac
