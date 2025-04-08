from importlib import metadata

try:
    __version__ = metadata.version("rpmautospec")
except Exception:  # pragma: no cover
    __version__ = "0.0.0"
__version_info__ = tuple(int(x) for x in __version__.split("."))
