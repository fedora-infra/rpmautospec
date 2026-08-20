from enum import IntEnum, IntFlag
from io import BytesIO
from typing import TYPE_CHECKING

needs_minimal_pygit2_enums = False

try:
    import pygit2
except ImportError:  # pragma: has-no-pygit2
    from ._wrappers import minigit2 as pygit2  # noqa: F401

    uses_minigit2 = True
else:  # pragma: has-pygit2
    uses_minigit2 = False

    # The pygit2.enums module was introduced partly in 1.13.3 and fully in 1.14.0. Attempt to import
    # the used enum types, so we can monkey-patch them if necessary.
    try:
        from pygit2.enums import CheckoutStrategy, ConfigLevel, FileStatus, RepositoryOpenFlag
    except ImportError:  # pragma: no cover
        needs_minimal_pygit2_enums = True
    else:  # pragma: no cover
        del CheckoutStrategy, ConfigLevel, FileStatus, RepositoryOpenFlag


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


# This is only for pygit2 < 1.14, so ignore it for coverage.
if not uses_minigit2 and needs_minimal_pygit2_enums:  # pragma: no cover

    class _pygit2_enums:
        # Wrap old names in enum classes. See minigit2.enums for which enum types/values are needed.

        class CheckoutStrategy(IntFlag):
            FORCE = pygit2.GIT_CHECKOUT_FORCE

        class ConfigLevel(IntEnum):
            SYSTEM = pygit2.GIT_CONFIG_LEVEL_SYSTEM
            XDG = pygit2.GIT_CONFIG_LEVEL_XDG
            GLOBAL = pygit2.GIT_CONFIG_LEVEL_GLOBAL
            LOCAL = pygit2.GIT_CONFIG_LEVEL_LOCAL

        class FileStatus(IntFlag):
            CURRENT = pygit2.GIT_STATUS_CURRENT
            INDEX_NEW = pygit2.GIT_STATUS_INDEX_NEW
            INDEX_MODIFIED = pygit2.GIT_STATUS_INDEX_MODIFIED
            INDEX_DELETED = pygit2.GIT_STATUS_INDEX_DELETED
            INDEX_RENAMED = pygit2.GIT_STATUS_INDEX_RENAMED
            INDEX_TYPECHANGE = pygit2.GIT_STATUS_INDEX_TYPECHANGE
            WT_NEW = pygit2.GIT_STATUS_WT_NEW
            WT_MODIFIED = pygit2.GIT_STATUS_WT_MODIFIED
            WT_DELETED = pygit2.GIT_STATUS_WT_DELETED
            WT_TYPECHANGE = pygit2.GIT_STATUS_WT_TYPECHANGE
            WT_RENAMED = pygit2.GIT_STATUS_WT_RENAMED
            WT_UNREADABLE = pygit2.GIT_STATUS_WT_UNREADABLE
            IGNORED = pygit2.GIT_STATUS_IGNORED
            CONFLICTED = pygit2.GIT_STATUS_CONFLICTED

        class RepositoryOpenFlag(IntFlag):
            NO_SEARCH = pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH

    pygit2.enums = _pygit2_enums


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
