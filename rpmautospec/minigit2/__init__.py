"""Minimal wrapper for libgit2

This package wraps the functionality of libgit2 used by rpmautospec (and
only that), aiming to mimic the pygit2 API (of the minimum version
supported, 1.1).

The reason we want to be able to bypass pygit2 itself is because it
makes bootstrapping rpmautospec hairy (e.g. for a new Python version).
"""

from . import enums, settings
from .blob import Blob
from .commit import Commit
from .constants import (
    GIT_CHECKOUT_FORCE,
    GIT_CONFIG_LEVEL_GLOBAL,
    GIT_CONFIG_LEVEL_LOCAL,
    GIT_CONFIG_LEVEL_SYSTEM,
    GIT_CONFIG_LEVEL_XDG,
    GIT_REPOSITORY_OPEN_NO_SEARCH,
    GIT_STATUS_CONFLICTED,
    GIT_STATUS_CURRENT,
    GIT_STATUS_IGNORED,
    GIT_STATUS_INDEX_DELETED,
    GIT_STATUS_INDEX_MODIFIED,
    GIT_STATUS_INDEX_NEW,
    GIT_STATUS_INDEX_RENAMED,
    GIT_STATUS_INDEX_TYPECHANGE,
    GIT_STATUS_WT_DELETED,
    GIT_STATUS_WT_MODIFIED,
    GIT_STATUS_WT_NEW,
    GIT_STATUS_WT_RENAMED,
    GIT_STATUS_WT_TYPECHANGE,
    GIT_STATUS_WT_UNREADABLE,
)
from .exc import GitError
from .oid import Oid
from .repository import Repository
from .signature import Signature
from .tree import Tree

init_repository = Repository.init_repository
