#!/usr/bin/env bash
# Shared settings for the CI scripts. Jenkins sets BUILD_NUMBER and GIT_COMMIT;
# when a script runs on a laptop the values fall back to "local" and git.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

IMAGE_NAME="${IMAGE_NAME:-citemap-app}"
BUILD_NUMBER="${BUILD_NUMBER:-local}"
GIT_COMMIT="${GIT_COMMIT:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
SHORT_SHA="${GIT_COMMIT:0:7}"
IMAGE_TAG="${IMAGE_TAG:-${BUILD_NUMBER}-${SHORT_SHA}}"
REPORTS_DIR="${REPORTS_DIR:-reports}"

# Optional overrides of the base images and extra `docker build` options
# (for example a registry mirror or --network host behind a proxy).
BUILD_ARGS=()
[[ -n "${PYTHON_IMAGE:-}" ]] && BUILD_ARGS+=(--build-arg "PYTHON_IMAGE=${PYTHON_IMAGE}")
[[ -n "${NODE_IMAGE:-}" ]] && BUILD_ARGS+=(--build-arg "NODE_IMAGE=${NODE_IMAGE}")
read -r -a EXTRA_BUILD_OPTS <<< "${DOCKER_BUILD_OPTS:-}"

log() { printf '\n==> %s\n' "$*"; }

# run_tests <target> <name>: build a test image and run it, copying the reports
# out of the container whether the tests pass or fail.
run_tests() {
  local target="$1" name="$2"
  local image="${IMAGE_NAME}-test:${name}-${IMAGE_TAG}"
  local container="${IMAGE_NAME}-${name}-test-${IMAGE_TAG}"
  log "Building ${target} image ${image}"
  docker build "${EXTRA_BUILD_OPTS[@]}" "${BUILD_ARGS[@]}" --target "${target}" -t "${image}" .
  log "Running ${name} tests"
  docker rm -f "${container}" >/dev/null 2>&1 || true
  local status=0
  docker run --name "${container}" "${image}" || status=$?
  mkdir -p "${REPORTS_DIR}"
  docker cp "${container}:/reports/." "${REPORTS_DIR}/" || true
  docker rm "${container}" >/dev/null
  return "${status}"
}
