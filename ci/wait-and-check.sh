#!/usr/bin/env bash
# wait-and-check.sh <container>: wait until the API answers inside the container,
# then run the functional smoke test there (no network setup needed).
source "$(dirname "$0")/lib.sh"
container="$1"
for attempt in $(seq 1 30); do
  if docker exec "${container}" python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)" \
      >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" == 30 ]]; then
    echo "API did not start in time" >&2
    docker logs "${container}" >&2 || true
    exit 1
  fi
  sleep 1
done
docker exec -i "${container}" python - < ci/smoke_test.py
