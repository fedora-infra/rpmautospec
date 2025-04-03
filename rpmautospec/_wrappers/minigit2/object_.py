"""Minimal wrapper for libgit2 - Object"""

from ctypes import _SimpleCData, byref, c_char_p, cast
from functools import cached_property
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import TYPE_CHECKING, Literal, Optional, Type, Union, overload

from .native_adaptation import (
    git_blob_p,
    git_buf,
    git_commit_p,
    git_filemode_t,
    git_object_p,
    git_object_t,
    git_tag_p,
    git_tree_entry_p,
    git_tree_p,
    lib,
)
from .oid import Oid, OidTypes
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .blob import Blob
    from .commit import Commit
    from .repository import Repository
    from .tag import Tag
    from .tree import Tree

ObjectTypes = Union[git_object_p, git_commit_p, git_tree_p, git_tag_p, git_blob_p]


class Object(WrapperOfWrappings):
    """Represent a generic git object."""

    _libgit2_native_finalizer = "git_object_free"

    _object_type: _SimpleCData = git_object_p
    _object_t: git_object_t
    _object_t_to_cls: dict[git_object_t, "Object"] = {}

    _repo: "Repository"
    _real_native: Optional[ObjectTypes] = None

    _initialized: bool = False

    def __init_subclass__(cls):
        if cls._object_t in cls._object_t_to_cls:  # pragma: no cover
            raise TypeError(f"Object type already registered: {cls._object_t.name}")
        cls._object_t_to_cls[cls._object_t] = cls
        super().__init_subclass__()

    def __init__(
        self,
        *,
        _repo: "Repository",
        _native: ObjectTypes,
        _must_free: Optional[bool] = None,
        _entry: Optional[git_tree_entry_p] = None,
    ) -> None:
        self._repo = _repo
        self._entry = _entry
        super().__init__(native=cast(_native, self._object_type), _must_free=_must_free)

    @classmethod
    def _from_native(
        cls,
        repo: "Repository",
        native: ObjectTypes,
        *,
        _must_free: Optional[bool] = None,
        _entry: Optional[git_tree_entry_p] = None,
    ) -> "Object":
        object_t = lib.git_object_type(cast(native, git_object_p))
        try:
            concrete_cls = cls._object_t_to_cls[object_t]
        except KeyError:  # pragma: no cover
            raise TypeError(f"Unexpected object type: {object_t.name}")

        return concrete_cls(_repo=repo, _native=native, _must_free=_must_free, _entry=_entry)

    @classmethod
    def _from_oid(
        cls, repo: "Repository", oid: OidTypes, *, _must_free: Optional[bool] = None
    ) -> "Object":
        oid = Oid._from_oid(oid)
        native = git_object_p()
        error_code = lib.git_object_lookup_prefix(
            native, repo._native, oid._native, len(oid.hexb), git_object_t.ANY
        )
        cls.raise_if_error(error_code, "Can’t lookup object: {message}")

        return cls._from_native(repo=repo, native=native, _must_free=_must_free)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(oid={self.id.hex!r})"

    def __eq__(self, other: "Object") -> bool:
        return isinstance(other, Object) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id.hex)

    @cached_property
    def id(self) -> Oid:
        return Oid(lib.git_object_id(cast(self._native, git_object_p)))

    @cached_property
    def short_id(self) -> str:
        buf = git_buf()
        buf_p = byref(buf)
        error_code = lib.git_object_short_id(buf_p, cast(self._native, git_object_p))
        self.raise_if_error(error_code, "Error determining short id: {message}")
        short_id = cast(buf.ptr, c_char_p).value.decode("ascii")
        lib.git_buf_dispose(buf_p)
        return short_id

    @overload
    def peel(self, target_type: Literal[git_object_t.COMMIT]) -> "Commit": ...

    @overload
    def peel(self, target_type: Literal[git_object_t.TREE]) -> "Tree": ...

    @overload
    def peel(self, target_type: Literal[git_object_t.TAG]) -> "Tag": ...

    @overload
    def peel(self, target_type: Literal[git_object_t.BLOB]) -> "Blob": ...

    @overload
    def peel(self, target_type: None) -> "Union[Commit, Tree, Blob]": ...

    def peel(
        self, target_type: Optional[Union[git_object_t, Type["Object"]]] = None
    ) -> "Union[Commit, Tree, Tag, Blob]":
        if not target_type:
            target_type = git_object_t.ANY
        elif isinstance(target_type, type) and issubclass(target_type, Object):
            target_type = target_type._object_t

        peeled = git_object_p()
        error_code = lib.git_object_peel(peeled, cast(self._native, git_object_p), target_type)
        self.raise_if_error(error_code)

        return Object._from_native(repo=self._repo, native=peeled)

    @cached_property
    def name(self) -> Optional[bytes]:
        if not self._entry:
            return None

        return lib.git_tree_entry_name(self._entry).decode(
            encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
        )

    @cached_property
    def filemode(self) -> git_filemode_t:
        if not self._entry:
            return None

        return lib.git_tree_entry_filemode(self._entry)
