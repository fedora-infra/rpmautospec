"""Minimal wrapper for libgit2 - Walk revisions"""

from collections.abc import Iterator
from ctypes import byref
from typing import TYPE_CHECKING, Optional

from .commit import Commit
from .native_adaptation import git_commit_p, git_error_code, git_oid, git_revwalk_p, lib
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .repository import Repository


class RevWalk(WrapperOfWrappings, Iterator):
    """Represent a walk over commits in a repository."""

    _libgit2_native_finalizer = "git_revwalk_free"

    _repo: "Repository"
    _native = Optional[git_revwalk_p]

    def __init__(self, repo: "Repository", native: git_revwalk_p) -> None:
        self._repo = repo
        super().__init__(native=native)

    def __iter__(self) -> Iterator[Commit]:
        return self

    def __next__(self) -> Commit:
        oid = git_oid()
        oid_p = byref(oid)

        error_code = lib.git_revwalk_next(oid_p, self._native)
        if error_code == git_error_code.ITEROVER:
            raise StopIteration
        self.raise_if_error(error_code)

        commit = git_commit_p()
        error_code = lib.git_commit_lookup(commit, self._repo._native, oid_p)
        self.raise_if_error(error_code)

        return Commit(_repo=self._repo, _native=commit)
