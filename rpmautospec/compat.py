from importlib.metadata import EntryPoint, entry_points
from io import BytesIO

try:
    import pygit2
except ImportError:  # pragma: has-no-pygit2
    from . import minigit2 as pygit2

    uses_minigit2 = True
else:  # pragma: has-pygit2
    import pygit2.enums

    uses_minigit2 = False

needs_minimal_blobio = False
if uses_minigit2:  # pragma: has-no-pygit2
    needs_minimal_blobio = True
else:  # pragma: has-pygit2
    try:
        from pygit2 import BlobIO
    except ImportError:  # pragma: no cover
        needs_minimal_blobio = True


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


if needs_minimal_blobio:  # pragma: no cover
    BlobIO = MinimalBlobIO


def cli_plugin_entry_points() -> tuple[EntryPoint]:
    """Find entry points for CLI plugins.

    :return: Entry points implementing CLI commands
    """
    try:
        return entry_points(group="rpmautospec.cli")
    except TypeError:
        return entry_points()["rpmautospec.cli"]
