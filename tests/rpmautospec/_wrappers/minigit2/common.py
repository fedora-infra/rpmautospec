from ctypes import c_void_p
from typing import Type
from unittest import mock

from rpmautospec._wrappers.minigit2.wrapper import WrapperOfWrappings


class BaseTestWrapper:
    cls: Type[WrapperOfWrappings]

    def test___init__(self) -> None:
        repo = object()
        native = c_void_p(1)

        with mock.patch.object(self.cls, "_libgit2_native_finalizer"):
            self.cls._libgit2_native_finalizer = None
            obj = self.cls(repo=repo, native=native)

        # Tidy up for ref-counting
        obj._libgit2_native_finalizer = None

        assert obj._repo is repo
        assert obj._real_native is native
        assert native.value not in self.cls._real_native_refcounts
