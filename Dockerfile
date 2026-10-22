# CiteMap container image.
#
# Targets (docker build --target <name>):
#   frontend-test  runs the frontend linter, type check and unit tests
#   backend-test   runs the backend linter, type check and unit tests
#   runtime        the application image (default, last stage)
#
# The base images can be overridden with build arguments, for example to use a
# mirror: docker build --build-arg PYTHON_IMAGE=mirror.example/python:3.12-slim .
ARG PYTHON_IMAGE=python:3.12-slim
ARG NODE_IMAGE=node:22-alpine

# ---------------------------------------------------------------- frontend
FROM ${NODE_IMAGE} AS frontend-deps
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./

FROM frontend-deps AS frontend-test
RUN mkdir -p /reports
CMD ["sh", "-c", "npm run lint && npm run typecheck && npx vitest run --reporter=default --reporter=junit --outputFile.junit=/reports/frontend-junit.xml"]

FROM frontend-deps AS frontend
RUN npm run build

# ---------------------------------------------------------------- backend
# Wheels for the backend and all dependencies (git is needed for citemap-core).
FROM ${PYTHON_IMAGE} AS wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY backend/ backend/
RUN pip wheel --no-cache-dir --wheel-dir /wheels ./backend

FROM wheels AS backend-test
WORKDIR /src/backend
RUN pip install --no-cache-dir -e ".[dev]" && mkdir -p /reports
CMD ["sh", "-c", "ruff check . && ruff format --check . && mypy && pytest --cov --cov-report=term --cov-report=xml:/reports/backend-coverage.xml --junitxml=/reports/backend-junit.xml"]

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE} AS runtime
ARG VCS_REF=unknown
ARG BUILD_NUMBER=local
LABEL org.opencontainers.image.title="CiteMap" \
      org.opencontainers.image.source="https://github.com/verozroke/citemap-app" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision="${VCS_REF}" \
      ci.build-number="${BUILD_NUMBER}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CITEMAP_DATA_DIR=/data \
    CITEMAP_STATIC_DIR=/app/static \
    CITEMAP_HOST=0.0.0.0 \
    CITEMAP_PORT=8000
COPY --from=wheels /wheels /wheels
# /wheels already holds every dependency; --no-deps stops pip from trying to
# fetch the git reference to citemap-core again.
RUN pip install --no-cache-dir --no-index --no-deps /wheels/*.whl && pip check && rm -rf /wheels
COPY --from=frontend /src/frontend/dist /app/static
RUN useradd --create-home --uid 1000 citemap && mkdir /data && chown citemap /data
USER citemap
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["citemap-api"]
