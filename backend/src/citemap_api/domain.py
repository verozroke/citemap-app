"""Domain objects shared by data sources, analysis and storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from citemap import Paper


@dataclass(frozen=True)
class PaperMeta:
    """Descriptive fields that citemap-core does not need for graph analysis."""

    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    venue: str | None = None


@dataclass(frozen=True)
class SearchHit:
    id: str
    title: str
    year: int | None
    authors: tuple[str, ...]
    cited_by_count: int


@dataclass
class Network:
    """Papers around a seed paper as delivered by a data source."""

    source: str
    seed_id: str
    papers: list[Paper]
    meta: dict[str, PaperMeta] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def meta_for(self, paper_id: str) -> PaperMeta:
        return self.meta.get(paper_id, PaperMeta())
