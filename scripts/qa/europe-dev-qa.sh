#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

MODE="${1:-}"
case "$MODE" in
  smoke|daily|full|stateful) ;;
  -h|--help)
    cat <<'EOF'
Usage: bash scripts/qa/europe-dev-qa.sh <mode>

Modes:
  smoke     Run the read-only smoke script only.
  daily     Run backend pytest, frontend build, Playwright e2e, then smoke.
  full      Same as daily, plus full metadata in the report files.
  stateful  Run a fresh pgBackRest backup first, then the calendar stateful QA flow.

Reports are written to:
  /opt/apps/family-hero-hub/tmp/qa-runs/YYYYMMDD-HHMMSS-<mode>/
EOF
    exit 0
    ;;
  "")
    cat <<'EOF'
Usage: bash scripts/qa/europe-dev-qa.sh <mode>

Run with --help to see available modes.
EOF
    exit 2
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    exit 2
    ;;
esac

timestamp="$(date +%Y%m%d-%H%M%S)"
report_dir="${REPO_ROOT}/tmp/qa-runs/${timestamp}-${MODE}"
mkdir -p "$report_dir"

summary_file="${report_dir}/summary.md"
metadata_file="${report_dir}/metadata.txt"
docker_compose_ps_file="${report_dir}/docker-compose-ps.txt"
git_status_file="${report_dir}/git-status.txt"

backend_log="${report_dir}/backend-pytest.log"
frontend_log="${report_dir}/frontend-build.log"
playwright_log="${report_dir}/playwright-e2e.log"
smoke_log="${report_dir}/smoke.log"
backup_log="${report_dir}/backup.log"
stateful_playwright_log="${report_dir}/stateful-playwright.log"

qa_env_file="/home/administrator/.hermes/fhh-qa.env"
stateful_qa_env_file="$qa_env_file"
backup_report_dir=""

declare -A STEP_STATUS=(
  [backend_pytest]="SKIPPED"
  [frontend_build]="SKIPPED"
  [playwright_e2e]="SKIPPED"
  [smoke]="SKIPPED"
  [backup]="SKIPPED"
  [stateful_playwright]="SKIPPED"
)

hostname_value="$(hostname)"
branch_value="$(git -C "$REPO_ROOT" branch --show-current)"
commit_value="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
runtime_note="Europe dev PostgreSQL-backed runtime via Docker Compose"
docker_services="$(cd "$REPO_ROOT" && docker compose config --services 2>/dev/null || true)"
stateful_note=""

log_suffix() {
  local path="$1"
  local label="$2"
  if [[ -f "$path" ]]; then
    printf ' (`%s`)' "$label"
  fi
  return 0
}

write_runtime_files() {
  set +e
  {
    printf 'environment=Europe dev\n'
    printf 'mode=%s\n' "$MODE"
    printf 'timestamp=%s\n' "$timestamp"
    printf 'hostname=%s\n' "$hostname_value"
    printf 'branch=%s\n' "$branch_value"
    printf 'commit=%s\n' "$commit_value"
    printf 'runtime_note=%s\n' "$runtime_note"
    printf 'report_dir=%s\n' "$report_dir"
    printf 'qa_login_token_present=%s\n' "${QA_LOGIN_TOKEN:+yes}"
    printf 'qa_login_api_base_url=%s\n' "${QA_LOGIN_API_BASE_URL:-http://127.0.0.1:8000}"
    printf 'frontend_base_url=%s\n' "${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:5173}"
    printf 'backend_base_url=%s\n' "${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
    printf 'backup_report_dir=%s\n' "${backup_report_dir}"
    printf 'docker_compose_services=\n%s\n' "$docker_services"
  } >"$metadata_file"

  (
    cd "$REPO_ROOT"
    docker compose ps
  ) >"$docker_compose_ps_file" 2>&1 || true

  (
    cd "$REPO_ROOT"
    git status --short
  ) >"$git_status_file" 2>&1 || true
  set -e
}

