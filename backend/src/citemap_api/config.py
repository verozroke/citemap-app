"""Application settings, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    """Runtime configuration.

    Attributes:
        data_dir: Where the SQLite cache is stored.
        openalex_api_key: Optional OpenAlex key; requests work without it but
            with a much smaller daily budget.
        openalex_mailto: Contact e-mail sent to OpenAlex, as it recommends.
        max_citing: How many citing works to fetch for a live network (1..100).
        cache_ttl_hours: How long a live OpenAlex network stays fresh in the cache.
        static_dir: Built frontend to serve at ``/``; ``None`` disables it.
        cors_origins: Origins allowed to call the API from a browser (dev server).
        run_jobs_inline: Run graph jobs synchronously; used by tests.
    """

    data_dir: Path = Path(".citemap-data")
    openalex_api_key: str | None = None
    openalex_mailto: str | None = None
    max_citing: int = 50
    cache_ttl_hours: float = 168.0
    static_dir: Path | None = None
    cors_origins: tuple[str, ...] = field(default=("http://localhost:5173",))
    run_jobs_inline: bool = False

    @property
    def database_path(self) -> Path:
        return self.data_dir / "citemap.sqlite3"

    @classmethod
    def from_env(cls) -> Settings:
        static = _env("CITEMAP_STATIC_DIR")
        if static is None:
            default = Path(__file__).resolve().parents[3] / "frontend" / "dist"
            static_dir: Path | None = default if default.is_dir() else None
        else:
            static_dir = Path(static)
        origins = _env("CITEMAP_CORS_ORIGINS")
        return cls(
            data_dir=Path(_env("CITEMAP_DATA_DIR") or ".citemap-data"),
            openalex_api_key=_env("OPENALEX_API_KEY"),
            openalex_mailto=_env("OPENALEX_MAILTO"),
            max_citing=int(_env("CITEMAP_MAX_CITING") or 50),
            cache_ttl_hours=float(_env("CITEMAP_CACHE_TTL_HOURS") or 168),
            static_dir=static_dir,
            cors_origins=tuple(o.strip() for o in origins.split(","))
            if origins
            else ("http://localhost:5173",),
        )
