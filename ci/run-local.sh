#!/usr/bin/env bash
# Run the whole pipeline on a machine with Docker, without Jenkins.
# Usage: bash ci/run-local.sh [--deploy]
source "$(dirname "$0")/lib.sh"
start=$(date +%s)
step() { local s=$(date +%s); bash "$@"; echo "[timing] $1 $(( $(date +%s) - s ))s"; }
step ci/test-backend.sh
step ci/test-frontend.sh
step ci/build-image.sh
step ci/smoke-test.sh
if [[ "${1:-}" == "--deploy" ]]; then step ci/deploy-staging.sh; fi
bash ci/cleanup.sh
echo "[timing] total $(( $(date +%s) - start ))s"
