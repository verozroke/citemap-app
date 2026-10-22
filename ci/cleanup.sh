#!/usr/bin/env bash
# Post-build cleanup: remove the test images of this build and dangling layers.
source "$(dirname "$0")/lib.sh"
docker image rm "${IMAGE_NAME}-test:backend-${IMAGE_TAG}" "${IMAGE_NAME}-test:frontend-${IMAGE_TAG}" >/dev/null 2>&1 || true
docker image prune -f >/dev/null 2>&1 || true
