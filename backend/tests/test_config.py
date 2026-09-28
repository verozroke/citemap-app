from __future__ import annotations

from pathlib import Path

import pytest

from citemap_api.config import Settings


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "CITEMAP_DATA_DIR",
        "OPENALEX_API_KEY",
        "CITEMAP_STATIC_DIR",
        "CITEMAP_CORS_ORIGINS",
        "CITEMAP_MAX_CITING",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env()
    assert settings.database_path == Path(".citemap-data") / "citemap.sqlite3"
    assert settings.openalex_api_key is None
    assert settings.max_citing == 50
    assert settings.cors_origins == ("http://localhost:5173",)


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CITEMAP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENALEX_API_KEY", " secret ")
    monkeypatch.setenv("OPENALEX_MAILTO", "me@example.org")
    monkeypatch.setenv("CITEMAP_MAX_CITING", "20")
    monkeypatch.setenv("CITEMAP_CACHE_TTL_HOURS", "2.5")
    monkeypatch.setenv("CITEMAP_STATIC_DIR", str(tmp_path / "dist"))
    monkeypatch.setenv("CITEMAP_CORS_ORIGINS", "http://a.test, http://b.test")
    settings = Settings.from_env()
    assert settings.data_dir == tmp_path
    assert settings.openalex_api_key == "secret"
    assert settings.openalex_mailto == "me@example.org"
    assert settings.max_citing == 20
    assert settings.cache_ttl_hours == 2.5
    assert settings.static_dir == tmp_path / "dist"
    assert settings.cors_origins == ("http://a.test", "http://b.test")
