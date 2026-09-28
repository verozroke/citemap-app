# 1. Build the React frontend into static files.
FROM node:22-alpine AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. Build wheels for the backend and its dependencies (git is needed for citemap-core).
FROM python:3.12-slim AS wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY backend/ backend/
RUN pip wheel --no-cache-dir --wheel-dir /wheels ./backend

# 3. Small runtime image: Python, the installed wheels and the built frontend.
FROM python:3.12-slim
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
