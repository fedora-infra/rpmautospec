"""Minimal wrapper for libgit2 - Tree"""

from ctypes import byref
from typing import TYPE_CHECKING, Optional, Union

from .constants import GIT_DIFF_OPTIONS_VERSION
from .diff import Diff
from .native_adaptation import (
    git_diff_option_t,
    git_diff_options,
    git_diff_p,
    git_object_p,
    git_object_t,
    git_tree_entry_p,
    git_tree_p,
    lib,
)
from .object_ import Object

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .index import Index


class Tree(Object):
    """Represent a git tree."""

    _libgit2_native_finalizer = "git_tree_free"

    _object_type = git_tree_p
    _object_t = git_object_t.TREE

    _real_native: Optional[git_tree_p] = None

    def _get_tree_entry_for_path(self, path: Union[str, bytes]) -> git_tree_entry_p:
        if isinstance(path, str):
            path = path.encode("utf-8")

        entry = git_tree_entry_p()
        error_code = lib.git_tree_entry_bypath(entry, self._native, path)
        self.raise_if_error(error_code, key=path)

        return entry

    def __contains__(self, path: Union[str, bytes]) -> bool:
        try:
            entry = self._get_tree_entry_for_path(path)
        except KeyError:
            return False
        else:
            lib.git_tree_entry_free(entry)
            return True

    def _object_from_tree_entry(self, entry: git_tree_entry_p) -> Object:
        native = git_object_p()
        error_code = lib.git_tree_entry_to_object(native, self._repo._native, entry)
        self.raise_if_error(error_code)
        return Object._from_native(repo=self._repo, native=native, _entry=entry)

    def __getitem__(self, path: Union[str, bytes]) -> Object:
        return self._object_from_tree_entry(self._get_tree_entry_for_path(path))

    def __len__(self) -> int:
        return lib.git_tree_entrycount(self._native)

    def __iter__(self) -> "Iterator[Object]":
        for idx in range(len(self)):
            unowned_entry = lib.git_tree_entry_byindex(self._native, idx)
            self.raise_if_error(not unowned_entry, "Error looking up tree entry: {message}")

            owned_entry = git_tree_entry_p()
            error_code = lib.git_tree_entry_dup(byref(owned_entry), unowned_entry)
            self.raise_if_error(error_code)

            yield self._object_from_tree_entry(owned_entry)

    def diff_to_tree(
        self,
        tree: "Tree",
        flags: git_diff_option_t = git_diff_option_t.NORMAL,
        context_lines: int = 3,
        interhunk_lines: int = 0,
        swap: bool = False,
    ) -> Diff:
        diff_options = git_diff_options()
        error_code = lib.git_diff_options_init(diff_options, GIT_DIFF_OPTIONS_VERSION)
        self.raise_if_error(error_code, "Can’t initialize diff options: {message}")

        diff_options.flags = flags
        diff_options.context_lines = context_lines
        diff_options.interhunk_lines = interhunk_lines

        diff_p = git_diff_p()

        if swap:
            a, b = tree._native, self._native
        else:
            a, b = self._native, tree._native

        error_code = lib.git_diff_tree_to_tree(diff_p, self._repo._native, a, b, diff_options)
        self.raise_if_error(error_code, "Error diffing tree to tree: {message}")

        return Diff(self._repo, diff_p)

    def diff_to_workdir(
        self,
        flags: git_diff_option_t = git_diff_option_t.NORMAL,
        context_lines: int = 3,
        interhunk_lines: int = 0,
    ) -> Diff:
        diff_options = git_diff_options()
        error_code = lib.git_diff_options_init(diff_options, GIT_DIFF_OPTIONS_VERSION)
        self.raise_if_error(error_code)

        diff_options.flags = flags
        diff_options.context_lines = context_lines
        diff_options.interhunk_lines = interhunk_lines

        diff_p = git_diff_p()

        error_code = lib.git_diff_tree_to_workdir(
            diff_p, self._repo._native, self._native, diff_options
        )
        self.raise_if_error(error_code)

        return Diff(repo=self._repo, native=diff_p)

    def diff_to_index(
        self,
        index: "Index",
        flags: git_diff_option_t = git_diff_option_t.NORMAL,
        context_lines: int = 3,
        interhunk_lines: int = 0,
    ) -> Diff:
        diff_options = git_diff_options()
        error_code = lib.git_diff_options_init(diff_options, GIT_DIFF_OPTIONS_VERSION)
        self.raise_if_error(error_code)

        diff_options.flags = flags
        diff_options.context_lines = context_lines
        diff_options.interhunk_lines = interhunk_lines

        diff_p = git_diff_p()

        error_code = lib.git_diff_tree_to_index(
            diff_p, self._repo._native, self._native, index._native, diff_options
        )
        self.raise_if_error(error_code)

        return Diff(repo=self._repo, native=diff_p)
