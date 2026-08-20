"""Minimal wrapper for libgit2

This package wraps the functionality of libgit2 used by rpmautospec (and
only that), aiming to mimic the pygit2 API (of version 1.20).

The reason we want to be able to bypass pygit2 itself is because it
makes bootstrapping rpmautospec hairy (e.g. for a new Python version).
"""

from . import enums, settings
from .blob import Blob
from .commit import Commit
from .exc import GitError
from .oid import Oid
from .repository import Repository
from .signature import Signature
from .tree import Tree

init_repository = Repository.init_repository
