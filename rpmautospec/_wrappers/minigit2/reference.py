"""Minimal wrapper for libgit2 - Reference"""

from ctypes import byref
from functools import cached_property
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import TYPE_CHECKING, Optional, Type, Union

from .native_adaptation import git_object_p, git_object_t, git_reference_p, git_reference_t, lib
from .object_ import Object
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

    def __eq__(self, other: "Reference") -> bool:
        return (
            isinstance(other, Reference)
            and self._repo is other._repo
            and self.target == other.target
        )

    @cached_property
    def name(self) -> str:
        return lib.git_reference_name(self._native).decode(
            encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
        )

    @property
    def target(self) -> Union[Oid, str]:
        if lib.git_reference_type(self._native) == git_reference_t.DIRECT:
            return Oid(lib.git_reference_target(self._native))

        if not (name := lib.git_reference_symbolic_target(self._native)):
            raise ValueError("no target available")

        return name.decode(encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors())

    def peel(self, target_type: Optional[Union[git_object_t, Type[Object]]] = None) -> Object:
        if not target_type:
            target_type = git_object_t.ANY
        elif isinstance(target_type, type) and issubclass(target_type, Object):
            target_type = target_type._object_t

        peeled = git_object_p()
        error_code = lib.git_reference_peel(peeled, self._native, target_type)
        self.raise_if_error(error_code)

        return Object._from_native(repo=self._repo, native=peeled)

    def resolve(self) -> "Reference":
        if lib.git_reference_type(self._native) == git_reference_t.DIRECT:
            return self

        native = git_reference_p()
        error_code = lib.git_reference_resolve(byref(native), self._native)
        self.raise_if_error(error_code)

        return Reference(repo=self._repo, native=native)

    @cached_property
    def shorthand(self) -> str:
        return lib.git_reference_shorthand(self._native).decode(
            encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
        )
