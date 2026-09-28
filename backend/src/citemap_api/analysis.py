"""Turn a fetched network into an analysed graph, and cut views out of it.

``enrich`` does the expensive work once per network: graph construction,
PageRank and summary statistics come from citemap-core, topic clusters from
:mod:`citemap_api.clustering`. The result is cached as one JSON document, so a
request only has to filter and slice it (``build_view``). This is adjustment A5
from Assignment 2: cache the assembled graph, not only the raw provider data.
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass
from typing import Any

from citemap import build_citation_graph, network_summary, rank_papers
from citemap.export import CSV_COLUMNS, to_graph_json

from citemap_api.clustering import cluster_papers
from citemap_api.domain import Network


@dataclass(frozen=True)
class ViewFilters:
    from_year: int | None = None
    to_year: int | None = None
    min_citations: int = 0
    clusters: frozenset[int] | None = None
    limit: int | None = 150


def enrich(network: Network) -> dict[str, Any]:
    """Analyse a network and return a JSON-serialisable document."""
    graph = build_citation_graph(network.papers)
    ranking = rank_papers(graph, top=None)
    texts = {p.id: f"{p.title}. {network.meta_for(p.id).abstract or ''}" for p in network.papers}
    clustering = cluster_papers(texts)
    by_id = {p.id: p for p in network.papers}

    nodes = []
    for position, item in enumerate(ranking, start=1):
        paper = by_id[item.id]
        meta = network.meta_for(item.id)
        nodes.append(
            {
                "id": item.id,
                "title": paper.title,
                "year": paper.year,
                "authors": list(paper.authors),
                "cited_by_count": paper.cited_by_count,
                "local_citations": item.local_citations,
                "references_in_network": int(graph.out_degree(item.id)),
                "pagerank": item.pagerank,
                "rank": position,
                "cluster": clustering.assignments.get(item.id, 0),
                "is_seed": item.id == network.seed_id,
                **asdict(meta),
            }
        )
    summary = network_summary(graph)
    return {
        "source": network.source,
        "seed_id": network.seed_id,
        "provenance": network.provenance,
        "nodes": nodes,
        "links": to_graph_json(graph)["links"],
        "clusters": [
            {"id": i, "label": label, "size": size}
            for i, (label, size) in enumerate(zip(clustering.labels, clustering.sizes, strict=True))
        ],
        "summary": asdict(summary),
    }


def build_view(enriched: dict[str, Any], filters: ViewFilters) -> dict[str, Any]:
    """Filter the analysed network and keep at most ``limit`` papers.

    The seed paper is always kept. Among the rest, papers with the highest
    PageRank are kept first, so the most influential part of a large network
    is shown before the periphery (adjustment A4 from Assignment 2).
    """

    def visible(node: dict[str, Any]) -> bool:
        if node["is_seed"]:
            return True
        year = node["year"]
        if filters.from_year is not None and (year is None or year < filters.from_year):
            return False
        if filters.to_year is not None and (year is None or year > filters.to_year):
            return False
        if node["cited_by_count"] < filters.min_citations:
            return False
        return filters.clusters is None or node["cluster"] in filters.clusters

    candidates = [n for n in enriched["nodes"] if visible(n)]  # already sorted by rank
    candidates.sort(key=lambda n: (not n["is_seed"], n["rank"]))
    kept = candidates if filters.limit is None else candidates[: filters.limit]
    kept_ids = {n["id"] for n in kept}
    links = [
        link
        for link in enriched["links"]
        if link["source"] in kept_ids and link["target"] in kept_ids
    ]
    return {
        "source": enriched["source"],
        "seed_id": enriched["seed_id"],
        "provenance": enriched["provenance"],
        "nodes": sorted(kept, key=lambda n: n["rank"]),
        "links": links,
        "clusters": enriched["clusters"],
        "summary": enriched["summary"],
        "total_nodes": len(enriched["nodes"]),
        "matching_nodes": len(candidates),
        "shown_nodes": len(kept),
    }


def view_to_csv(view: dict[str, Any]) -> str:
    """Ranking of the papers in a view, in the CSV layout of citemap-core."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([*CSV_COLUMNS, "cluster", "doi"])
    for node in view["nodes"]:
        writer.writerow(
            [
                node["rank"],
                node["id"],
                node["title"],
                "" if node["year"] is None else node["year"],
                f"{node['pagerank']:.6f}",
                node["local_citations"],
                node["cited_by_count"],
                node["cluster"],
                node.get("doi") or "",
            ]
        )
    return buffer.getvalue()
