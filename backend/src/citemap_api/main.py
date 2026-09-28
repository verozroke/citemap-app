"""FastAPI application: HTTP routes, error mapping and the static frontend.

Start it with ``citemap-api`` (see :func:`run`) or
``uvicorn citemap_api.main:create_app --factory``.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from citemap_api import __version__
from citemap_api.analysis import ViewFilters, build_view, view_to_csv
from citemap_api.config import Settings
from citemap_api.jobs import JobRunner, UnknownSourceError
from citemap_api.repository import Repository
from citemap_api.schemas import (
    ErrorOut,
    GraphRequest,
    GraphView,
    Health,
    JobOut,
    SearchHitOut,
    SourceOut,
    ViewParams,
)
from citemap_api.sources import (
    DataSource,
    DemoSource,
    InvalidInputError,
    NotFoundError,
    OpenAlexSource,
    UpstreamError,
)

log = logging.getLogger(__name__)

Filters = Annotated[ViewParams, Query()]
EXAMPLES = {"demo": "D042", "openalex": "W2741809807"}
ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorOut},
    404: {"model": ErrorOut},
    502: {"model": ErrorOut},
}


def default_sources(settings: Settings) -> dict[str, DataSource]:
    return {
        "demo": DemoSource(),
        "openalex": OpenAlexSource(
            api_key=settings.openalex_api_key,
            mailto=settings.openalex_mailto,
            max_citing=settings.max_citing,
        ),
    }


def parse_clusters(raw: str | None) -> frozenset[int] | None:
    """``"0,2"`` to ``{0, 2}``; empty or missing means all clusters."""
    if raw is None or not raw.strip():
        return None
    try:
        return frozenset(int(part) for part in raw.split(",") if part.strip())
    except ValueError as exc:
        raise InvalidInputError(f"clusters must be comma-separated integers, got {raw!r}") from exc


def create_app(
    settings: Settings | None = None, sources: Mapping[str, DataSource] | None = None
) -> FastAPI:
    """Build the application. Tests pass their own settings and fake sources."""
    settings = settings or Settings.from_env()
    sources = dict(sources) if sources is not None else default_sources(settings)
    repository = Repository(settings.database_path)
    runner = JobRunner(
        repository, sources, settings.cache_ttl_hours, inline=settings.run_jobs_inline
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        interrupted = repository.fail_interrupted_jobs()
        if interrupted:
            log.warning("marked %d interrupted job(s) as failed", interrupted)
        yield
        runner.shutdown()

    app = FastAPI(
        title="CiteMap API",
        version=__version__,
        description="Build, analyse and export citation networks around a seed paper.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.repository = repository
    app.state.runner = runner
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # -- error mapping -----------------------------------------------------
    def _error(code: int) -> Any:
        async def handler(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse({"detail": str(exc)}, status_code=code)

        return handler

    app.add_exception_handler(InvalidInputError, _error(status.HTTP_400_BAD_REQUEST))
    app.add_exception_handler(NotFoundError, _error(status.HTTP_404_NOT_FOUND))
    app.add_exception_handler(UnknownSourceError, _error(status.HTTP_404_NOT_FOUND))
    app.add_exception_handler(UpstreamError, _error(status.HTTP_502_BAD_GATEWAY))

    def source_or_404(name: str) -> DataSource:
        if name not in sources:
            raise UnknownSourceError(f"Unknown data source: {name!r}")
        return sources[name]

    def load_view(source: str, seed_id: str, filters: ViewFilters) -> dict[str, Any]:
        canonical = source_or_404(source).normalise(seed_id)
        stored = repository.get_network(source, canonical)
        if stored is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"No graph for {canonical} yet. Start one with POST /api/graphs.",
            )
        view = build_view(stored.document, filters)
        view["fetched_at"] = stored.fetched_at.isoformat()
        return view

    def to_filters(params: ViewParams) -> ViewFilters:
        return ViewFilters(
            params.from_year,
            params.to_year,
            params.min_citations,
            parse_clusters(params.clusters),
            params.limit,
        )

    # -- routes --------------------------------------------------------------
    @app.get("/api/health", response_model=Health, tags=["meta"])
    def health() -> Health:
        return Health(version=__version__)

    @app.get("/api/sources", response_model=list[SourceOut], tags=["meta"])
    def list_sources() -> list[SourceOut]:
        return [
            SourceOut(name=name, label=src.label, example=EXAMPLES.get(name, ""))
            for name, src in sources.items()
        ]

    @app.get("/api/search", response_model=list[SearchHitOut], responses=ERRORS, tags=["papers"])
    def search(
        q: Annotated[str, Query(max_length=300, description="Title words, DOI or id")] = "",
        source: str = "demo",
        limit: Annotated[int, Query(ge=1, le=25)] = 10,
    ) -> list[SearchHitOut]:
        hits = source_or_404(source).search(q, limit)
        return [SearchHitOut(**{**asdict(h), "authors": list(h.authors)}) for h in hits]

    @app.post(
        "/api/graphs",
        response_model=JobOut,
        status_code=status.HTTP_202_ACCEPTED,
        responses=ERRORS,
        tags=["graphs"],
    )
    def start_graph(request: GraphRequest) -> JobOut:
        job = runner.submit(request.source, request.seed_id, refresh=request.refresh)
        return JobOut(**asdict(job))

    @app.get("/api/jobs/{job_id}", response_model=JobOut, responses=ERRORS, tags=["graphs"])
    def get_job(job_id: str) -> JobOut:
        job = repository.get_job(job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown job: {job_id}")
        return JobOut(**asdict(job))

    @app.get(
        "/api/graphs/{source}/{seed_id}",
        response_model=GraphView,
        responses=ERRORS,
        tags=["graphs"],
    )
    def get_graph(source: str, seed_id: str, params: Filters) -> dict[str, Any]:
        return load_view(source, seed_id, to_filters(params))

    @app.get(
        "/api/graphs/{source}/{seed_id}/export.csv",
        responses=ERRORS,
        tags=["export"],
        response_class=Response,
    )
    def export_csv(source: str, seed_id: str, params: Filters) -> Response:
        view = load_view(source, seed_id, to_filters(params))
        return _download(view_to_csv(view), "text/csv", f"citemap-{view['seed_id']}.csv")

    @app.get(
        "/api/graphs/{source}/{seed_id}/export.json",
        responses=ERRORS,
        tags=["export"],
        response_class=Response,
    )
    def export_json(source: str, seed_id: str, params: Filters) -> Response:
        view = load_view(source, seed_id, to_filters(params))
        body = json.dumps(view, ensure_ascii=False, indent=2)
        return _download(body, "application/json", f"citemap-{view['seed_id']}.json")

    # -- frontend --------------------------------------------------------------
    if settings.static_dir is not None and settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="frontend")

    return app


def _download(body: str, media_type: str, filename: str) -> Response:
    return Response(
        body,
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def run() -> None:  # pragma: no cover - thin wrapper around uvicorn
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "citemap_api.main:create_app",
        factory=True,
        host=os.environ.get("CITEMAP_HOST", "127.0.0.1"),
        port=int(os.environ.get("CITEMAP_PORT", "8000")),
    )
