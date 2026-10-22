#!/usr/bin/env bash
# Stage "Push to Docker Hub" (optional): needs DOCKERHUB_USERNAME, DOCKERHUB_TOKEN
# and DOCKERHUB_REPO, e.g. verozroke/citemap-app.
source "$(dirname "$0")/lib.sh"
: "${DOCKERHUB_USERNAME:?set DOCKERHUB_USERNAME}"
: "${DOCKERHUB_TOKEN:?set DOCKERHUB_TOKEN}"
: "${DOCKERHUB_REPO:?set DOCKERHUB_REPO}"
log "Pushing ${DOCKERHUB_REPO}:${IMAGE_TAG} and :latest"
printf '%s' "${DOCKERHUB_TOKEN}" | docker login -u "${DOCKERHUB_USERNAME}" --password-stdin
trap 'docker logout >/dev/null 2>&1 || true' EXIT
for tag in "${IMAGE_TAG}" latest; do
  docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${DOCKERHUB_REPO}:${tag}"
  docker push "${DOCKERHUB_REPO}:${tag}"
done
