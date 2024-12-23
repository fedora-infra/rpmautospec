"""Minimal wrapper for libgit2 - High Level Wrappers"""

import re
from collections.abc import Sequence
from ctypes import (
    CDLL,
    _CFuncPtr,
    _SimpleCData,
    byref,
    c_char,
    c_char_p,
    c_uint,
    cast,
    memmove,
    sizeof,
)
from ctypes.util import find_library
from functools import cached_property
from pathlib import Path
from typing import Any, Literal, Optional, Union, overload
from warnings import warn

from .constants import GIT_DIFF_OPTIONS_VERSION, GIT_OID_SHA1_HEXSIZE
from .exc import GitError, Libgit2NotFoundError, Libgit2VersionError, Libgit2VersionWarning
from .native_adaptation import (
    NULL,
    git_blob_p,
    git_commit_p,
    git_diff_option_t,
    git_diff_options,
    git_diff_p,
    git_index_p,
    git_object_p,
    git_object_t,
    git_oid,
    git_reference_p,
    git_reference_t,
    git_repository_p,
    git_tag_p,
    git_tree_p,
    install_func_decls,
)

LIBGIT2_MIN_VERSION = (1, 1)
LIBGIT2_MAX_VERSION = (1, 8)
LIBGIT2_MIN_VERSION_STR = ".".join(str(x) for x in LIBGIT2_MIN_VERSION)
LIBGIT2_MAX_VERSION_STR = ".".join(str(x) for x in LIBGIT2_MAX_VERSION)


class WrapperOfWrappings:
    """Base class wrapping pieces of libgit2."""

    _soname: Optional[str] = None
    _libgit2: Optional[CDLL] = None
    _libgit2_obj_destructor: Optional[Union[_CFuncPtr, str]] = None

    _obj: Optional[Any] = None

    def __del__(self) -> None:
        if self._libgit2_obj_destructor and self._obj:
            cls = type(self)
            if isinstance(cls._libgit2_obj_destructor, str):
                cls._libgit2_obj_destructor = getattr(self._lib, cls._libgit2_obj_destructor)
            cls._libgit2_obj_destructor(self._obj)
            self._obj = None

    @classmethod
    def _get_library(cls) -> CDLL:
        """Discover and load libgit2.

        This caches the loaded library object in the class.

        :return: The loaded library
        """
        if not WrapperOfWrappings._libgit2:
            soname = find_library("git2")
            if not soname:
                raise Libgit2NotFoundError("libgit2 not found")
            if not (match := re.match(r"libgit2\.so\.(?P<version>\d+(?:\.\d+)*)", soname)):
                raise Libgit2VersionError(f"Can’t parse libgit2 version: {soname}")
            version = match.group("version")
            version_tuple = tuple(int(x) for x in match.group("version").split("."))
            if LIBGIT2_MIN_VERSION > version_tuple[: len(LIBGIT2_MIN_VERSION)]:
                raise Libgit2VersionError(
                    f"Version {version} of libgit2 too low (must be >= {LIBGIT2_MIN_VERSION_STR})"
                )
            if LIBGIT2_MAX_VERSION < version_tuple[: len(LIBGIT2_MAX_VERSION)]:
                warn(
                    f"Version {version} of libgit2 unknown (latest known is"
                    + f" {LIBGIT2_MIN_VERSION_STR}.)",
                    Libgit2VersionWarning,
                )

            WrapperOfWrappings._soname = soname
            WrapperOfWrappings._libgit2 = CDLL(soname)
            install_func_decls(WrapperOfWrappings._libgit2)
            WrapperOfWrappings._libgit2.git_libgit2_init()

        return WrapperOfWrappings._libgit2

    @cached_property
    def _lib(self) -> CDLL:
        """The loaded library."""
        return self._get_library()

    @classmethod
    def raise_if_error(
        cls, error_code: int, exc_msg_tmpl: Optional[str] = None, exc_class: Exception = GitError
    ) -> None:
        if not error_code:
            return

        error_p = cls._get_library().git_error_last()
        message = error_p.contents.message.decode("utf-8", errors="replace")
        if exc_msg_tmpl:
            message = exc_msg_tmpl.format(message=message)
        raise exc_class(message)


OidTypes = Union["Oid", str, bytes]


