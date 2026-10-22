#!/usr/bin/env bash
# Stage "Build image": the runtime image, tagged with the build number and commit.
source "$(dirname "$0")/lib.sh"
log "Building ${IMAGE_NAME}:${IMAGE_TAG}"
docker build "${EXTRA_BUILD_OPTS[@]}" "${BUILD_ARGS[@]}" \
  --target runtime \
  --build-arg "VCS_REF=${GIT_COMMIT}" \
  --build-arg "BUILD_NUMBER=${BUILD_NUMBER}" \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" -t "${IMAGE_NAME}:latest" .
docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" \
  --format 'Image {{.Id}} size {{.Size}} bytes, revision {{index .Config.Labels "org.opencontainers.image.revision"}}'
