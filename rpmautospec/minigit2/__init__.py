"""Minimal wrapper for libgit2

This package wraps the functionality of libgit2 used by rpmautospec (and
only that), aiming to mimic the pygit2 API (of the minimum version
supported, 1.1).

The reason why we don’t use pygit2 itself is because it makes
bootstrapping rpmautospec hairy (e.g. for a new Python version).
"""

from .constants import GIT_REPOSITORY_OPEN_NO_SEARCH
from .exc import GitError
from .wrapper import Commit, Repository, Tree
