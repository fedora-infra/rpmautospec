"""Minimal wrapper for libgit2 - High Level Wrappers"""

from ctypes import byref, c_char, memmove, sizeof
from functools import cached_property
from typing import Optional, Union

from .constants import GIT_OID_SHA1_HEXSIZE
from .native_adaptation import git_oid, git_oid_p
from .wrapper import WrapperOfWrappings

OidTypes = Union["Oid", str, bytes]


class Oid(WrapperOfWrappings):
    """Represent a git oid."""

    _real_native: Optional[git_oid] = None

    def __init__(
        self, *, native: Optional[git_oid_p] = None, oid: Optional[OidTypes] = None
    ) -> None:
        if (native is None) == (oid is None):
            raise ValueError("Exactly one of native or oid has to be specified")

        if native:
            src = native
            native = git_oid()
            dst = byref(native)
            memmove(dst, src, sizeof(git_oid))
        else:
            assert oid
            if isinstance(oid, Oid):
                native = oid._native
            else:
                if isinstance(oid, str):
                    oid = oid.encode("ascii")
                native = git_oid()
                error_code = self._lib.git_oid_fromstrp(native, oid)
                self.raise_if_error(error_code, "Error creating Oid: {message}")

        super().__init__(native=native)

    def __eq__(self, other: "Oid") -> bool:
        return self._native.id == other._native.id

    @cached_property
    def hexb(self) -> bytes:
        buf = (c_char * GIT_OID_SHA1_HEXSIZE)()
        error_code = self._lib.git_oid_fmt(buf, self._native)
        self.raise_if_error(error_code, "Can’t format Oid: {message}")
        return buf.value

    @cached_property
    def hex(self) -> str:
        return self.hexb.decode("ascii")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(oid={self.hex!r})"

    def __str__(self) -> str:
        return self.hex
