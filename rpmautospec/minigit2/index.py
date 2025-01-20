"""Minimal wrapper for libgit2 - Index"""

from typing import TYPE_CHECKING, Optional

from .native_adaptation import git_index_p
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
