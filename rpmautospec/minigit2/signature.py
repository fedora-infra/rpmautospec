"""Minimal wrapper for libgit2 - Signature"""

from functools import cached_property
from typing import TYPE_CHECKING, Optional

from .native_adaptation import git_signature_p
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .commit import Commit


class Signature(WrapperOfWrappings):
    """Represents an action signature."""

    _libgit2_native_finalizer = "git_signature_free"

    _real_native: Optional[git_signature_p] = None

    def __init__(self, native: git_signature_p, _owner: Optional["Commit"] = None) -> None:
        self._owner = _owner
        super().__init__(native=native, _must_free=not _owner)

    @cached_property
    def _encoding(self) -> str:
        if self._owner:
            return self._owner.message_encoding
        else:
            return "utf-8"

    @cached_property
    def name(self) -> str:
        return self._native.contents.name.decode(encoding=self._encoding, errors="replace")

    @cached_property
    def email(self) -> str:
        return self._native.contents.email.decode(encoding=self._encoding, errors="replace")