write_summary() {
  local exit_code="${1:-0}"
  local result_text="FAIL"
  if [[ "$exit_code" -eq 0 ]]; then
    result_text="PASS"
  fi

  write_runtime_files

  {
    printf '# Europe Dev QA Run\n\n'
    printf '%s\n' '- environment: Europe dev'
    printf '%s\n' "- mode: $MODE"
    printf '%s\n' "- timestamp: $timestamp"
    printf '%s\n' "- hostname: $hostname_value"
    printf '%s\n' "- branch: $branch_value"
    printf '%s\n' "- commit: $commit_value"
    printf '%s\n' "- runtime: $runtime_note"
    printf '%s\n' "- report dir: $report_dir"
    printf '%s\n\n' "- result: $result_text"

    printf '## Step Status\n\n'
    if [[ "$MODE" == "stateful" ]]; then
      printf '%s%s\n' "- backup: ${STEP_STATUS[backup]}" "$(log_suffix "$backup_log" "backup.log")"
      printf '%s%s\n' "- stateful playwright: ${STEP_STATUS[stateful_playwright]}" "$(log_suffix "$stateful_playwright_log" "stateful-playwright.log")"
      if [[ -n "$backup_report_dir" ]]; then
        printf '%s\n' "- backup report dir: $backup_report_dir"
      else
        printf '%s\n' "- backup report dir: unavailable"
      fi
    else
      printf '%s%s\n' "- backend pytest: ${STEP_STATUS[backend_pytest]}" "$(log_suffix "$backend_log" "backend-pytest.log")"
      printf '%s%s\n' "- frontend build: ${STEP_STATUS[frontend_build]}" "$(log_suffix "$frontend_log" "frontend-build.log")"
      printf '%s%s\n' "- playwright e2e: ${STEP_STATUS[playwright_e2e]}" "$(log_suffix "$playwright_log" "playwright-e2e.log")"
      printf '%s%s\n' "- smoke: ${STEP_STATUS[smoke]}" "$(log_suffix "$smoke_log" "smoke.log")"
    fi
    printf '\n'

    printf '## Report Files\n\n'
    printf '%s\n' '- metadata.txt'
    printf '%s\n' '- docker-compose-ps.txt'
    printf '%s\n' '- git-status.txt'
    [[ -f "$backup_log" ]] && printf '%s\n' '- backup.log'
    [[ -f "$stateful_playwright_log" ]] && printf '%s\n' '- stateful-playwright.log'
    [[ -f "$backend_log" ]] && printf '%s\n' '- backend-pytest.log'
    [[ -f "$frontend_log" ]] && printf '%s\n' '- frontend-build.log'
    [[ -f "$playwright_log" ]] && printf '%s\n' '- playwright-e2e.log'
    [[ -f "$smoke_log" ]] && printf '%s\n' '- smoke.log'
    printf '\n'

    printf '## Notes\n\n'
    printf '%s\n' '- PostgreSQL runtime confirmation: Europe dev is PostgreSQL-backed.'
    printf '%s\n' '- Smoke, daily, and full modes are read-only and do not mutate app data.'
    printf '%s\n' '- Stateful QA performs a fresh pgBackRest backup first, then runs calendar, points, reward-rejection, and reward-approval stateful flows.'
    printf '%s\n' '- Before any future state-changing automated QA outside this framework, create a fresh Europe-dev pgBackRest backup.'
    if [[ -n "$stateful_note" ]]; then
      printf '%s\n' "- $stateful_note"
    fi
    printf '\n'
    if [[ "$MODE" == "stateful" ]]; then
      printf '## Next Action\n\n'
      printf '%s\n' '- Review the backup and stateful reports before extending coverage to child-device flows.'
    elif [[ "$exit_code" -eq 0 ]]; then
      printf '## Next Action\n\n'
      printf '%s\n' '- Review the report files, then decide whether to schedule the next QA mode.'
    else
      printf '## Next Action\n\n'
      printf '%s\n' '- Inspect the failed log and rerun the relevant mode after fixing the issue.'
    fi
  } >"$summary_file"
}

trap 'write_summary "$?"' EXIT

echo "=== Europe dev QA runner ==="
echo "Mode: $MODE"
echo "Report dir: $report_dir"
echo

run_step() {
  local key="$1"
  local label="$2"
  local log_file="$3"
  shift 3

  echo "==> $label"
  if "$@" >"$log_file" 2>&1; then
    STEP_STATUS["$key"]="PASS"
    echo "PASS: $label"
    return 0
  fi

  STEP_STATUS["$key"]="FAIL"
  echo "FAIL: $label"
  echo "--- ${label} log tail ---"
  tail -n 60 "$log_file" || true
  return 1
}

