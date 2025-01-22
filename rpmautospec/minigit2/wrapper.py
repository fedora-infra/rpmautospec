"""Minimal wrapper for libgit2 - LibraryUser & WrapperOfWrappings"""

import re
from collections import defaultdict
from ctypes import CDLL, _CFuncPtr, _SimpleCData, c_void_p, cast
from ctypes.util import find_library
from functools import cached_property
from typing import Optional, Union
from warnings import warn
from weakref import ref

from .exc import (
    AlreadyExistsError,
    GitError,
    InvalidSpecError,
    Libgit2NotFoundError,
    Libgit2VersionError,
    Libgit2VersionWarning,
)
from .native_adaptation import git_error_code, git_error_t, install_func_decls

LIBGIT2_MIN_VERSION = (1, 1)
LIBGIT2_MAX_VERSION = (1, 9)
LIBGIT2_MIN_VERSION_STR = ".".join(str(x) for x in LIBGIT2_MIN_VERSION)
LIBGIT2_MAX_VERSION_STR = ".".join(str(x) for x in LIBGIT2_MAX_VERSION)


class LibraryUser:
    ERROR_CODE_TO_EXC_CLASS = {
        git_error_code.ENOTFOUND: KeyError,
        git_error_code.EEXISTS: AlreadyExistsError,
        git_error_code.EAMBIGUOUS: ValueError,
        git_error_code.EBUFS: ValueError,
        git_error_code.EINVALIDSPEC: InvalidSpecError,
        git_error_code.PASSTHROUGH: GitError,
        git_error_code.ITEROVER: StopIteration,
    }

    ERROR_T_TO_EXC_CLASS = {
        git_error_t.NOMEMORY: MemoryError,
        git_error_t.OS: OSError,
        git_error_t.INVALID: ValueError,
    }

    _soname: Optional[str] = None
    _library_obj: Optional[CDLL] = None

    @classmethod
    def _get_library(cls) -> CDLL:
        """Discover and load libgit2.

        This caches the loaded library object in the class.

        :return: The loaded library
        """
        if not LibraryUser._library_obj:
            soname = find_library("git2")
            if not soname:
                raise Libgit2NotFoundError("libgit2 not found")
            if not (match := re.match(r"libgit2\.so\.(?P<version>\d+(?:\.\d+)*)", soname)):
                raise Libgit2VersionError(f"Can’t parse libgit2 version: {soname}")
            version = match.group("version")
            version_tuple = tuple(int(x) for x in match.group("version").split("."))
            if LIBGIT2_MIN_VERSION > version_tuple:
                raise Libgit2VersionError(
                    f"Version {version} of libgit2 too low (must be >= {LIBGIT2_MIN_VERSION_STR})"
                )
            if LIBGIT2_MAX_VERSION < version_tuple[: len(LIBGIT2_MAX_VERSION)]:
                warn(
                    f"Version {version} of libgit2 is unknown (latest known is"
                    + f" {LIBGIT2_MAX_VERSION_STR}).",
                    Libgit2VersionWarning,
                )

            LibraryUser._soname = soname
            LibraryUser._library_obj = CDLL(soname)
            install_func_decls(LibraryUser._library_obj)
            LibraryUser._library_obj.git_libgit2_init()

        return LibraryUser._library_obj

    @cached_property
    def _lib(self) -> CDLL:
        """The loaded library."""
        return self._get_library()

    @classmethod
    def raise_if_error(
        cls,
        error_code: int,
        exc_msg_tmpl: Optional[str] = None,
        key: Optional[Union[str, bytes]] = None,
    ) -> None:
        if not error_code:
            return

        exc_class = cls.ERROR_CODE_TO_EXC_CLASS.get(error_code)

        if exc_class is KeyError and key:
            raise KeyError(key)

        error_p = cls._get_library().git_error_last()
        if error_p:
            message = error_p.contents.message.decode("utf-8", errors="replace")

            if not exc_class:
                exc_class = cls.ERROR_T_TO_EXC_CLASS.get(error_p.contents.klass, GitError)
        else:
            message = "(No error information given)"
            exc_class = exc_class or GitError

        if exc_msg_tmpl:
            message = exc_msg_tmpl.format(message=message)

        raise exc_class(message)


class WrapperOfWrappings(LibraryUser):
    """Base class wrapping libgit2 objects."""

    _libgit2_native_finalizer: Optional[Union[_CFuncPtr, str]] = None

    _live_obj_refs: dict[int, ref["WrapperOfWrappings"]] = {}
    _real_native_refcounts: defaultdict[int, int] = defaultdict(int)
    _real_native_must_free: defaultdict[int, bool] = defaultdict(bool)

    _real_native: Optional[_SimpleCData] = None
    _must_free: bool = True

    def __init__(
        self, native: Optional[_SimpleCData] = None, _must_free: Optional[bool] = None
    ) -> None:
        self._live_obj_refs[id(self)] = ref(self)
        if _must_free is not None:
            self._must_free = _must_free
        if native is not None:
            self._native = native

    def __del__(self) -> None:
        del self._native
        self._live_obj_refs.pop(id(self), None)

    def __bool__(self) -> bool:
        return bool(self._real_native)

    @property
    def _native(self) -> Optional[_SimpleCData]:
        return self._real_native

    @_native.setter
    def _native(self, native: _SimpleCData) -> None:
        if self._real_native is not None:
            raise ValueError("_native can’t be changed")

        self._real_native = native

        if self._libgit2_native_finalizer:
            # self._native must be valid pointer
            ptr = cast(native, c_void_p)
            if not ptr:
                raise ValueError("_native must be a valid (non-NULL) pointer")

            self._real_native_refcounts[ptr.value] += 1
            self._real_native_must_free[ptr.value] = (
                self._real_native_must_free[ptr.value] or self._must_free
            )

    @_native.deleter
    def _native(self) -> None:
        native = self._real_native
        if native is None:
            return

        finalizer = self._libgit2_native_finalizer
        if finalizer:
            ptr = cast(native, c_void_p)
            if not ptr.value:
                return

            if ptr.value not in self._real_native_refcounts:
                print(f"{finalizer=} {self._real_native}", file=open("/dev/tty", "w"), flush=True)
                print(
                    f"{ptr!r} {ptr.value=} not in refcounts", file=open("/dev/tty", "w"), flush=True
                )
            assert ptr.value in self._real_native_refcounts

            self._real_native_refcounts[ptr.value] -= 1
            if not self._real_native_refcounts[ptr.value]:
                if self._real_native_must_free[ptr.value]:
                    if isinstance(finalizer, str):
                        type(self)._libgit2_native_finalizer_name = finalizer
                        type(self)._libgit2_native_finalizer = finalizer = getattr(
                            self._lib, finalizer
                        )

                    finalizer(native)

                del self._real_native_must_free[ptr.value]
                del self._real_native_refcounts[ptr.value]

        del self._real_native
