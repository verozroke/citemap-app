"""Topic clustering of papers.

Papers are represented by TF-IDF vectors of their title and abstract and
grouped with k-means. This is deliberately lightweight: it installs in seconds
and runs on any laptop. The public function has a narrow interface, so the
vectoriser can later be replaced by sentence embeddings without touching the
rest of the application (the ports-and-adapters idea from Assignment 2).
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

# Words that appear in almost every scholarly text and would dominate labels.
_DOMAIN_STOP_WORDS = {
    "study",
    "paper",
    "results",
    "result",
    "approach",
    "method",
    "methods",
    "propose",
    "proposed",
    "based",
    "using",
    "use",
    "new",
    "show",
    "shows",
    "analysis",
    "towards",
    "evidence",
    "rethinking",
    "scalable",
    "research",
    "fictional",
    "demo",
}
STOP_WORDS = sorted(ENGLISH_STOP_WORDS | _DOMAIN_STOP_WORDS)


@dataclass(frozen=True)
class Clustering:
    """Cluster id per paper (0 is the largest cluster) and a label per cluster."""

    assignments: dict[str, int]
    labels: list[str]
    sizes: list[int]


def choose_k(n: int) -> int:
    """Number of clusters: about sqrt(n / 3), between 2 and 8."""
    if n < 4:
        return 1
    return max(2, min(8, round(math.sqrt(n / 3)), n - 1))


def cluster_papers(
    texts: Mapping[str, str], k: int | None = None, random_state: int = 42
) -> Clustering:
    """Group papers by topic.

    Args:
        texts: Paper id to the text describing it (title and abstract).
        k: Number of clusters, or ``None`` to choose it from the network size.
        random_state: Seed for k-means, so results are reproducible.
    """
    ids = sorted(texts)
    k = choose_k(len(ids)) if k is None else k
    if k <= 1 or len(ids) < 2:
        return Clustering(
            {pid: 0 for pid in ids}, ["all papers"] if ids else [], [len(ids)] if ids else []
        )

    vectorizer = TfidfVectorizer(
        stop_words=STOP_WORDS, ngram_range=(1, 2), min_df=1, max_features=3000, sublinear_tf=True
    )
    try:
        matrix = vectorizer.fit_transform([texts[i] for i in ids])
    except ValueError:  # every text was empty or only stop words
        return Clustering({pid: 0 for pid in ids}, ["all papers"], [len(ids)])

    k = min(k, matrix.shape[0])
    model = KMeans(n_clusters=k, n_init=10, random_state=random_state)
    raw = model.fit_predict(matrix)

    # Renumber clusters by size so that colours stay stable: 0 is the largest.
    order = [c for c, _ in Counter(raw.tolist()).most_common()]
    remap = {old: new for new, old in enumerate(order)}
    terms = np.array(vectorizer.get_feature_names_out())
    labels: list[str] = []
    for old in order:
        top = np.argsort(model.cluster_centers_[old])[::-1]
        words: list[str] = []
        used: set[str] = set()
        for idx in top:
            term = str(terms[idx])
            parts = set(term.split())
            if parts & used:  # "graph layout" after "graph" adds nothing new
                continue
            words.append(term)
            used |= parts
            if len(words) == 3:
                break
        labels.append(", ".join(words))
    assignments = {pid: remap[int(c)] for pid, c in zip(ids, raw, strict=True)}
    counts = Counter(assignments.values())
    return Clustering(assignments, labels, [counts[c] for c in range(len(order))])
