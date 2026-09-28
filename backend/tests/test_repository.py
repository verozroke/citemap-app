from __future__ import annotations

from pathlib import Path

from citemap_api.repository import Repository


def test_networks_round_trip(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "nested" / "db.sqlite3")
    assert repo.get_network("demo", "D001") is None
    repo.save_network("demo", "D001", {"nodes": [1, 2]})
    repo.save_network("demo", "D001", {"nodes": [3]})
    stored = repo.get_network("demo", "D001")
    assert stored is not None
    assert stored.document == {"nodes": [3]}
    assert stored.fetched_at.tzinfo is not None


def test_job_lifecycle(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "db.sqlite3")
    job = repo.create_job("demo", "D001")
    assert repo.find_active_job("demo", "D001") == job
    repo.update_job(job.id, "failed", "broken")
    stored = repo.get_job(job.id)
    assert stored is not None
    assert (stored.status, stored.error) == ("failed", "broken")
    assert repo.find_active_job("demo", "D001") is None
    assert repo.get_job("missing") is None


def test_interrupted_jobs_are_failed(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "db.sqlite3")
    queued = repo.create_job("demo", "D001")
    done = repo.create_job("demo", "D002", status="done", cached=True)
    assert Repository(tmp_path / "db.sqlite3").fail_interrupted_jobs() == 1
    assert repo.get_job(queued.id).status == "failed"  # type: ignore[union-attr]
    assert repo.get_job(done.id).cached is True  # type: ignore[union-attr]
