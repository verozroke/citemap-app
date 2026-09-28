"""Request and response models of the HTTP API.

They are the public contract with the frontend and appear in the generated
OpenAPI documentation at ``/docs``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "running", "done", "failed"]


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class SourceOut(BaseModel):
    name: str
    label: str
    example: str = Field(description="An identifier or query that works with this source")


class SearchHitOut(BaseModel):
    id: str
    title: str
    year: int | None
    authors: list[str]
    cited_by_count: int


class GraphRequest(BaseModel):
    source: str = Field(examples=["demo"])
    seed_id: str = Field(min_length=1, max_length=200, examples=["D042"])
    refresh: bool = Field(default=False, description="Ignore the cache and fetch again")


class ViewParams(BaseModel):
    """Filters applied to a cached graph before it is returned or exported."""

    from_year: int | None = Field(default=None, ge=0, le=3000)
    to_year: int | None = Field(default=None, ge=0, le=3000)
    min_citations: int = Field(default=0, ge=0, description="Minimum global citation count")
    clusters: str | None = Field(default=None, description="Comma-separated cluster ids")
    limit: int = Field(default=150, ge=1, le=2000, description="Maximum number of papers")


class JobOut(BaseModel):
    id: str
    source: str
    seed_id: str
    status: JobStatus
    error: str | None
    cached: bool
    created_at: str
    updated_at: str


class NodeOut(BaseModel):
    id: str
    title: str
    year: int | None
    authors: list[str]
    cited_by_count: int
    local_citations: int
    references_in_network: int
    pagerank: float
    rank: int
    cluster: int
    is_seed: bool
    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    venue: str | None = None


class LinkOut(BaseModel):
    source: str
    target: str


class ClusterOut(BaseModel):
    id: int
    label: str
    size: int


class GraphView(BaseModel):
    source: str
    seed_id: str
    provenance: dict[str, Any]
    fetched_at: str
    nodes: list[NodeOut]
    links: list[LinkOut]
    clusters: list[ClusterOut]
    summary: dict[str, Any]
    total_nodes: int
    matching_nodes: int
    shown_nodes: int


class ErrorOut(BaseModel):
    detail: str
