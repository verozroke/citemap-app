from __future__ import annotations

import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest

from citemap_api.domain import Network
from citemap_api.jobs import JobRunner, UnknownSourceError
from citemap_api.repository import Repository
from citemap_api.sources import DemoSource, InvalidInputError, OpenAlexSource
from tests.conftest import FakeOpenAlex


class ExplodingSource(DemoSource):
    def fetch(self, seed_id: str) -> Network:
        raise RuntimeError("disk on fire")


class SlowSource(DemoSource):
    def __init__(self) -> None:
        super().__init__()
        self.release = threading.Event()
        self.calls = 0

    def fetch(self, seed_id: str) -> Network:
        self.calls += 1
        self.release.wait(5)
        return super().fetch(seed_id)


def wait_for(repo: Repository, job_id: str, timeout: float = 10) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = repo.get_job(job_id)
        assert job is not None
        if job.status in ("done", "failed"):
            return job.status
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_inline_job_then_cache_hit(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "db.sqlite3")
    runner = JobRunner(repo, {"demo": DemoSource()}, inline=True)
    first = runner.submit("demo", "d042")
    assert (first.status, first.cached, first.seed_id) == ("done", False, "D042")
    second = runner.submit("demo", "D042")
    assert (second.status, second.cached) == ("done", True)
    refreshed = runner.submit("demo", "D042", refresh=True)
    assert refreshed.cached is False


def test_live_networks_expire(tmp_path: Path, fake_openalex: FakeOpenAlex) -> None:
    repo = Repository(tmp_path / "db.sqlite3")
    runner = JobRunner(
        repo, {"openalex": OpenAlexSource(http_get=fake_openalex)}, cache_ttl_hours=1, inline=True
    )
    runner.submit("openalex", "W1")
    assert runner.is_fresh("openalex", "W1")
    runner._ttl = timedelta(0)
    assert not runner.is_fresh("openalex", "W1")
    assert runner.submit("openalex", "W1").cached is False


def test_errors_are_reported_on_the_job(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "db.sqlite3")
    runner = JobRunner(repo, {"demo": DemoSource(), "bad": ExplodingSource()}, inline=True)
    missing = runner.submit("demo", "D999")
    assert missing.status == "failed"
    assert "not in the demo dataset" in (missing.error or "")
    exploded = runner.submit("bad", "D001")
    assert exploded.error == "Unexpected error: disk on fire"


def test_invalid_requests_raise(tmp_path: Path) -> None:
    runner = JobRunner(Repository(tmp_path / "db.sqlite3"), {"demo": DemoSource()}, inline=True)
    with pytest.raises(UnknownSourceError):
        runner.submit("nope", "D001")
    with pytest.raises(InvalidInputError):
        runner.submit("demo", "W1")


def test_background_jobs_are_deduplicated(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "db.sqlite3")
    source = SlowSource()
    runner = JobRunner(repo, {"demo": source})
    try:
        first = runner.submit("demo", "D042")
        second = runner.submit("demo", "D042")
        assert second.id == first.id
        source.release.set()
        assert wait_for(repo, first.id) == "done"
        assert source.calls == 1
    finally:
        runner.shutdown()
