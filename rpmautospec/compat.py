from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
