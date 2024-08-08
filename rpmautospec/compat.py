from importlib.metadata import EntryPoint, entry_points
from io import BytesIO

import pygit2


class MinimalBlobIO:
    """Minimal substitute for pygit2.BlobIO for old pygit2 versions.

    This doesn’t do any of the filtering"""

    def __init__(self, blob: pygit2.Blob, *, as_path: str = None, commit_id: pygit2.Oid = None):
        self.blob = blob
        # the rest is ignored

    def __enter__(self):
        return BytesIO(self.blob.data)

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def cli_plugin_entry_points() -> tuple[EntryPoint]:
    """Find entry points for CLI plugins.

    :return: Entry points implementing CLI commands
    """
    try:
        return entry_points(group="rpmautospec.cli")
    except TypeError:
        return entry_points()["rpmautospec.cli"]
