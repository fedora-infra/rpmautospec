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
