from importlib import metadata

__version__ = metadata.version("rpmautospec")
__version_info__ = tuple(int(x) for x in __version__.split("."))
