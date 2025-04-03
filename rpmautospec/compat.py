from io import BytesIO
from typing import TYPE_CHECKING

try:
    import pygit2
except ImportError:  # pragma: has-no-pygit2
    from ._wrappers import minigit2 as pygit2  # noqa: F401

    uses_minigit2 = True
else:  # pragma: has-pygit2
    uses_minigit2 = False

needs_minimal_blobio = False
if uses_minigit2:  # pragma: has-no-pygit2
    needs_minimal_blobio = True
else:  # pragma: has-pygit2
    try:
        from pygit2 import BlobIO
    except ImportError:  # pragma: no cover
        needs_minimal_blobio = True

try:
    import rpm
except ImportError:  # pragma: has-no-rpm
    from ._wrappers import minirpm as rpm  # noqa: F401

if TYPE_CHECKING:
    if uses_minigit2:
        from .minigit2 import Blob, Oid
    else:
        from pygit2 import Blob, Oid


class MinimalBlobIO:
    """Minimal substitute for pygit2.BlobIO for old pygit2 versions.

    This doesn’t do any of the filtering"""

    def __init__(self, blob: "Blob", *, as_path: str = None, commit_id: "Oid" = None) -> None:
        self.blob = blob
        # the rest is ignored

    def __enter__(self) -> BytesIO:
        return BytesIO(self.blob.data)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass


if needs_minimal_blobio:  # pragma: no cover
    BlobIO = MinimalBlobIO
