#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: capture_fhh_screenshots.sh <flow-name>" >&2
  echo "Supported: parent-dashboard, add-child-flow, child-dashboard, rewards, reward-request, allowance, parent-tools" >&2
  exit 2
fi

FLOW_NAME="$1"

if [[ -f /home/administrator/.hermes/fhh-qa.env ]]; then
  # shellcheck disable=SC1090
  set -a
  . /home/administrator/.hermes/fhh-qa.env
  set +a
fi

export NODE_PATH="${REPO_ROOT}/frontend/node_modules${NODE_PATH:+:${NODE_PATH}}"
exec node "${SCRIPT_DIR}/capture_fhh_screenshots.js" "$FLOW_NAME"
