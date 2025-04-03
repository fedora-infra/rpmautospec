"""Minimal wrapper for libgit2 - Oid"""

from ctypes import byref, c_char, memmove, sizeof
from functools import cached_property
from typing import Optional, Union

from .constants import GIT_OID_SHA1_HEXSIZE
from .native_adaptation import git_oid, git_oid_p, lib
from .wrapper import WrapperOfWrappings

OidTypes = Union["Oid", str, bytes]


class Oid(WrapperOfWrappings):
    """Represent a git oid."""

    _real_native: Optional[git_oid] = None

    def __init__(self, native: Union[git_oid, git_oid_p]) -> None:
        if isinstance(native, git_oid_p):
            src = native
            native = git_oid()
            dst = byref(native)
            memmove(dst, src, sizeof(git_oid))

        super().__init__(native=native)

    @classmethod
    def _from_oid(cls, oid: OidTypes) -> "Oid":
        if isinstance(oid, Oid):
            native = oid._native
        else:
            if isinstance(oid, str):
                oid = oid.encode("ascii")
            native = git_oid()
            error_code = lib.git_oid_fromstrp(native, oid)
            cls.raise_if_error(error_code, "Error creating Oid: {message}")

        return Oid(native)

    def __eq__(self, other: Union["Oid", str, bytes]) -> bool:
        if isinstance(other, Oid):
            return self._native.id == other._native.id
        elif isinstance(other, str):
            return self.hex == other
        else:  # isinstance(other, bytes)
            return self.hexb == other

    @cached_property
    def hexb(self) -> bytes:
        buf = (c_char * GIT_OID_SHA1_HEXSIZE)()
        error_code = lib.git_oid_fmt(buf, self._native)
        self.raise_if_error(error_code, "Can’t format Oid: {message}")
        return buf.value

    @cached_property
    def hex(self) -> str:
        return self.hexb.decode("ascii")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}._from_oid({self.hex!r})"

    def __str__(self) -> str:
        return self.hex
