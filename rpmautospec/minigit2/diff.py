"""Minimal wrapper for libgit2 - Diff & DiffStat"""

from functools import cached_property
from typing import TYPE_CHECKING, Optional

from .native_adaptation import git_diff_p, git_diff_stats_p, lib
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .repository import Repository


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

    @cached_property
    def stats(self) -> DiffStats:
        native = git_diff_stats_p()
        error_code = lib.git_diff_get_stats(native, self._native)
        self.raise_if_error(error_code, "Can’t get diff stats: {message}")
        return DiffStats(diff=self, native=native)