class Oid(WrapperOfWrappings):
    """Represent a git oid."""

    _obj: Optional[git_oid] = None

    def __init__(self, *, native: Optional[git_oid] = None, oid: Optional[OidTypes] = None) -> None:
        if bool(native) is bool(oid):
            raise ValueError("Exactly one of native or oid has to be specified")

        if native:
            src = byref(native)
            native = git_oid()
            dst = byref(native)
            memmove(dst, src, sizeof(git_oid))
        else:
            assert oid
            if isinstance(oid, Oid):
                native = oid._obj
            else:
                if isinstance(oid, str):
                    oid = oid.encode("ascii")
                native = git_oid()
                error_code = self._lib.git_oid_fromstrn(native, oid, len(oid))
                self.raise_if_error(error_code, "Error creating Oid: {message}")

        self._obj = native

    @cached_property
    def hex(self) -> str:
        return str(self)

    @cached_property
    def hexb(self) -> bytes:
        return self.hex.encode("ascii")

    def __str__(self) -> str:
        buf = (c_char * GIT_OID_SHA1_HEXSIZE)()
        error_code = self._lib.git_oid_fmt(buf, self._obj)
        self.raise_if_error(error_code, "Can’t format OID: {message}")
        return buf.value.decode("ascii")


class Repository(WrapperOfWrappings):
    """Represent a git repository."""

    _libgit2_obj_destructor = "git_repository_free"

    _obj: Optional[git_repository_p] = None

    def __init__(self, path: Union[str, Path], flags: int = 0) -> None:
        if isinstance(path, Path):
            path = str(path)
        path_c = c_char_p(path.encode("utf-8"))

        self._obj = git_repository_p()

        error_code = self._lib.git_repository_open_ext(
            self._obj, path_c, c_uint(flags), cast(NULL, c_char_p)
        )

        self.raise_if_error(error_code, "Can’t open repository: {message}")

    def __getitem__(self, oid: OidTypes) -> "Object":
        obj = Object(repo=self, oid=oid)
        wrapped = obj.wrap()
        raise RuntimeError
        return Object(repo=self, oid=oid).wrap()

    def _coerce_to_object_and_peel(
        self,
        obj: Optional[Union["Object", str, bytes, Oid]],
        peel_types: Sequence[git_object_t] = (git_object_t.BLOB, git_object_t.TREE),
    ) -> Optional["Object"]:
        if obj is None:
            return

        _obj = obj

        if isinstance(obj, (str, bytes)):
            obj = self.revparse_single(obj)
        elif isinstance(obj, Oid):
            obj = self[obj]

        for peel_type in peel_types:
            try:
                obj = obj.peel(target_type=peel_type)
            except Exception:
                pass
            else:
                break
        else:
            raise TypeError(f'unexpected "{type(_obj)}"')

        return obj.wrap()

    @property
    def head(self) -> "Reference":
        head_ref_p = git_reference_p()
        error_code = self._lib.git_repository_head(head_ref_p, self._obj)
        self.raise_if_error(error_code, "Can’t resolve HEAD: {message}")
        return Reference(repo=self, native=head_ref_p)

    @property
    def index(self) -> "Index":
        index_p = git_index_p()
        error_code = self._lib.git_repository_index(index_p, self._obj)
        self.raise_if_error(error_code, "Error getting repository index: {message}")
        return Index(repo=self, native=index_p)

    def revparse_single(self, revision: Union[str, bytes]) -> "Object":
        if isinstance(revision, str):
            revision = revision.encode("utf-8")

        git_object = git_object_p()
        error_code = self._lib.git_revparse_single(git_object, self._obj, revision)
        self.raise_if_error(error_code, "Error parsing revision: {message}")
        return Object(repo=self, native=git_object)

    def diff(
        self,
        a: Optional[Union["Commit", "Reference"]] = None,
        b: Optional[Union["Commit", "Reference"]] = None,
        cached: bool = False,
        flags: git_diff_option_t = git_diff_option_t.NORMAL,
        context_lines: int = 3,
        interhunk_lines: int = 0,
    ) -> ...:
        a = self._coerce_to_object_and_peel(a)
        b = self._coerce_to_object_and_peel(b)

        opts = {
            "flags": int(flags),
            "context_lines": context_lines,
            "interhunk_lines": interhunk_lines,
        }

        if isinstance(a, Tree) and isinstance(b, Tree):
            return a.diff_to_tree(b, **opts)
        elif a is None and b is None:
            return self.index.diff_to_workdir(*opts.values())
        elif isinstance(a, Tree) and b is None:
            if cached:
                return a.diff_to_index(self.index, *opts.values())
            else:
                return a.diff_to_workdir(*opts.values())
        elif isinstance(a, Blob) and isinstance(b, Blob):
            return a.diff(b)

        raise ValueError("Only blobs and treeish can be diffed")


class Index(WrapperOfWrappings):
    """Represent the git index."""

    _libgit2_obj_destructor = "git_index_free"

    _repo: Repository
    _obj: Optional[git_index_p]

    def __init__(self, repo: Repository, native: git_index_p) -> None:
        self._repo = repo
        self._obj = native


class Reference(WrapperOfWrappings):
    """Represent a git reference."""

    _libgit2_obj_destructor = "git_reference_free"

    _repo: Repository
    _obj: Optional[git_reference_p] = None

    def __init__(self, repo: Repository, native: git_reference_p) -> None:
        self._repo = repo
        self._obj = native

    @property
    def target(self) -> Union[Oid, str]:
        if self._lib.git_reference_type(self._obj) == git_reference_t.DIRECT:
            return Oid(native=self._lib.git_reference_target(self._obj).contents)

        if not (name := self._lib.git_reference_symbolic_target(self._obj)):
            raise ValueError("no target available")

        return name.value


