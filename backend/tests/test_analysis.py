from __future__ import annotations

import csv
import io
import json

import pytest

from citemap_api.analysis import ViewFilters, build_view, enrich, view_to_csv
from citemap_api.sources import DemoSource


@pytest.fixture(scope="module")
def enriched() -> dict[str, object]:
    return enrich(DemoSource().fetch("D042"))


def test_enrich_document_is_complete(enriched: dict) -> None:
    nodes = enriched["nodes"]
    assert json.loads(json.dumps(enriched)) == enriched
    assert [n["rank"] for n in nodes] == list(range(1, len(nodes) + 1))
    assert sum(n["is_seed"] for n in nodes) == 1
    assert enriched["summary"]["papers"] == len(nodes)
    assert sum(c["size"] for c in enriched["clusters"]) == len(nodes)
    assert {n["cluster"] for n in nodes} == {c["id"] for c in enriched["clusters"]}
    assert abs(sum(n["pagerank"] for n in nodes) - 1) < 1e-6


def test_view_without_filters_keeps_everything(enriched: dict) -> None:
    view = build_view(enriched, ViewFilters(limit=None))
    assert view["shown_nodes"] == view["total_nodes"] == len(enriched["nodes"])
    assert len(view["links"]) == len(enriched["links"])


def test_limit_keeps_seed_and_top_ranked(enriched: dict) -> None:
    view = build_view(enriched, ViewFilters(limit=5))
    ids = {n["id"] for n in view["nodes"]}
    top = {n["id"] for n in enriched["nodes"] if n["rank"] <= 4}
    assert view["shown_nodes"] == 5
    assert "D042" in ids
    assert top <= ids
    assert all(link["source"] in ids and link["target"] in ids for link in view["links"])


def test_filters_by_year_citations_and_cluster(enriched: dict) -> None:
    filters = ViewFilters(
        from_year=2005, to_year=2020, min_citations=50, clusters=frozenset({0}), limit=None
    )
    view = build_view(enriched, filters)
    for node in view["nodes"]:
        if node["is_seed"]:
            continue
        assert 2005 <= node["year"] <= 2020
        assert node["cited_by_count"] >= 50
        assert node["cluster"] == 0
    assert view["matching_nodes"] == view["shown_nodes"] < view["total_nodes"]


def test_seed_survives_any_filter(enriched: dict) -> None:
    view = build_view(enriched, ViewFilters(from_year=3000))
    assert [n["id"] for n in view["nodes"]] == ["D042"]


def test_papers_without_year_are_excluded_by_year_filters() -> None:
    node = {"id": "X", "year": None, "is_seed": False, "cited_by_count": 0, "cluster": 0, "rank": 1}
    doc = {
        "source": "t",
        "seed_id": "S",
        "provenance": {},
        "nodes": [node],
        "links": [],
        "clusters": [],
        "summary": {},
    }
    assert build_view(doc, ViewFilters(from_year=1))["shown_nodes"] == 0
    assert build_view(doc, ViewFilters(to_year=3000))["shown_nodes"] == 0
    assert build_view(doc, ViewFilters())["shown_nodes"] == 1


def test_csv_export(enriched: dict) -> None:
    view = build_view(enriched, ViewFilters(limit=3))
    rows = list(csv.DictReader(io.StringIO(view_to_csv(view))))
    assert len(rows) == 3
    assert rows[0]["rank"] == "1"
    assert set(rows[0]) >= {"id", "title", "pagerank", "cluster", "doi"}
