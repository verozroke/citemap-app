from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi.testclient import TestClient

from citemap_api.config import Settings
from citemap_api.main import create_app, parse_clusters
from citemap_api.repository import Repository
from citemap_api.sources import DemoSource


def build(client: TestClient, source: str = "demo", seed_id: str = "D042") -> dict:
    response = client.post("/api/graphs", json={"source": source, "seed_id": seed_id})
    assert response.status_code == 202
    return response.json()


def test_health_and_sources(client: TestClient) -> None:
    assert client.get("/api/health").json()["status"] == "ok"
    sources = {s["name"]: s for s in client.get("/api/sources").json()}
    assert set(sources) == {"demo", "openalex"}
    assert sources["demo"]["example"] == "D042"


def test_search(client: TestClient) -> None:
    hits = client.get("/api/search", params={"q": "graph layout", "limit": 3}).json()
    assert len(hits) == 3
    assert isinstance(hits[0]["authors"], list)
    live = client.get("/api/search", params={"q": "community", "source": "openalex"}).json()
    assert [h["id"] for h in live] == ["W2"]


def test_search_validation(client: TestClient) -> None:
    assert client.get("/api/search", params={"limit": 0}).status_code == 422
    response = client.get("/api/search", params={"source": "nope"})
    assert response.status_code == 404
    assert "Unknown data source" in response.json()["detail"]


def test_build_poll_and_view(client: TestClient) -> None:
    job = build(client, seed_id="d042")
    assert job["status"] == "done"
    assert client.get(f"/api/jobs/{job['id']}").json() == job
    view = client.get("/api/graphs/demo/d042").json()
    assert view["seed_id"] == "D042"
    assert view["shown_nodes"] == len(view["nodes"]) > 10
    assert view["fetched_at"]
    assert any(node["is_seed"] for node in view["nodes"])
    assert build(client)["cached"] is True


def test_view_filters(client: TestClient) -> None:
    build(client)
    small = client.get("/api/graphs/demo/D042", params={"limit": 5}).json()
    assert small["shown_nodes"] == 5
    only_zero = client.get("/api/graphs/demo/D042", params={"clusters": "0"}).json()
    assert {n["cluster"] for n in only_zero["nodes"] if not n["is_seed"]} == {0}
    bad = client.get("/api/graphs/demo/D042", params={"clusters": "x"})
    assert bad.status_code == 400
    assert client.get("/api/graphs/demo/D042", params={"limit": 0}).status_code == 422


def test_exports(client: TestClient) -> None:
    build(client)
    response = client.get("/api/graphs/demo/D042/export.csv", params={"limit": 4})
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="citemap-D042.csv"' in response.headers["content-disposition"]
    assert len(list(csv.DictReader(io.StringIO(response.text)))) == 4
    data = client.get("/api/graphs/demo/D042/export.json").json()
    assert data["seed_id"] == "D042"
    assert data["links"]


def test_openalex_graph(client: TestClient) -> None:
    job = build(client, "openalex", "https://openalex.org/W1")
    assert job["seed_id"] == "W1"
    view = client.get("/api/graphs/openalex/W1").json()
    assert view["total_nodes"] == 5
    seed = next(n for n in view["nodes"] if n["is_seed"])
    assert seed["doi"] == "https://doi.org/10.1234/gnn"


def test_error_responses(client: TestClient) -> None:
    assert client.post("/api/graphs", json={"source": "demo", "seed_id": "W1"}).status_code == 400
    assert client.post("/api/graphs", json={"source": "x", "seed_id": "D001"}).status_code == 404
    assert client.post("/api/graphs", json={"source": "demo", "seed_id": ""}).status_code == 422
    failed = build(client, seed_id="D999")
    assert failed["status"] == "failed"
    missing = client.get("/api/graphs/demo/D043")
    assert missing.status_code == 404
    assert "POST /api/graphs" in missing.json()["detail"]
    assert client.get("/api/jobs/nope").status_code == 404


def test_upstream_failure_maps_to_502(settings: Settings) -> None:
    class Down(DemoSource):
        def search(self, query: str, limit: int = 10) -> list:
            from citemap_api.sources import UpstreamError

            raise UpstreamError("OpenAlex is down")

    with TestClient(create_app(settings, {"demo": Down()})) as client:
        response = client.get("/api/search", params={"q": "x"})
    assert response.status_code == 502
    assert response.json() == {"detail": "OpenAlex is down"}


def test_startup_fails_interrupted_jobs(settings: Settings) -> None:
    job = Repository(settings.database_path).create_job("demo", "D001")
    with TestClient(create_app(settings, {"demo": DemoSource()})) as client:
        status = client.get(f"/api/jobs/{job.id}").json()
    assert status["status"] == "failed"
    assert "restart" in status["error"]


def test_serves_frontend_and_cors(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>CiteMap</h1>", encoding="utf-8")
    settings = Settings(
        data_dir=tmp_path / "d",
        static_dir=dist,
        run_jobs_inline=True,
        cors_origins=("http://localhost:5173",),
    )
    with TestClient(create_app(settings, {"demo": DemoSource()})) as client:
        assert "CiteMap" in client.get("/").text
        preflight = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_default_sources_are_created_from_settings(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, openalex_api_key="k"))
    try:
        with TestClient(app) as client:
            names = [s["name"] for s in client.get("/api/sources").json()]
        assert names == ["demo", "openalex"]
    finally:
        app.state.runner.shutdown()


def test_parse_clusters() -> None:
    assert parse_clusters(None) is None
    assert parse_clusters(" ") is None
    assert parse_clusters("0, 2,") == frozenset({0, 2})
