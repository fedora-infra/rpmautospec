"""Minimal wrapper for libgit2 - LibraryUser & WrapperOfWrappings"""

from collections import defaultdict
from ctypes import _CFuncPtr, _SimpleCData, c_void_p, cast
from typing import Optional, Union
from weakref import ref

from .exc import (
    AlreadyExistsError,
    GitError,
    InvalidSpecError,
)
from .native_adaptation import git_error_code, git_error_t, lib


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

    @classmethod
    def raise_if_error(
        cls,
        error_code: int,
        exc_msg_tmpl: Optional[str] = None,
        key: Optional[Union[str, bytes]] = None,
        io: bool = False,
    ) -> None:
        if not error_code:
            return

        exc_class = cls.ERROR_CODE_TO_EXC_CLASS.get(error_code)

        if exc_class is KeyError:
            if io:
                exc_class = IOError
            elif key:
                raise KeyError(key)

        error_p = lib.git_error_last()
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

            assert ptr.value in self._real_native_refcounts

            self._real_native_refcounts[ptr.value] -= 1
            if not self._real_native_refcounts[ptr.value]:
                if self._real_native_must_free[ptr.value]:
                    if isinstance(finalizer, str):
                        type(self)._libgit2_native_finalizer_name = finalizer
                        type(self)._libgit2_native_finalizer = finalizer = getattr(lib, finalizer)

                    finalizer(native)

                del self._real_native_must_free[ptr.value]
                del self._real_native_refcounts[ptr.value]

        del self._real_native
