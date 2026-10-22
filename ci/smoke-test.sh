#!/usr/bin/env bash
# Stage "Smoke test": start the new image and exercise the API end to end.
source "$(dirname "$0")/lib.sh"
container="${IMAGE_NAME}-smoke-${IMAGE_TAG}"
docker rm -f "${container}" >/dev/null 2>&1 || true
log "Starting ${IMAGE_NAME}:${IMAGE_TAG} as ${container}"
docker run -d --name "${container}" "${IMAGE_NAME}:${IMAGE_TAG}" >/dev/null
trap 'docker rm -f "${container}" >/dev/null 2>&1 || true' EXIT
bash ci/wait-and-check.sh "${container}"
