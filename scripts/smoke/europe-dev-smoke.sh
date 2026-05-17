#!/usr/bin/env bash

set -Eeuo pipefail

BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-http://127.0.0.1:5173}"
DEV_PUBLIC_URL="${DEV_PUBLIC_URL:-https://dev.familyherohub.com}"
STATE_CHANGING=0

usage() {
  cat <<'EOF'
Usage: bash scripts/smoke/europe-dev-smoke.sh [--state-changing]

Read-only Europe-dev smoke checks default to loopback URLs:
  BACKEND_BASE_URL=http://127.0.0.1:8000
  FRONTEND_BASE_URL=http://127.0.0.1:5173

The public dev URL is probed for information only and is not treated as a pass/fail signal.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --state-changing)
      STATE_CHANGING=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$STATE_CHANGING" -eq 1 ]]; then
  echo "--state-changing is reserved for future QA flows and is not implemented yet." >&2
  echo "Before any future state-changing automated QA, confirm a fresh Europe-dev pgBackRest backup." >&2
  exit 2
fi

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

warn() {
  echo "WARN: $*" >&2
}

join_expected() {
  local first=1
  for code in "$@"; do
    if [[ "$first" -eq 1 ]]; then
      printf '%s' "$code"
      first=0
    else
      printf ', %s' "$code"
    fi
  done
}

status_allowed() {
  local code="$1"
  shift
  local expected
  for expected in "$@"; do
    [[ "$code" == "$expected" ]] && return 0
  done
  return 1
}

request() {
  local method="$1"
  local url="$2"
  local label="$3"
  local headers_file="$tmpdir/${label//[^A-Za-z0-9._-]/_}.headers"
  local body_file="$tmpdir/${label//[^A-Za-z0-9._-]/_}.body"
  local code=""

  if ! code="$(curl -sS --max-time 20 --connect-timeout 5 -X "$method" -D "$headers_file" -o "$body_file" -w '%{http_code}' "$url")"; then
    echo "Request failed: $method $url" >&2
    [[ -f "$headers_file" ]] && { echo "--- headers ---" >&2; cat "$headers_file" >&2; }
    [[ -f "$body_file" ]] && { echo "--- body ---" >&2; sed -n '1,120p' "$body_file" >&2; }
    return 1
  fi

  printf '%s\n' "$code"
}

dump_failure() {
  local headers_file="$1"
  local body_file="$2"
  echo "--- headers ---" >&2
  [[ -f "$headers_file" ]] && cat "$headers_file" >&2 || true
  echo "--- body ---" >&2
  [[ -f "$body_file" ]] && sed -n '1,120p' "$body_file" >&2 || true
}

check_status() {
  local label="$1"
  local method="$2"
  local url="$3"
  shift 3
  local expected_statuses=("$@")
  local headers_file="$tmpdir/${label//[^A-Za-z0-9._-]/_}.headers"
  local body_file="$tmpdir/${label//[^A-Za-z0-9._-]/_}.body"
  local code=""

  echo "==> $label"
  if ! code="$(curl -sS --max-time 20 --connect-timeout 5 -X "$method" -D "$headers_file" -o "$body_file" -w '%{http_code}' "$url")"; then
    echo "Request failed: $method $url" >&2
    dump_failure "$headers_file" "$body_file"
    return 1
  fi

  if ! status_allowed "$code" "${expected_statuses[@]}"; then
    echo "Unexpected status for $label: $code (expected $(join_expected "${expected_statuses[@]}"))" >&2
    dump_failure "$headers_file" "$body_file"
    return 1
  fi

  echo "OK: $label -> $code"
}

check_body_contains() {
  local label="$1"
  local body_file="$2"
  local pattern="$3"
  if ! grep -Eq "$pattern" "$body_file"; then
    echo "Body assertion failed for $label: missing pattern $pattern" >&2
    sed -n '1,120p' "$body_file" >&2
    return 1
  fi
}

probe_public_url() {
  local url="$1"
  local label="$2"
  local headers_file="$tmpdir/${label//[^A-Za-z0-9._-]/_}.headers"
  local body_file="$tmpdir/${label//[^A-Za-z0-9._-]/_}.body"
  local code=""

  echo "==> $label (informational only)"
  if ! code="$(curl -sS --max-time 20 --connect-timeout 5 -I -D "$headers_file" -o "$body_file" -w '%{http_code}' "$url")"; then
    warn "$label request failed; this does not fail the smoke run"
    [[ -f "$headers_file" ]] && { echo "--- headers ---" >&2; cat "$headers_file" >&2; }
    return 0
  fi

  case "$code" in
    200|301|302|303|307|308|403)
      echo "INFO: $label -> $code"
      ;;
    5??)
      warn "$label returned a 5xx status ($code)"
      ;;
    *)
      echo "INFO: $label -> $code"
      ;;
  esac
}

echo "=== Europe dev smoke checks ==="
echo "Backend base URL:  $BACKEND_BASE_URL"
echo "Frontend base URL: $FRONTEND_BASE_URL"
echo "Public dev URL:    $DEV_PUBLIC_URL"
echo
echo "Read-only by default. No login, no writes, no data creation."
echo

check_status "backend health" GET "${BACKEND_BASE_URL%/}/api/health" 200
check_body_contains "backend health" "$tmpdir/backend_health.body" '"status"[[:space:]]*:[[:space:]]*"ok"'

check_status "frontend root" GET "${FRONTEND_BASE_URL%/}/" 200
check_status "frontend login" GET "${FRONTEND_BASE_URL%/}/login" 200
check_status "frontend request access" GET "${FRONTEND_BASE_URL%/}/request-access" 200
check_status "frontend privacy" GET "${FRONTEND_BASE_URL%/}/privacy" 200
check_status "frontend terms" GET "${FRONTEND_BASE_URL%/}/terms" 200
check_status "frontend contact" GET "${FRONTEND_BASE_URL%/}/contact" 200
check_status "frontend parent" GET "${FRONTEND_BASE_URL%/}/parent" 200
check_status "frontend calendar" GET "${FRONTEND_BASE_URL%/}/calendar" 200
check_status "frontend admin users" GET "${FRONTEND_BASE_URL%/}/admin/users" 200

check_status "api me unauthenticated" GET "${BACKEND_BASE_URL%/}/api/me" 401 403
check_status "api children unauthenticated" GET "${BACKEND_BASE_URL%/}/api/children/" 401 403
check_status "api rewards unauthenticated" GET "${BACKEND_BASE_URL%/}/api/rewards/" 401 403
check_status "api auth google login redirect" GET "${BACKEND_BASE_URL%/}/api/auth/google/login" 302 303 307 308

probe_public_url "${DEV_PUBLIC_URL%/}/" "public dev root"
probe_public_url "${DEV_PUBLIC_URL%/}/api/health" "public dev api health"

echo
echo "Smoke checks completed."
echo "State-changing flows remain intentionally disabled in this script."
