"""Minimal wrapper for libgit2 - Signature"""

from ctypes import byref
from functools import cached_property
from typing import TYPE_CHECKING, Optional, Union

from .native_adaptation import git_signature_p, lib
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .commit import Commit


class Signature(WrapperOfWrappings):
    """Represents an action signature."""

    _libgit2_native_finalizer = "git_signature_free"

    _real_native: Optional[git_signature_p] = None

    _init_encoding: Optional[str] = None

    def __init__(
        self,
        name: Union[str, bytes],
        email: Union[str, bytes],
        time: Optional[int] = None,
        offset: Optional[int] = 0,
        encoding: Optional[str] = None,
    ) -> None:
        self._owner = None
        self._init_encoding = encoding

        if isinstance(name, str):
            name = name.encode(encoding=encoding or "utf-8")
        if isinstance(email, str):
            email = email.encode(encoding=encoding or "utf-8")

        native = git_signature_p()
        if time is None:
            error_code = lib.git_signature_now(byref(native), name, email)
        else:
            error_code = lib.git_signature_new(byref(native), name, email, time, offset)
        self.raise_if_error(error_code)

        super().__init__(native=native)

    @classmethod
    def _from_native(
        cls, native: git_signature_p, _owner: Optional["Commit"] = None
    ) -> "Signature":
        self = cls.__new__(Signature)
        self._owner = _owner
        super(Signature, self).__init__(native=native, _must_free=not _owner)
        return self

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(name={self.name!r}, email={self.email!r}, time={self.time!r},"
            + f" offset={self.offset!r}, encoding={self.encoding!r})"
        )

    @cached_property
    def encoding(self) -> str:
        if self._init_encoding:
            return self._init_encoding

        if self._owner:
            try:
                return self._owner.message_encoding or "utf-8"
            except AttributeError:
                pass

        return "utf-8"

    @cached_property
    def name(self) -> str:
        return self._native.contents.name.decode(encoding=self.encoding, errors="replace")

    @cached_property
    def email(self) -> str:
        return self._native.contents.email.decode(encoding=self.encoding, errors="replace")

    @property
    def time(self) -> int:
        return self._native.contents.when.time

    @property
    def offset(self) -> int:
        return self._native.contents.when.offset
