"""Minimal wrapper for libgit2 - Diff, DiffStats & related"""

from collections.abc import Iterator
from ctypes import byref, c_char_p, cast
from functools import cached_property
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import TYPE_CHECKING, Optional

from .enums import DeltaStatus, DiffFlag
from .native_adaptation import (
    git_buf,
    git_diff_delta_p,
    git_diff_file,
    git_diff_flag_t,
    git_diff_format_t,
    git_diff_p,
    git_diff_stats_p,
    git_filemode_t,
    lib,
)
from .oid import Oid
from .wrapper import LibraryUser, WrapperOfWrappings

if TYPE_CHECKING:
    from .repository import Repository


class DiffFile:
    """Represent a file in a delta of a diff."""

    id: Oid
    raw_path: bytes
    path: str
    size: int
    flags: git_diff_flag_t
    mode: git_filemode_t

    def __init__(self, native: git_diff_file) -> None:
        self.id = Oid(native.id)
        if native.path:
            self.raw_path = native.path
            self.path = native.path.decode(
                encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
            )
        else:
            self.raw_path = None
            self.path = None
        self.size = native.size
        self.flags = git_diff_flag_t(native.flags)
        self.mode = git_filemode_t(native.mode)


class DiffDelta(WrapperOfWrappings):
    """Represent a delta of a diff."""

    _real_native: Optional[git_diff_delta_p] = None
    _diff: "Diff"

    def __init__(self, native: git_diff_delta_p, _diff: "Diff") -> None:
        self._diff = _diff
        super().__init__(native=native)

    @cached_property
    def status(self) -> DeltaStatus:
        return DeltaStatus(self._native.contents.status)

    @cached_property
    def flags(self) -> DiffFlag:
        return DiffFlag(self._native.contents.flags)

    @property
    def similarity(self) -> int:
        return self._native.contents.similarity

    @property
    def nfiles(self) -> int:
        return self._native.contents.nfiles

    @cached_property
    def old_file(self) -> DiffFile:
        return DiffFile(self._native.contents.old_file)

    @cached_property
    def new_file(self) -> DiffFile:
        return DiffFile(self._native.contents.new_file)


class DeltasIter(LibraryUser, Iterator):
    _diff: "Diff"

    def __init__(self, diff: "Diff") -> None:
        self._diff = diff
        self._index = 0
        self._num_items = lib.git_diff_num_deltas(diff._native)

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> DiffDelta:
        if self._index < self._num_items:
            native = lib.git_diff_get_delta(self._diff._native, self._index)
            self._index += 1
            return DiffDelta(native, _diff=self._diff)

        raise StopIteration


class DiffStats(WrapperOfWrappings):
    """Represent diff statistics."""

    _libgit2_native_finalizer = "git_diff_stats_free"

    _diff: "Diff"
    _real_native: Optional[git_diff_stats_p] = None

    def __init__(self, diff: "Diff", native: git_diff_stats_p) -> None:
        self._diff = diff
        super().__init__(native=native)

    @property
    def files_changed(self) -> int:
        return lib.git_diff_stats_files_changed(self._native)


class Diff(WrapperOfWrappings):
    """Represent a diff."""

    _repo: "Repository"
    _real_native: Optional[git_diff_p] = None

    def __init__(self, repo: "Repository", native: git_diff_p) -> None:
        self._repo = repo
        super().__init__(native=native)

    @property
    def deltas(self) -> DeltasIter:
        return DeltasIter(diff=self)

    @cached_property
    def stats(self) -> DiffStats:
        native = git_diff_stats_p()
        error_code = lib.git_diff_get_stats(native, self._native)
        self.raise_if_error(error_code, "Can’t get diff stats: {message}")
        return DiffStats(diff=self, native=native)

    @cached_property
    def patch(self) -> str:
        buf = git_buf()
        buf_p = byref(buf)

        error_code = lib.git_diff_to_buf(buf, self._native, git_diff_format_t.PATCH)
        self.raise_if_error(error_code)

        patch_encoded = cast(buf.ptr, c_char_p).value
        patch = patch_encoded.decode(encoding="utf-8", errors="replace")

        lib.git_buf_dispose(buf_p)

        return patch
