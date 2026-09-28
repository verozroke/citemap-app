from __future__ import annotations

import pytest
from citemap.providers import ProviderError

from citemap_api.sources import (
    DemoSource,
    InvalidInputError,
    NotFoundError,
    OpenAlexSource,
    UpstreamError,
    reconstruct_abstract,
)
from tests.conftest import FakeOpenAlex


class TestDemoSource:
    def test_bundled_dataset_is_labelled_synthetic(self, demo: DemoSource) -> None:
        network = demo.fetch("D042")
        assert network.provenance["synthetic"] is True
        assert len(demo.papers) == 100

    def test_search_ranks_title_matches_first(self, demo: DemoSource) -> None:
        hits = demo.search("embedding")
        assert hits
        assert all("embedding" in h.title.lower() for h in hits[:3])

    def test_search_by_id_is_case_insensitive(self, demo: DemoSource) -> None:
        assert [h.id for h in demo.search("d007")] == ["D007"]

    def test_empty_search_returns_most_cited(self, demo: DemoSource) -> None:
        hits = demo.search("", limit=5)
        counts = [h.cited_by_count for h in hits]
        assert len(hits) == 5
        assert counts == sorted(counts, reverse=True)

    def test_search_without_matches_is_empty(self, demo: DemoSource) -> None:
        assert demo.search("zzzz qqqq") == []

    def test_fetch_returns_neighbourhood_with_meta(self, demo: DemoSource) -> None:
        network = demo.fetch(" d042 ")
        ids = {p.id for p in network.papers}
        assert network.seed_id == "D042"
        assert "D042" in ids
        assert 1 < len(ids) < 100
        assert network.meta_for("D042").abstract

    @pytest.mark.parametrize("bad", ["", "42", "W123", "D1"])
    def test_malformed_id_is_invalid(self, demo: DemoSource, bad: str) -> None:
        with pytest.raises(InvalidInputError):
            demo.fetch(bad)

    def test_unknown_id_is_not_found(self, demo: DemoSource) -> None:
        with pytest.raises(NotFoundError):
            demo.fetch("D999")

    def test_custom_dataset(self) -> None:
        raw = {
            "papers": [
                {"id": "D001", "title": "A", "year": 2000, "references": []},
                {"id": "D002", "title": "B", "year": 2001, "references": ["D001"]},
                {"id": "D003", "title": "C", "year": 2002, "references": []},
            ]
        }
        network = DemoSource(raw, radius=1).fetch("D001")
        assert {p.id for p in network.papers} == {"D001", "D002"}


def test_reconstruct_abstract() -> None:
    assert reconstruct_abstract({"world": [1], "hello": [0], "again": [2]}) == "hello world again"
    assert reconstruct_abstract(None) is None
    assert reconstruct_abstract({}) is None


class TestOpenAlexSource:
    def test_search_by_text(self, fake_openalex: FakeOpenAlex) -> None:
        hits = OpenAlexSource(http_get=fake_openalex).search("community", limit=5)
        assert [h.id for h in hits] == ["W2"]
        assert "search=community" in fake_openalex.urls[0]
        assert "per_page=5" in fake_openalex.urls[0]

    def test_search_by_work_id_and_url(self, fake_openalex: FakeOpenAlex) -> None:
        source = OpenAlexSource(http_get=fake_openalex)
        assert [h.id for h in source.search("w3")] == ["W3"]
        assert [h.id for h in source.search("https://openalex.org/W4")] == ["W4"]

    def test_search_by_doi(self, fake_openalex: FakeOpenAlex) -> None:
        hits = OpenAlexSource(http_get=fake_openalex).search("https://doi.org/10.1234/gnn")
        assert [h.id for h in hits] == ["W1"]

    def test_search_unknown_id_or_empty(self, fake_openalex: FakeOpenAlex) -> None:
        source = OpenAlexSource(http_get=fake_openalex)
        assert source.search("W999") == []
        assert source.search("   ") == []

    def test_provider_errors_become_upstream_errors(self) -> None:
        def broken(url: str) -> dict[str, object]:
            raise ProviderError("boom")

        source = OpenAlexSource(http_get=broken)
        with pytest.raises(UpstreamError):
            source.search("anything")
        with pytest.raises(UpstreamError):
            source.fetch("W1")

    def test_credentials_are_added_to_urls(self, fake_openalex: FakeOpenAlex) -> None:
        OpenAlexSource(api_key="k", mailto="me@example.org", http_get=fake_openalex).search("x")
        assert "api_key=k" in fake_openalex.urls[0]
        assert "mailto=me%40example.org" in fake_openalex.urls[0]

    def test_fetch_builds_network_with_meta(self, fake_openalex: FakeOpenAlex) -> None:
        network = OpenAlexSource(max_citing=10, http_get=fake_openalex).fetch(
            "https://openalex.org/W1"
        )
        assert network.seed_id == "W1"
        assert {p.id for p in network.papers} == {"W1", "W2", "W3", "W4", "W5"}
        seed = network.meta_for("W1")
        assert seed.abstract == "graph neural networks learn citation structure"
        assert seed.doi == seed.url == "https://doi.org/10.1234/gnn"
        assert seed.venue == "Journal of Tests"
        assert network.meta_for("W2").url == "https://openalex.org/W2"
        assert network.provenance["max_citing"] == 10

    def test_fetch_rejects_malformed_id(self, fake_openalex: FakeOpenAlex) -> None:
        with pytest.raises(InvalidInputError):
            OpenAlexSource(http_get=fake_openalex).fetch("not-an-id")

    def test_fetch_unknown_work(self, fake_openalex: FakeOpenAlex) -> None:
        with pytest.raises(NotFoundError):
            OpenAlexSource(http_get=fake_openalex).fetch("W999")
