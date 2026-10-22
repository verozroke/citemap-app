#!/usr/bin/env bash
# Stage "Deploy to staging": replace the staging container with the new image
# and verify it. The staging server is the Docker host itself, port STAGING_PORT.
source "$(dirname "$0")/lib.sh"
STAGING_NAME="${STAGING_NAME:-citemap-staging}"
STAGING_PORT="${STAGING_PORT:-8081}"
previous="$(docker inspect --format '{{.Config.Image}}' "${STAGING_NAME}" 2>/dev/null || true)"
log "Deploying ${IMAGE_NAME}:${IMAGE_TAG} to ${STAGING_NAME} (previous: ${previous:-none})"
docker rm -f "${STAGING_NAME}" >/dev/null 2>&1 || true
docker run -d --name "${STAGING_NAME}" \
  --restart unless-stopped \
  -p "${STAGING_PORT}:8000" \
  -v citemap-staging-data:/data \
  --label "ci.build-number=${BUILD_NUMBER}" \
  "${IMAGE_NAME}:${IMAGE_TAG}" >/dev/null
if ! bash ci/wait-and-check.sh "${STAGING_NAME}"; then
  echo "Deployment check failed" >&2
  if [[ -n "${previous}" ]]; then
    log "Rolling back to ${previous}"
    docker rm -f "${STAGING_NAME}" >/dev/null 2>&1 || true
    docker run -d --name "${STAGING_NAME}" --restart unless-stopped \
      -p "${STAGING_PORT}:8000" -v citemap-staging-data:/data "${previous}" >/dev/null
  fi
  exit 1
fi
log "Staging is running ${IMAGE_NAME}:${IMAGE_TAG} at http://localhost:${STAGING_PORT}"
