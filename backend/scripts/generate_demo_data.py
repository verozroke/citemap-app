"""Generate the synthetic demo network shipped with CiteMap.

The demo lets the application run without internet access. Everything in it
is fictional: titles, authors, venues and citation counts are generated from
fixed word lists with a seeded random generator, so the file is reproducible:
running this script again produces exactly the same output.

The generator builds a citation network with realistic structure:
- five research topics with their own vocabulary, so topic clustering has
  something real to find;
- papers mostly cite earlier papers of their own topic, sometimes other topics;
- preferential attachment: papers that are already cited are more likely to be
  cited again, which produces a few highly influential "foundational" papers.

Usage:  python scripts/generate_demo_data.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 42
PAPERS_PER_TOPIC = 20
OUT = Path(__file__).resolve().parents[1] / "src" / "citemap_api" / "data" / "demo_network.json"

TOPICS = {
    "bibliometrics": {
        "heads": [
            "Citation Analysis",
            "Bibliometric Indicators",
            "Research Impact",
            "Co-citation Patterns",
            "Scholarly Influence",
            "Citation Counts",
            "Journal Impact",
            "Author Productivity",
        ],
        "objects": [
            "Scientific Journals",
            "Research Evaluation",
            "Academic Fields",
            "Funding Decisions",
            "Interdisciplinary Research",
            "Early Career Researchers",
            "University Rankings",
        ],
        "sentences": [
            "We analyse citation counts and bibliometric indicators across {obj}.",
            "The study measures research impact with co-citation and h-index based indicators.",
            "Our results show that citation distributions are highly skewed and field dependent.",
            (
                "We propose a normalised impact indicator that"
                " corrects for field size and publication age."
            ),
            "Bibliometric evidence suggests that scholarly influence concentrates in few journals.",
        ],
    },
    "embeddings": {
        "heads": [
            "Semantic Embeddings",
            "Transformer Representations",
            "Language Models",
            "Document Embeddings",
            "Contrastive Learning",
            "Sentence Representations",
            "Topic Modelling",
            "Neural Text Encoders",
        ],
        "objects": [
            "Scientific Abstracts",
            "Paper Similarity",
            "Literature Search",
            "Citation Recommendation",
            "Research Topics",
            "Full Text Articles",
            "Multilingual Papers",
        ],
        "sentences": [
            "We train transformer language models to embed {obj} into a semantic vector space.",
            (
                "Contrastive learning on citation pairs improves"
                " document embeddings for similarity search."
            ),
            "The embeddings capture topical similarity better than bag of words representations.",
            (
                "We evaluate sentence representations on paper"
                " recommendation and topic classification."
            ),
            "Pretrained neural encoders reduce the annotation effort for scientific text tasks.",
        ],
    },
    "visualization": {
        "heads": [
            "Interactive Visualization",
            "Graph Layout",
            "Visual Exploration",
            "Force-Directed Layouts",
            "Network Rendering",
            "Visual Analytics",
            "Literature Maps",
            "Zoomable Interfaces",
        ],
        "objects": [
            "Citation Networks",
            "Large Graphs",
            "Science Maps",
            "Research Landscapes",
            "Literature Reviews",
            "Knowledge Domains",
            "Web Browsers",
        ],
        "sentences": [
            "We present an interactive visualization system for exploring {obj}.",
            "Force-directed graph layout algorithms are adapted to render thousands of nodes.",
            "A user study shows that visual exploration speeds up literature review tasks.",
            "The interface combines zoomable maps, filtering and linked detail views.",
            "Visual analytics helps researchers identify clusters and bridges between fields.",
        ],
    },
    "reproducibility": {
        "heads": [
            "Reproducible Workflows",
            "Open Science",
            "Research Software",
            "Data Provenance",
            "Computational Reproducibility",
            "FAIR Data",
            "Software Citation",
            "Open Peer Review",
        ],
        "objects": [
            "Bibliometric Studies",
            "Machine Learning Experiments",
            "Scientific Pipelines",
            "Shared Datasets",
            "Research Code",
            "Laboratory Notebooks",
            "Digital Libraries",
        ],
        "sentences": [
            "We examine the reproducibility of {obj} and the availability of code and data.",
            "Open science practices such as data sharing and preregistration are becoming common.",
            "Provenance tracking and versioned workflows make computational results verifiable.",
            "We propose guidelines for citing research software and archiving releases with a DOI.",
            "FAIR principles improve the findability and reuse of research data and software.",
        ],
    },
    "networks": {
        "heads": [
            "Community Detection",
            "Network Clustering",
            "Modularity Optimization",
            "Graph Centrality",
            "Link Prediction",
            "Network Topology",
            "Random Walk Methods",
            "Scale-Free Networks",
        ],
        "objects": [
            "Citation Graphs",
            "Collaboration Networks",
            "Directed Networks",
            "Temporal Networks",
            "Bibliographic Coupling",
            "Heterogeneous Graphs",
            "Scientific Communities",
        ],
        "sentences": [
            "We detect communities in {obj} using modularity optimization and random walks.",
            "Centrality measures such as PageRank identify structurally important nodes.",
            "The network topology follows a heavy tailed degree distribution.",
            "Link prediction methods anticipate future citations from the current graph structure.",
            "Our clustering algorithm scales to networks with millions of edges.",
        ],
    },
}

TEMPLATES = [
    "{head} for {obj}",
    "{head} in {obj}",
    "Rethinking {head} for {obj}",
    "{head}: Evidence from {obj}",
    "Scalable {head} of {obj}",
    "Towards {head} in {obj}",
]

GIVEN = [
    "Aigerim",
    "Daniyar",
    "Laura",
    "Kenji",
    "Sofia",
    "Omar",
    "Priya",
    "Lukas",
    "Mei",
    "Tomás",
    "Amara",
    "Ivan",
    "Chloé",
    "Arman",
    "Yuki",
    "Fatima",
    "Noah",
    "Elif",
    "Mateo",
    "Zhanna",
]
FAMILY = [
    "Moreau",
    "Tanaka",
    "Oyelaran",
    "Lindqvist",
    "Bekova",
    "Carvalho",
    "Park",
    "Esenova",
    "Novak",
    "Haddad",
    "Kowalski",
    "Singh",
    "Okafor",
    "Nurlanov",
    "Rossi",
    "Kim",
    "Silva",
    "Fischer",
    "Abenova",
    "Duarte",
]
VENUES = [
    "Journal of Informetrics (fictional)",
    "Scientometric Letters (fictional)",
    "Proceedings of the Demo Conference on Digital Libraries",
    "Computational Linguistics Demo",
    "Visual Computing Review (fictional)",
    "Open Research Practice (fictional)",
    "Network Science Demo Journal",
]


def main() -> None:
    rng = random.Random(SEED)
    papers: list[dict[str, object]] = []
    used_titles: set[str] = set()
    topic_names = list(TOPICS)

    # 1. Create papers: each topic gets papers spread over 1996-2025.
    for topic in topic_names:
        spec = TOPICS[topic]
        for _ in range(PAPERS_PER_TOPIC):
            while True:
                title = rng.choice(TEMPLATES).format(
                    head=rng.choice(spec["heads"]), obj=rng.choice(spec["objects"])
                )
                if title not in used_titles:
                    used_titles.add(title)
                    break
            obj = rng.choice(spec["objects"]).lower()
            sentences = rng.sample(spec["sentences"], 3)
            abstract = " ".join(s.format(obj=obj) for s in sentences)
            papers.append(
                {
                    "topic": topic,
                    "title": title,
                    "year": rng.randint(1996, 2025),
                    "authors": [
                        f"{rng.choice(GIVEN)} {rng.choice(FAMILY)}"
                        for _ in range(rng.randint(1, 4))
                    ],
                    "venue": rng.choice(VENUES),
                    "abstract": abstract,
                }
            )

    # 2. Order by year and assign ids D001.. in chronological order.
    papers.sort(key=lambda p: (p["year"], p["title"]))
    for i, p in enumerate(papers, start=1):
        p["id"] = f"D{i:03d}"

    # 3. References with preferential attachment, mostly within the same topic.
    in_degree = {p["id"]: 0 for p in papers}
    for i, p in enumerate(papers):
        earlier = [q for q in papers[:i] if q["year"] < p["year"]]
        if not earlier:
            p["references"] = []
            continue
        wanted = min(len(earlier), rng.randint(3, 7))
        refs: set[str] = set()
        attempts = 0
        while len(refs) < wanted and attempts < 200:
            attempts += 1
            same_topic = rng.random() < 0.8
            pool = [q for q in earlier if (q["topic"] == p["topic"]) == same_topic] or earlier
            weights = [1 + 2 * in_degree[q["id"]] for q in pool]
            refs.add(rng.choices(pool, weights=weights, k=1)[0]["id"])  # type: ignore[arg-type]
        p["references"] = sorted(refs)
        for r in refs:
            in_degree[r] += 1

    # 4. Global citation counts: in-network citations scaled up, older papers accumulate more.
    for p in papers:
        age = 2026 - int(p["year"])  # type: ignore[arg-type]
        base = in_degree[p["id"]] * rng.randint(18, 40) + age * rng.randint(2, 9)
        p["cited_by_count"] = int(base * rng.uniform(0.8, 1.3))

    out = {
        "meta": {
            "source": "demo",
            "synthetic": True,
            "description": (
                "Synthetic citation network for offline demonstrations of CiteMap. "
                "Titles, authors, venues and counts are generated "
                "and do not describe real publications."
            ),
            "generator": "backend/scripts/generate_demo_data.py",
            "seed": SEED,
            "license": "CC0-1.0",
        },
        "papers": [
            {
                k: p[k]
                for k in (
                    "id",
                    "title",
                    "year",
                    "authors",
                    "cited_by_count",
                    "references",
                    "venue",
                    "abstract",
                )
            }
            for p in papers
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    edges = sum(len(p["references"]) for p in papers)  # type: ignore[arg-type]
    print(f"wrote {len(papers)} papers and {edges} citations to {OUT}")


if __name__ == "__main__":
    main()