class Diff(WrapperOfWrappings):
    """Represent a diff."""

    _object_type = git_diff_p

    _obj: Optional[git_diff_p] = None

    def __init__(self, repo: Repository, native: git_diff_p) -> None:
        self._repo = repo
        self._obj = native


ObjectTypes = Union[git_object_p, git_commit_p, git_tree_p, git_tag_p, git_blob_p]


class Object(WrapperOfWrappings):
    """Represent a generic git object."""

    _libgit2_obj_destructor = "git_object_free"

    _object_type: _SimpleCData = git_object_p
    _object_t: git_object_t
    _object_t_to_cls: dict[git_object_t, "Object"] = {}

    _repo: Repository
    _obj: Optional[ObjectTypes] = None
    _delegate: Optional["Object"] = None

    def __init_subclass__(cls):
        if not hasattr(cls, "_libgit2_obj_destructor"):
            cls._libgit2_obj_destructor = None
        if cls._object_t in cls._object_t_to_cls:  # pragma: no cover
            raise TypeError(f"Object type already registered: {cls._object_t.name}")
        cls._object_t_to_cls[cls._object_t] = cls
        super().__init_subclass__()

    def __init__(
        self,
        repo: Repository,
        *,
        native: Optional[ObjectTypes] = None,
        oid: Optional[OidTypes] = None,
        _delegate: Optional["Object"] = None,
    ) -> None:
        if bool(native) is bool(oid):
            raise ValueError("Exactly one of native or oid has to be specified")

        if oid:
            oid = Oid(oid=oid)
            native = self._object_type()
            error_code = self._lib.git_object_lookup_prefix(
                native, repo._obj, oid._obj, len(oid.hexb), git_object_t.ANY
            )
            self.raise_if_error(error_code, "Can’t lookup object: {message}")

        self._repo = repo
        self._obj = cast(native, self._object_type)
        self._delegate = _delegate

    def __del__(self) -> None:
        if not self._delegate:
            super().__del__()

    @cached_property
    def oid(self):
        return Oid(native=self._lib.git_object_id(cast(self._obj, git_object_p)))

    def wrap(self) -> "Object":
        object_t = self._lib.git_object_type(cast(self._obj, git_object_p))
        try:
            concrete_class = self._object_t_to_cls[object_t]
        except KeyError:  # pragma: no cover
            raise TypeError(f"unexpected object type: {object_t.name}")
        return concrete_class(repo=self._repo, native=self._obj, _delegate=self._delegate or self)

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

    def peel(self, target_type: Optional[git_object_t]) -> "Union[Commit, Tree, Tag, Blob]":
        if not target_type:
            target_type = git_object_t.ANY

        peeled = git_object_p()
        error_code = self._lib.git_object_peel(peeled, cast(self._obj, git_object_p), target_type)
        self.raise_if_error(error_code)

        return Object(repo=self, native=peeled).wrap()


CommitTypes = Union[git_commit_p, Oid, str, bytes]


class Commit(Object):
    """Represent a git commit."""

    _object_type = git_commit_p
    _object_t = git_object_t.COMMIT

    _obj: Optional[git_commit_p] = None


class Tree(Object):
    """Represent a git tree."""

    _object_type = git_tree_p
    _object_t = git_object_t.TREE

    _obj: Optional[git_tree_p] = None

    def diff_to_tree(
        self,
        tree: "Tree",
        flags: git_diff_option_t.NORMAL,
        context_lines: int = 3,
        interhunk_lines: int = 0,
        swap: bool = False,
    ) -> Diff:
        diff_options = git_diff_options()
        error_code = self._lib.git_diff_options_init(diff_options, GIT_DIFF_OPTIONS_VERSION)
        self.raise_if_error(error_code, "Can’t initialize diff options: {message}")

        diff_options.flags = flags
        diff_options.context_lines = context_lines
        diff_options.interhunk_lines = interhunk_lines

        diff_p = git_diff_p()

        if swap:
            a, b = tree._obj, self._obj
        else:
            a, b = self._obj, tree._obj

        error_code = self._lib.git_diff_tree_to_tree(diff_p, self._repo, a, b, diff_options)
        self.raise_if_error(error_code, "Error diffing tree to tree: {message}")

        return Diff(self._repo, diff_p)


class Tag(Object):
    """Represent a git tag."""

    _object_type = git_tag_p
    _object_t = git_object_t.TAG

    _obj: Optional[git_tag_p] = None


class Blob(Object):
    """Represent a git blob."""

    _object_type = git_blob_p
    _object_t = git_object_t.BLOB

    _obj: Optional[git_blob_p] = None
