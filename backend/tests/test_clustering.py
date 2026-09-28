from __future__ import annotations

import pytest

from citemap_api.clustering import choose_k, cluster_papers

TOPICS = {
    "graph": "community detection modularity graph clustering networks",
    "text": "semantic embeddings transformer language models text similarity",
    "open": "reproducible research software open data provenance workflows",
}


def corpus(per_topic: int = 6) -> dict[str, str]:
    return {
        f"{topic}{i}": f"{words} variant{i}"
        for topic, words in TOPICS.items()
        for i in range(per_topic)
    }


@pytest.mark.parametrize(("n", "k"), [(0, 1), (3, 1), (4, 2), (27, 3), (50, 4), (150, 7), (999, 8)])
def test_choose_k(n: int, k: int) -> None:
    assert choose_k(n) == k


def test_separates_topics_and_labels_them() -> None:
    result = cluster_papers(corpus(), k=3)
    for topic in TOPICS:
        assert len({result.assignments[f"{topic}{i}"] for i in range(6)}) == 1
    assert sorted(result.sizes) == [6, 6, 6]
    assert len(result.labels) == 3
    for label in result.labels:
        words = [w for term in label.split(", ") for w in term.split()]
        assert len(words) == len(set(words)), label


def test_is_reproducible() -> None:
    assert cluster_papers(corpus()) == cluster_papers(corpus())


def test_clusters_are_numbered_by_size() -> None:
    texts = corpus()
    texts.update({f"extra{i}": TOPICS["text"] + f" more{i}" for i in range(4)})
    result = cluster_papers(texts, k=3)
    assert result.sizes == sorted(result.sizes, reverse=True)
    assert "embeddings" in result.labels[0] or "semantic" in result.labels[0]


def test_tiny_or_empty_inputs_form_one_cluster() -> None:
    assert cluster_papers({}).labels == []
    single = cluster_papers({"a": "graph"})
    assert single.assignments == {"a": 0}
    stop_words_only = cluster_papers({str(i): "the and of" for i in range(10)})
    assert set(stop_words_only.assignments.values()) == {0}
    assert stop_words_only.labels == ["all papers"]
