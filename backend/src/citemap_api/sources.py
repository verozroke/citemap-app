"""Data sources: where CiteMap gets papers from.

``DataSource`` is the port. Two adapters implement it:

* :class:`DemoSource` reads the synthetic dataset shipped with the app and
  works fully offline, which makes demonstrations independent of the network.
* :class:`OpenAlexSource` searches OpenAlex and delegates network retrieval to
  the tested ``OpenAlexProvider`` of citemap-core. The HTTP function is wrapped
  so that every raw OpenAlex record passing through is kept, which gives the
  abstracts, DOIs and venues that citemap-core itself does not model.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from importlib import resources
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import networkx as nx
from citemap import Paper, build_citation_graph
from citemap.providers import (
    OPENALEX_BASE_URL,
    OpenAlexProvider,
    ProviderError,
    normalise_work_id,
    work_to_paper,
)

from citemap_api import __version__
from citemap_api.domain import Network, PaperMeta, SearchHit

JsonGetter = Callable[[str], Mapping[str, Any]]

_DOI = re.compile(r"(10\.\d{4,9}/\S+)", re.IGNORECASE)
_WORK_ID = re.compile(r"(?:openalex\.org/)?(W\d+)$", re.IGNORECASE)
_DEMO_ID = re.compile(r"^D\d{3,}$")
_TOKEN = re.compile(r"[a-z0-9]+")


class SourceError(RuntimeError):
    """Base class for data source failures."""


class NotFoundError(SourceError):
    """The requested paper does not exist in the source."""


class InvalidInputError(SourceError):
    """The request cannot be understood, e.g. a malformed identifier."""


class UpstreamError(SourceError):
    """The external service failed or refused the request."""


class DataSource(Protocol):
    name: str
    label: str
    expires: bool

    def normalise(self, seed_id: str) -> str:
        """Canonical form of an identifier; raises :class:`InvalidInputError`."""
        ...

    def search(self, query: str, limit: int = 10) -> list[SearchHit]: ...

    def fetch(self, seed_id: str) -> Network: ...


# ---------------------------------------------------------------- demo
def _tokens(text: str) -> set[str]:
    """Lower-case word tokens with a plural "s" removed, so "graph" finds "graphs"."""
    return {t[:-1] if len(t) > 3 and t.endswith("s") else t for t in _TOKEN.findall(text.lower())}


class DemoSource:
    """Synthetic network bundled with the application."""

    name = "demo"
    label = "Demo dataset (synthetic, offline)"
    expires = False

    def __init__(self, raw: Mapping[str, Any] | None = None, radius: int = 2) -> None:
        if raw is None:
            text = (
                resources.files("citemap_api.data")
                .joinpath("demo_network.json")
                .read_text(encoding="utf-8")
            )
            raw = json.loads(text)
        self._raw_meta: dict[str, Any] = dict(raw.get("meta", {}))
        self._radius = radius
        self.papers: list[Paper] = []
        self.meta: dict[str, PaperMeta] = {}
        for record in raw["papers"]:
            paper = Paper.from_dict(record)
            self.papers.append(paper)
            self.meta[paper.id] = PaperMeta(
                abstract=record.get("abstract"), venue=record.get("venue")
            )
        self._by_id = {p.id: p for p in self.papers}
        self._graph = build_citation_graph(self.papers)

    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        query = query.strip()
        if query.upper() in self._by_id:
            return [_hit(self._by_id[query.upper()])]
        tokens = _tokens(query)
        scored: list[tuple[int, int, Paper]] = []
        for paper in self.papers:
            if not tokens:
                scored.append((0, paper.cited_by_count, paper))
                continue
            score = (
                3 * len(tokens & _tokens(paper.title))
                + 2 * len(tokens & _tokens(" ".join(paper.authors)))
                + len(tokens & _tokens(self.meta[paper.id].abstract or ""))
            )
            if score:
                scored.append((score, paper.cited_by_count, paper))
        scored.sort(key=lambda s: (-s[0], -s[1], s[2].id))
        return [_hit(p) for _, _, p in scored[:limit]]

    def normalise(self, seed_id: str) -> str:
        canonical = seed_id.strip().upper()
        if not _DEMO_ID.match(canonical):
            raise InvalidInputError(f"Not a demo paper id: {seed_id!r} (expected e.g. D042)")
        return canonical

    def fetch(self, seed_id: str) -> Network:
        seed_id = self.normalise(seed_id)
        if seed_id not in self._by_id:
            raise NotFoundError(f"Paper {seed_id} is not in the demo dataset")
        neighbourhood = nx.ego_graph(
            self._graph.to_undirected(as_view=True), seed_id, radius=self._radius
        )
        keep = set(neighbourhood.nodes)
        papers = [p for p in self.papers if p.id in keep]
        return Network(
            source=self.name,
            seed_id=seed_id,
            papers=papers,
            meta={p.id: self.meta[p.id] for p in papers},
            provenance={**self._raw_meta, "radius": self._radius},
        )


# ---------------------------------------------------------------- OpenAlex
def reconstruct_abstract(inverted: Mapping[str, list[int]] | None) -> str | None:
    """OpenAlex stores abstracts as ``{word: [positions]}``; rebuild the text."""
    if not inverted:
        return None
    positions = [(pos, word) for word, places in inverted.items() for pos in places]
    return " ".join(word for _, word in sorted(positions)) or None


def _work_meta(work: Mapping[str, Any]) -> PaperMeta:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    doi = work.get("doi")
    return PaperMeta(
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        doi=doi,
        url=doi or location.get("landing_page_url") or work.get("id"),
        venue=source.get("display_name"),
    )


class _RecordingGetter:
    """Wraps an HTTP getter and remembers every OpenAlex work it returns."""

    def __init__(self, inner: JsonGetter) -> None:
        self._inner = inner
        self.works: dict[str, Mapping[str, Any]] = {}

    def __call__(self, url: str) -> Mapping[str, Any]:
        data = self._inner(url)
        records = data.get("results") if "results" in data else [data]
        for work in records or []:
            if isinstance(work, Mapping) and work.get("id"):
                self.works[normalise_work_id(str(work["id"]))] = work
        return data


def urllib_get_json(url: str, timeout: float = 30.0) -> Mapping[str, Any]:  # pragma: no cover
    """Default HTTP client. Excluded from coverage: tests never touch the network."""
    request = Request(url, headers={"User-Agent": f"citemap-api/{__version__}"})
    try:
        with urlopen(request, timeout=timeout) as response:
            data: Mapping[str, Any] = json.loads(response.read().decode("utf-8"))
            return data
    except HTTPError as exc:
        if exc.code == 404:
            raise NotFoundError("OpenAlex has no record for this identifier") from exc
        if exc.code == 429:
            raise UpstreamError(
                "OpenAlex rate limit reached. Wait a minute, or set OPENALEX_API_KEY."
            ) from exc
        raise UpstreamError(f"OpenAlex returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise UpstreamError(f"Could not reach OpenAlex: {exc.reason}") from exc


class OpenAlexSource:
    """Live data from the OpenAlex API (https://openalex.org)."""

    name = "openalex"
    label = "OpenAlex (live, needs internet)"
    expires = True

    def __init__(
        self,
        api_key: str | None = None,
        mailto: str | None = None,
        max_citing: int = 50,
        http_get: JsonGetter | None = None,
    ) -> None:
        self._api_key = api_key or ""
        self._mailto = mailto
        self._max_citing = max_citing
        self._http_get: JsonGetter = http_get or urllib_get_json

    def _url(self, path: str, params: Mapping[str, str] | None = None) -> str:
        query = dict(params or {})
        if self._api_key:
            query["api_key"] = self._api_key
        if self._mailto:
            query["mailto"] = self._mailto
        url = OPENALEX_BASE_URL + path
        return url + ("?" + urlencode(query, safe=":|,", quote_via=quote) if query else "")

    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        query = query.strip()
        if not query:
            return []
        work_match = _WORK_ID.search(query)
        doi_match = _DOI.search(query)
        try:
            if work_match:
                work = self._http_get(self._url(f"/works/{work_match.group(1).upper()}"))
                return [_hit(work_to_paper(work))]
            if doi_match:
                doi = doi_match.group(1).rstrip(".")
                work = self._http_get(self._url(f"/works/doi:{doi}"))
                return [_hit(work_to_paper(work))]
            data = self._http_get(
                self._url("/works", {"search": query, "per_page": str(min(limit, 25))})
            )
        except NotFoundError:
            return []
        except ProviderError as exc:
            raise UpstreamError(str(exc)) from exc
        return [_hit(work_to_paper(w)) for w in data.get("results", [])][:limit]

    def normalise(self, seed_id: str) -> str:
        try:
            return normalise_work_id(seed_id.strip())
        except ProviderError as exc:
            raise InvalidInputError(str(exc)) from exc

    def fetch(self, seed_id: str) -> Network:
        work_id = self.normalise(seed_id)
        recorder = _RecordingGetter(self._http_get)
        provider = OpenAlexProvider(
            api_key=self._api_key,
            mailto=self._mailto,
            max_citing=self._max_citing,
            http_get=recorder,
        )
        try:
            papers = provider.fetch_network(work_id)
        except ProviderError as exc:
            raise UpstreamError(str(exc)) from exc
        meta = {pid: _work_meta(work) for pid, work in recorder.works.items()}
        return Network(
            source=self.name,
            seed_id=work_id,
            papers=papers,
            meta=meta,
            provenance={
                "source": "OpenAlex",
                "api": OPENALEX_BASE_URL,
                "max_citing": self._max_citing,
            },
        )


def _hit(paper: Paper) -> SearchHit:
    return SearchHit(
        id=paper.id,
        title=paper.title,
        year=paper.year,
        authors=paper.authors,
        cited_by_count=paper.cited_by_count,
    )
