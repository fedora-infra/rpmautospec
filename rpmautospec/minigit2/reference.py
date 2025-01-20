"""Minimal wrapper for libgit2 - Reference"""

from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import TYPE_CHECKING, Optional, Union

from .native_adaptation import git_reference_p, git_reference_t
from .oid import Oid
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .repository import Repository


class Reference(WrapperOfWrappings):
    """Represent a git reference."""

    _libgit2_native_finalizer = "git_reference_free"

    _repo: "Repository"
    _real_native: Optional[git_reference_p] = None

    def __init__(self, repo: "Repository", native: git_reference_p) -> None:
        self._repo = repo
        super().__init__(native=native)

    @property
    def target(self) -> Union[Oid, str]:
        if self._lib.git_reference_type(self._native) == git_reference_t.DIRECT:
            return Oid(native=self._lib.git_reference_target(self._native))

        if not (name := self._lib.git_reference_symbolic_target(self._native)):
            raise ValueError("no target available")

        return name.decode(encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors())
