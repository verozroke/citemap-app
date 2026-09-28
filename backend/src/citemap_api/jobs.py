"""Background construction of citation graphs.

Fetching a live network, building the graph and clustering it takes seconds,
far longer than a web request should block. The API therefore only creates a
job and returns immediately; the work happens in a thread pool and the client
polls the job status (adjustment A2 from Assignment 2).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from citemap_api.analysis import enrich
from citemap_api.repository import Job, Repository, utcnow
from citemap_api.sources import DataSource, SourceError

log = logging.getLogger(__name__)


class UnknownSourceError(ValueError):
    pass


class JobRunner:
    def __init__(
        self,
        repository: Repository,
        sources: Mapping[str, DataSource],
        cache_ttl_hours: float = 168.0,
        inline: bool = False,
        max_workers: int = 2,
    ) -> None:
        self._repo = repository
        self._sources = sources
        self._ttl = timedelta(hours=cache_ttl_hours)
        self._inline = inline
        self._pool = (
            None
            if inline
            else ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="citemap-job")
        )

    def is_fresh(self, source: str, seed_id: str) -> bool:
        stored = self._repo.get_network(source, seed_id)
        if stored is None:
            return False
        if not self._sources[source].expires:
            return True
        return utcnow() - stored.fetched_at < self._ttl

    def submit(self, source: str, seed_id: str, refresh: bool = False) -> Job:
        """Start building a graph, or reuse a fresh cached one or a running job.

        Raises:
            UnknownSourceError: ``source`` is not configured.
            InvalidInputError: ``seed_id`` is malformed for this source.
        """
        if source not in self._sources:
            raise UnknownSourceError(f"Unknown data source: {source!r}")
        seed_id = self._sources[source].normalise(seed_id)
        if not refresh and self.is_fresh(source, seed_id):
            return self._repo.create_job(source, seed_id, status="done", cached=True)
        active = self._repo.find_active_job(source, seed_id)
        if active is not None:
            return active
        job = self._repo.create_job(source, seed_id)
        if self._pool is None:
            self._run(job)
        else:
            self._pool.submit(self._run, job)
        return self._repo.get_job(job.id) or job

    def _run(self, job: Job) -> None:
        self._repo.update_job(job.id, "running")
        try:
            network = self._sources[job.source].fetch(job.seed_id)
            document = enrich(network)
            self._repo.save_network(job.source, job.seed_id, document)
        except SourceError as exc:
            self._repo.update_job(job.id, "failed", str(exc))
        except Exception as exc:  # unexpected: keep the server alive, report the job
            log.exception("job %s failed", job.id)
            self._repo.update_job(job.id, "failed", f"Unexpected error: {exc}")
        else:
            self._repo.update_job(job.id, "done")

    def shutdown(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