run_smoke_only() {
  run_step smoke "smoke script" "$smoke_log" bash -lc "cd '$REPO_ROOT' && bash scripts/smoke/europe-dev-smoke.sh"
}

load_qa_env() {
  if [[ -f "$qa_env_file" ]]; then
    # shellcheck disable=SC1090
    set -a
    . "$qa_env_file"
    set +a
    return 0
  fi

  echo "QA env file missing: $qa_env_file" >&2
  return 1
}

load_stateful_qa_env() {
  load_qa_env || return 1
}

validate_stateful_qa_env() {
  local expected_values=(
    "QA_LOGIN_ENABLED=true"
    "APP_ENV=development"
    "QA_LOGIN_API_BASE_URL=http://127.0.0.1:8000"
    "PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173"
    "QA_LOGIN_EMAIL=qa-parent@dev.familyherohub.com"
    "QA_LOGIN_NAME=QA Parent"
  )
  local item key expected
  for item in "${expected_values[@]}"; do
    key="${item%%=*}"
    expected="${item#*=}"
    if [[ "${!key:-}" != "$expected" ]]; then
      stateful_note="Stateful QA was not started because the required QA env was invalid or missing."
      echo "QA stateful cannot run: invalid QA env in $stateful_qa_env_file. Check $key." >&2
      return 1
    fi
  done
  if [[ -z "${QA_LOGIN_TOKEN:-}" ]]; then
    stateful_note="Stateful QA was not started because the required QA env was invalid or missing."
    echo "QA stateful cannot run: missing required QA env. Configure $stateful_qa_env_file." >&2
    return 1
  fi
}

find_latest_backup_report_dir() {
  local latest_summary
  latest_summary="$(
    find "$REPO_ROOT/tmp/backups" -type f -path '*/summary.md' -printf '%T@ %p\n' 2>/dev/null \
      | sort -nr \
      | head -n1 \
      | cut -d' ' -f2-
  )"
  if [[ -n "$latest_summary" ]]; then
    dirname "$latest_summary"
  fi
}

run_stateful_pipeline() {
  if ! run_step backup "pgBackRest backup" "$backup_log" bash -lc "cd '$REPO_ROOT' && bash scripts/backup/europe-dev-pgbackrest-backup.sh"; then
    STEP_STATUS[stateful_playwright]="SKIPPED"
    stateful_note="Stateful Playwright was skipped because the backup step failed."
    return 1
  fi

  backup_report_dir="$(find_latest_backup_report_dir || true)"
  if [[ -z "$backup_report_dir" ]]; then
    STEP_STATUS[stateful_playwright]="SKIPPED"
    stateful_note="Stateful Playwright was skipped because no backup report directory could be located."
    echo "FAIL: stateful playwright" >&2
    return 1
  fi

  run_step stateful_playwright "stateful playwright" "$stateful_playwright_log" bash -lc "cd '$REPO_ROOT/frontend' && npm run test:e2e:stateful" || {
    stateful_note="Stateful Playwright failed after a confirmed pgBackRest backup."
    return 1
  }
}

run_daily_pipeline() {
  load_qa_env || return 1

  run_step backend_pytest "backend pytest" "$backend_log" bash -lc "cd '$REPO_ROOT' && docker compose exec backend python -m pytest" || return 1
  run_step frontend_build "frontend build" "$frontend_log" bash -lc "cd '$REPO_ROOT/frontend' && npm run build" || return 1

  if [[ -z "${QA_LOGIN_TOKEN:-}" ]]; then
    STEP_STATUS["playwright_e2e"]="FAIL"
    printf '%s\n' "QA_LOGIN_TOKEN is required for authenticated Playwright QA" >"$playwright_log"
    echo "FAIL: playwright e2e"
    echo "--- playwright e2e log tail ---"
    cat "$playwright_log"
    return 1
  fi

  run_step playwright_e2e "playwright e2e" "$playwright_log" bash -lc "cd '$REPO_ROOT/frontend' && npm run test:e2e" || return 1
  run_step smoke "smoke script" "$smoke_log" bash -lc "cd '$REPO_ROOT' && bash scripts/smoke/europe-dev-smoke.sh" || return 1
}

main() {
  case "$MODE" in
    smoke)
      run_smoke_only
      ;;
    daily|full)
      run_daily_pipeline
      ;;
    stateful)
      load_stateful_qa_env
      validate_stateful_qa_env || return 1
      run_stateful_pipeline
      ;;
  esac
}

main
