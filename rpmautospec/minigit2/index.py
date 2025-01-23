"""Minimal wrapper for libgit2 - Index"""

from typing import TYPE_CHECKING, Optional

from .constants import GIT_DIFF_OPTIONS_VERSION
from .diff import Diff
from .native_adaptation import git_diff_option_t, git_diff_options, git_diff_p, git_index_p, lib
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
