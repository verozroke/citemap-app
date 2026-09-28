"""Shared fixtures. No test touches the network: OpenAlex is replaced by a fake."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import pytest
from fastapi.testclient import TestClient

from citemap_api.config import Settings
from citemap_api.sources import DemoSource, NotFoundError, OpenAlexSource


def work(
    wid: str,
    title: str,
    year: int,
    refs: list[str] | None = None,
    cited_by: int = 0,
    abstract: str | None = None,
    doi: str | None = None,
) -> dict[str, Any]:
    """A minimal OpenAlex Work record."""
    inverted: dict[str, list[int]] = {}
    for position, word in enumerate((abstract or "").split()):
        inverted.setdefault(word, []).append(position)
    return {
        "id": f"https://openalex.org/{wid}",
        "display_name": title,
        "publication_year": year,
        "cited_by_count": cited_by,
        "doi": doi,
        "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
        "referenced_works": [f"https://openalex.org/{r}" for r in refs or []],
        "abstract_inverted_index": inverted or None,
        "primary_location": {"source": {"display_name": "Journal of Tests"}},
    }


class FakeOpenAlex:
    """Answers the handful of OpenAlex URLs CiteMap uses from an in-memory list."""

    def __init__(self, works: list[dict[str, Any]]) -> None:
        self.works = {w["id"].rsplit("/", 1)[-1]: w for w in works}
        self.urls: list[str] = []

    def __call__(self, url: str) -> Mapping[str, Any]:
        self.urls.append(url)
        parts = urlsplit(url)
        path = unquote(parts.path)
        query = {k: v[0] for k, v in parse_qs(parts.query).items()}
        if path.startswith("/works/doi:"):
            doi = path.removeprefix("/works/doi:")
            for w in self.works.values():
                if w["doi"] and w["doi"].endswith(doi):
                    return w
            raise NotFoundError("no such DOI")
        if path.startswith("/works/"):
            wid = path.removeprefix("/works/")
            if wid not in self.works:
                raise NotFoundError("no such work")
            return self.works[wid]
        results = list(self.works.values())
        flt = query.get("filter", "")
        if flt.startswith("openalex:"):
            wanted = flt.removeprefix("openalex:").split("|")
            results = [self.works[w] for w in wanted if w in self.works]
        elif flt.startswith("cites:"):
            target = "https://openalex.org/" + flt.removeprefix("cites:")
            results = [w for w in results if target in w["referenced_works"]]
        elif "search" in query:
            words = query["search"].lower().split()
            results = [w for w in results if any(x in w["display_name"].lower() for x in words)]
        return {"results": results[: int(query.get("per_page", 25))]}


@pytest.fixture
def fake_openalex() -> FakeOpenAlex:
    return FakeOpenAlex(
        [
            work(
                "W1",
                "Graph neural networks for citation analysis",
                2020,
                ["W2", "W3"],
                120,
                "graph neural networks learn citation structure",
                "https://doi.org/10.1234/gnn",
            ),
            work(
                "W2",
                "Community detection in graphs",
                2010,
                [],
                900,
                "modularity based community detection in large graphs",
            ),
            work(
                "W3",
                "Semantic embeddings of scientific text",
                2018,
                ["W2"],
                300,
                "semantic embeddings capture topical similarity of papers",
            ),
            work(
                "W4",
                "Citation recommendation with graph networks",
                2022,
                ["W1", "W3"],
                15,
                "we recommend citations using graph neural networks",
            ),
            work("W5", "Survey of citation network visualisation", 2023, ["W1", "W2"], 4),
        ]
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", run_jobs_inline=True)


@pytest.fixture
def demo() -> DemoSource:
    return DemoSource()


@pytest.fixture
def client(
    settings: Settings, demo: DemoSource, fake_openalex: FakeOpenAlex
) -> Iterator[TestClient]:
    from citemap_api.main import create_app

    sources = {"demo": demo, "openalex": OpenAlexSource(http_get=fake_openalex)}
    with TestClient(create_app(settings, sources)) as test_client:
        yield test_client
