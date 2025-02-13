"""Minimal wrapper for libgit2 - Commit"""

from functools import cached_property
from typing import Optional, Union

from .native_adaptation import git_commit_p, git_object_t, git_tree_p, lib
from .object_ import Object
from .oid import Oid
from .signature import Signature
from .tree import Tree

CommitTypes = Union[git_commit_p, Oid, str, bytes]


class Commit(Object):
    """Represent a git commit."""

    _libgit2_native_finalizer = "git_commit_free"

    _object_type = git_commit_p
    _object_t = git_object_t.COMMIT

    _real_native: Optional[git_commit_p] = None

    @cached_property
    def parents(self) -> list["Commit"]:
        n_parents = lib.git_commit_parentcount(self._native)
        parents = []
        for n in range(n_parents):
            native = git_commit_p()
            error_code = lib.git_commit_parent(native, self._native, n)
            self.raise_if_error(error_code, "Error getting parent: {message}")
            parents.append(Commit(_repo=self._repo, _native=native))
        return parents

    @cached_property
    def tree(self) -> "Tree":
        native = git_tree_p()
        error_code = lib.git_commit_tree(native, self._native)
        self.raise_if_error(error_code, "Error retrieving tree: {message}")
        return Tree(_repo=self._repo, _native=native)

    @cached_property
    def commit_time(self) -> int:
        return lib.git_commit_time(self._native)

    @cached_property
    def commit_time_offset(self) -> int:
        return lib.git_commit_time_offset(self._native)

    @cached_property
    def author(self) -> "Signature":
        return Signature._from_native(native=lib.git_commit_author(self._native), _owner=self)

    @cached_property
    def committer(self) -> "Signature":
        return Signature._from_native(native=lib.git_commit_committer(self._native), _owner=self)

    @cached_property
    def message_encoding(self) -> Optional[str]:
        encoding = lib.git_commit_message_encoding(self._native)
        if encoding:
            encoding = encoding.decode("ascii")
        else:
            encoding = "utf-8"
        return encoding

    @cached_property
    def message(self) -> str:
        message = lib.git_commit_message(self._native)
        return message.decode(encoding=self.message_encoding, errors="replace")
