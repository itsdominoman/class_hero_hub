#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLAYWRIGHT_IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.59.1-jammy}"
MODE="${1:-daily}"

case "$MODE" in
  daily|stateful|public|auth|visual|child) ;;
  *)
    echo "Unknown mode: $MODE" >&2
    echo "Usage: bash ./scripts/run-playwright-e2e.sh [daily|stateful|public|auth|visual|child]" >&2
    exit 2
    ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for npm run test:e2e on this host." >&2
  echo "Fallback: cd ${FRONTEND_DIR} && npm run test:e2e:local" >&2
  exit 1
fi

run_suffix="$MODE"
if [[ "$MODE" == "visual" ]]; then
  run_suffix="visual-layout"
fi
run_id="${QA_RUN_ID:-$(date +%Y%m%d-%H%M%S)-${run_suffix}}"
export QA_RUN_ID="$run_id"

exec docker run --rm \
  --network host \
  --user "$(id -u):$(id -g)" \
  -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
  -e PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:5173}" \
  -e QA_LOGIN_API_BASE_URL="${QA_LOGIN_API_BASE_URL:-http://127.0.0.1:8000}" \
  -e QA_LOGIN_ENABLED="${QA_LOGIN_ENABLED:-}" \
  -e QA_LOGIN_TOKEN="${QA_LOGIN_TOKEN:-}" \
  -e QA_LOGIN_EMAIL="${QA_LOGIN_EMAIL:-}" \
  -e QA_LOGIN_NAME="${QA_LOGIN_NAME:-}" \
  -e QA_CHILD_LOGIN_ENABLED="${QA_CHILD_LOGIN_ENABLED:-}" \
  -e QA_CHILD_LOGIN_TOKEN="${QA_CHILD_LOGIN_TOKEN:-}" \
  -e QA_ARTIFACT_ROOT="${QA_ARTIFACT_ROOT:-/repo/tmp/qa-runs}" \
  -e QA_RUN_ID="$run_id" \
  -e CI="${CI:-1}" \
  -e HOME=/tmp \
  -e NPM_CONFIG_CACHE=/tmp/.npm \
  -v "${REPO_ROOT}:/repo" \
  -v "${FRONTEND_DIR}:/work" \
  -w /work \
  "${PLAYWRIGHT_IMAGE}" \
  bash -lc "
    case '$MODE' in
      stateful)
        npm run test:e2e:stateful:local
        ;;
      public)
        npm run test:e2e:local -- e2e/public-pages.spec.ts
        ;;
      auth)
        npm run test:e2e:local -- e2e/authenticated-qa-login.spec.ts
        ;;
      visual)
        npm run test:e2e:local -- e2e/visual-layout.spec.ts
        ;;
      child)
        npm run test:e2e:local -- e2e/authenticated-child-pages.spec.ts
        ;;
      *)
        npm run test:e2e:local
        ;;
    esac"
