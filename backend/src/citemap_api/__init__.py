"""CiteMap API: citation network search, graph building, clustering and export."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("citemap-api")
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled tree
    __version__ = "0.0.0+local"
