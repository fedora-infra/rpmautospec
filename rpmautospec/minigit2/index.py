"""Minimal wrapper for libgit2 - Index"""

from collections.abc import Collection
from ctypes import byref, c_char_p, c_void_p
from os import PathLike, fspath
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import TYPE_CHECKING, Optional, Union

from .constants import GIT_DIFF_OPTIONS_VERSION
from .diff import Diff
from .native_adaptation import (
    git_diff_option_t,
    git_diff_options,
    git_diff_p,
    git_index_matched_path_cb,
    git_index_p,
    git_oid,
    git_strarray,
    lib,
)
from .oid import Oid
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .repository import Repository


class Index(WrapperOfWrappings):
    """Represent the git index."""

    _libgit2_native_finalizer = "git_index_free"

    _repo: "Repository"
    _real_native: Optional[git_index_p]

    def __init__(self, repo: "Repository", native: git_index_p) -> None:
        self._repo = repo
        super().__init__(native=native)

    def write(self) -> None:
        error_code = lib.git_index_write(self._native)
        self.raise_if_error(error_code)

    def write_tree(self) -> Oid:
        native_oid = git_oid()
        error_code = lib.git_index_write_tree(byref(native_oid), self._native)
        self.raise_if_error(error_code)
        return Oid(native_oid)

    def remove(self, path: Union[PathLike, str, bytes]) -> None:
        path = fspath(path)
        if isinstance(path, str):
            path = path.encode(encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors())
        error_code = lib.git_index_remove(self._native, path, 0)
        self.raise_if_error(error_code)

    def add_all(self, pathspecs: Optional[Collection[Union[PathLike, str, bytes]]] = None) -> None:
        pathspecs = (fspath(ps) for ps in pathspecs) if pathspecs else []

        encoding = getfilesystemencoding()
        errors = getfilesystemencodeerrors()
        pathspecs = [
            ps.encode(encoding=encoding, errors=errors) if isinstance(ps, str) else ps
            for ps in pathspecs
        ]

        count = len(pathspecs)
        native_specs_array = git_strarray(strings=(c_char_p * count)(*pathspecs), count=count)

        error_code = lib.git_index_add_all(
            self._native, byref(native_specs_array), 0, git_index_matched_path_cb(), c_void_p()
        )
        self.raise_if_error(error_code, io=True)

    def add(self, path: Union[PathLike, str, bytes]) -> None:
        path = fspath(path)
        if isinstance(path, str):
            path = path.encode(encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors())

        error_code = lib.git_index_add_bypath(self._native, path)
        self.raise_if_error(error_code, io=True)

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

        error_code = lib.git_diff_index_to_workdir(
            diff_p, self._repo._native, self._native, diff_options
        )
        self.raise_if_error(error_code)

        return Diff(repo=self._repo, native=diff_p)
