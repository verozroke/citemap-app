"""SQLite storage for analysed networks and graph-building jobs.

All SQL lives here (adjustment A3 from Assignment 2): the rest of the
application talks to :class:`Repository`, so the storage engine can be
replaced, for example by PostgreSQL for a multi-user deployment, without
changes elsewhere.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS networks (
    source      TEXT NOT NULL,
    seed_id     TEXT NOT NULL,
    fetched_at  TEXT NOT NULL,
    document    TEXT NOT NULL,
    PRIMARY KEY (source, seed_id)
);
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    source      TEXT NOT NULL,
    seed_id     TEXT NOT NULL,
    status      TEXT NOT NULL,
    error       TEXT,
    cached      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_by_seed ON jobs (source, seed_id, status);
"""

ACTIVE = ("queued", "running")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Job:
    id: str
    source: str
    seed_id: str
    status: str
    error: str | None
    cached: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class StoredNetwork:
    document: dict[str, Any]
    fetched_at: datetime


class Repository:
    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self._database = database
        self._write_lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._database, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- networks ----------------------------------------------------------
    def get_network(self, source: str, seed_id: str) -> StoredNetwork | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT document, fetched_at FROM networks WHERE source = ? AND seed_id = ?",
                (source, seed_id),
            ).fetchone()
        if row is None:
            return None
        return StoredNetwork(json.loads(row["document"]), datetime.fromisoformat(row["fetched_at"]))

    def save_network(self, source: str, seed_id: str, document: dict[str, Any]) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO networks (source, seed_id, fetched_at, document) "
                "VALUES (?, ?, ?, ?)",
                (source, seed_id, utcnow().isoformat(), json.dumps(document)),
            )

    # -- jobs --------------------------------------------------------------
    def create_job(
        self, source: str, seed_id: str, status: str = "queued", cached: bool = False
    ) -> Job:
        now = utcnow().isoformat()
        job = Job(uuid.uuid4().hex[:12], source, seed_id, status, None, cached, now, now)
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO jobs (id, source, seed_id, status, error, cached, created_at, "
                "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (job.id, source, seed_id, status, None, int(cached), now, now),
            )
        return job

    def update_job(self, job_id: str, status: str, error: str | None = None) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?",
                (status, error, utcnow().isoformat(), job_id),
            )

    def get_job(self, job_id: str) -> Job | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _job(row) if row else None

    def find_active_job(self, source: str, seed_id: str) -> Job | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE source = ? AND seed_id = ? AND status IN (?, ?) "
                "ORDER BY created_at DESC LIMIT 1",
                (source, seed_id, *ACTIVE),
            ).fetchone()
        return _job(row) if row else None

    def fail_interrupted_jobs(self) -> int:
        """Mark jobs left running by a previous process as failed."""
        with self._write_lock, self._connect() as conn:
            cursor = conn.execute(
                "UPDATE jobs SET status = 'failed', error = 'Interrupted by a server restart', "
                "updated_at = ? WHERE status IN (?, ?)",
                (utcnow().isoformat(), *ACTIVE),
            )
            return cursor.rowcount


def _job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        source=row["source"],
        seed_id=row["seed_id"],
        status=row["status"],
        error=row["error"],
        cached=bool(row["cached"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
