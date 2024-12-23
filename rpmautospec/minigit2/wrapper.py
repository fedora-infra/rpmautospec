"""Minimal wrapper for libgit2 - High Level Wrappers"""

import re
from collections import defaultdict
from collections.abc import Iterator, Sequence
from ctypes import (
    CDLL,
    _CFuncPtr,
    _SimpleCData,
    byref,
    c_char,
    c_char_p,
    c_uint,
    c_void_p,
    cast,
    memmove,
    sizeof,
)
from ctypes.util import find_library
from functools import cached_property
from pathlib import Path
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import Any, Literal, Optional, Union, overload
from warnings import warn

from .constants import GIT_DIFF_OPTIONS_VERSION, GIT_OID_SHA1_HEXSIZE
from .exc import (
    GitError,
    GitPeelError,
    Libgit2NotFoundError,
    Libgit2VersionError,
    Libgit2VersionWarning,
)
from .native_adaptation import (
    NULL,
    git_blob_p,
    git_buf,
    git_commit_p,
    git_diff_option_t,
    git_diff_options,
    git_diff_p,
    git_diff_stats_p,
    git_error_code,
    git_filemode_t,
    git_index_p,
    git_object_p,
    git_object_t,
    git_oid,
    git_oid_p,
    git_reference_p,
    git_reference_t,
    git_repository_p,
    git_revwalk_p,
    git_signature_p,
    git_sort_t,
    git_tag_p,
    git_tree_entry_p,
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
    _libgit2_native_finalizer: Optional[Union[_CFuncPtr, str]] = None

    _real_native_refcounts: defaultdict[int, int] = defaultdict(int)
    _real_native_must_free: defaultdict[int, bool] = defaultdict(bool)

    _real_native: Optional[_SimpleCData] = None
    _must_free: bool = True

    def __init__(
        self, native: Optional[_SimpleCData] = None, _must_free: Optional[bool] = None
    ) -> None:
        if _must_free is not None:
            self._must_free = _must_free
        if native is not None:
            self._native = native

    def __del__(self) -> None:
        del self._native

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
            self._real_native_refcounts[ptr.value] -= 1
            if (
                not self._real_native_refcounts[ptr.value]
                and self._real_native_must_free[ptr.value]
            ):
                if isinstance(finalizer, str):
                    type(self)._libgit2_native_finalizer_name = finalizer
                    type(self)._libgit2_native_finalizer = finalizer = getattr(self._lib, finalizer)

                finalizer(native)
                del self._real_native_refcounts[ptr.value]
                del self._real_native_must_free[ptr.value]
                del self._real_native

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

    def __str__(self) -> str:
        return self.hex


class Repository(WrapperOfWrappings):
    """Represent a git repository."""

    _libgit2_native_finalizer = "git_repository_free"

    _real_native: Optional[git_repository_p] = None

    def __init__(self, path: Union[str, Path], flags: int = 0) -> None:
        if isinstance(path, Path):
            path = str(path)
        path_c = c_char_p(path.encode("utf-8"))

        self.path = path

        native = git_repository_p()
        error_code = self._lib.git_repository_open_ext(
            native, path_c, c_uint(flags), cast(NULL, c_char_p)
        )
        self.raise_if_error(error_code, "Can’t open repository: {message}")

        super().__init__(native=native)

    def __getitem__(self, oid: OidTypes) -> "Object":
        return Object(repo=self, oid=oid)

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
            except GitError:
                pass
            else:
                break
        else:
            raise TypeError(f'unexpected "{type(_obj)}"')

        return obj

    @property
    def head(self) -> "Reference":
        head_ref_p = git_reference_p()
        error_code = self._lib.git_repository_head(head_ref_p, self._native)
        self.raise_if_error(error_code, "Can’t resolve HEAD: {message}")
        return Reference(repo=self, native=head_ref_p)

    @property
    def index(self) -> "Index":
        index_p = git_index_p()
        error_code = self._lib.git_repository_index(index_p, self._native)
        self.raise_if_error(error_code, "Error getting repository index: {message}")
        return Index(repo=self, native=index_p)

    def revparse_single(self, revision: Union[str, bytes]) -> "Object":
        if isinstance(revision, str):
            revision = revision.encode("utf-8")

        git_object = git_object_p()
        error_code = self._lib.git_revparse_single(git_object, self._native, revision)
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
    ) -> "Diff":
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

    def walk(self, oid: Optional[Oid] = None, sort: git_sort_t = git_sort_t.NONE) -> "RevWalk":
        revwalk = git_revwalk_p()
        error_code = self._lib.git_revwalk_new(revwalk, self._native)
        self.raise_if_error(error_code, "Can’t allocate revwalk: {message}")

        error_code = self._lib.git_revwalk_sorting(revwalk, sort)
        self.raise_if_error(error_code, "Can’t set sorting on revwalk: {message}")

        error_code = self._lib.git_revwalk_push(revwalk, oid._native)
        self.raise_if_error(error_code, "Can’t set revwalk to Oid: {message}")

        return RevWalk(repo=self, native=revwalk)


class Index(WrapperOfWrappings):
    """Represent the git index."""

    _libgit2_native_finalizer = "git_index_free"

    _repo: Repository
    _real_native: Optional[git_index_p]

    def __init__(self, repo: Repository, native: git_index_p) -> None:
        self._repo = repo
        super().__init__(native=native)


class Reference(WrapperOfWrappings):
    """Represent a git reference."""

    _libgit2_native_finalizer = "git_reference_free"

    _repo: Repository
    _real_native: Optional[git_reference_p] = None

    def __init__(self, repo: Repository, native: git_reference_p) -> None:
        self._repo = repo
        super().__init__(native=native)

    @property
    def target(self) -> Union[Oid, str]:
        if self._lib.git_reference_type(self._native) == git_reference_t.DIRECT:
            return Oid(native=self._lib.git_reference_target(self._native))

        if not (name := self._lib.git_reference_symbolic_target(self._native)):
            raise ValueError("no target available")

        return name.value


class DiffStats(WrapperOfWrappings):
    """Represent diff statistics."""

    _libgit2_native_finalizer = "git_diff_stats_free"

    _diff: "Diff"
    _real_native: Optional[git_diff_stats_p] = None

    def __init__(self, diff: "Diff", native: git_diff_stats_p) -> None:
        self._diff = diff
        super().__init__(native=native)

    @property
    def files_changed(self) -> int:
        return self._lib.git_diff_stats_files_changed(self._native)


class Diff(WrapperOfWrappings):
    """Represent a diff."""

    _repo: Repository
    _real_native: Optional[git_diff_p] = None

    def __init__(self, repo: Repository, native: git_diff_p) -> None:
        self._repo = repo
        super().__init__(native=native)

    @cached_property
    def stats(self) -> DiffStats:
        native = git_diff_stats_p()
        error_code = self._lib.git_diff_get_stats(native, self._native)
        self.raise_if_error(error_code, "Can’t get diff stats: {message}")
        return DiffStats(diff=self, native=native)


ObjectTypes = Union[git_object_p, git_commit_p, git_tree_p, git_tag_p, git_blob_p]


class Object(WrapperOfWrappings):
    """Represent a generic git object."""

    _libgit2_native_finalizer = "git_object_free"

    _object_type: _SimpleCData = git_object_p
    _object_t: git_object_t
    _object_t_to_cls: dict[git_object_t, "Object"] = {}

    _repo: Repository
    _real_native: Optional[ObjectTypes] = None

    _initialized: bool = False

    def __init_subclass__(cls):
        if cls._object_t in cls._object_t_to_cls:  # pragma: no cover
            raise TypeError(f"Object type already registered: {cls._object_t.name}")
        cls._object_t_to_cls[cls._object_t] = cls
        super().__init_subclass__()

    def __new__(
        cls,
        repo: Repository,
        *args: tuple[Any],
        native: Optional[ObjectTypes] = None,
        oid: Optional[OidTypes] = None,
        _must_free: Optional[bool] = None,
        _entry: Optional[git_tree_entry_p] = None,
    ) -> "Object":
        if (native is None) == (oid is None):
            raise ValueError("Exactly one of native or oid has to be specified")

        if cls is Object:
            lib = cls._get_library()
            if oid:
                oid = Oid(oid=oid)
                native = git_object_p()
                error_code = lib.git_object_lookup_prefix(
                    native, repo._native, oid._native, len(oid.hexb), git_object_t.ANY
                )
                cls.raise_if_error(error_code, "Can’t lookup object: {message}")

            object_t = lib.git_object_type(cast(native, git_object_p))
            try:
                concrete_cls = cls._object_t_to_cls[object_t]
            except KeyError:  # pragma: no cover
                raise TypeError(f"Unexpected object type: {object_t.name}")

            return concrete_cls(repo=repo, native=native, _must_free=_must_free, _entry=_entry)
        else:
            return super().__new__(cls)

    def __init__(
        self,
        repo: Repository,
        *,
        native: Optional[ObjectTypes] = None,
        oid: Optional[OidTypes] = None,  # processed by .__new__()
        _must_free: Optional[bool] = None,
        _entry: Optional[git_tree_entry_p] = None,
    ) -> None:
        if not self._initialized:
            self._repo = repo
            self._entry = _entry
            self._initialized = True

            super().__init__(native=cast(native, self._object_type), _must_free=_must_free)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(oid={self.short_id!r})"

    def __eq__(self, other: "Object") -> bool:
        return isinstance(other, Object) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id.hex)

    @cached_property
    def id(self) -> Oid:
        return Oid(native=self._lib.git_object_id(cast(self._native, git_object_p)))

    @cached_property
    def short_id(self) -> str:
        buf = git_buf()
        buf_p = byref(buf)
        error_code = self._lib.git_object_short_id(buf_p, cast(self._native, git_object_p))
        self.raise_if_error(error_code, "Error determining short id: {message}")
        return buf.ptr.decode("ascii")

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
        error_code = self._lib.git_object_peel(
            peeled, cast(self._native, git_object_p), target_type
        )
        self.raise_if_error(error_code, "Can’t peel object: {message}", exc_class=GitPeelError)

        return Object(repo=self._repo, native=peeled)

    @cached_property
    def name(self) -> Optional[bytes]:
        if not self._entry:
            return None

        return self._lib.git_tree_entry_name(self._entry).decode(
            encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
        )

    @cached_property
    def filemode(self) -> git_filemode_t:
        if not self._entry:
            return None

        return self._lib.git_tree_entry_filemode(self._entry)


CommitTypes = Union[git_commit_p, Oid, str, bytes]


class Commit(Object):
    """Represent a git commit."""

    _libgit2_native_finalizer = "git_commit_free"

    _object_type = git_commit_p
    _object_t = git_object_t.COMMIT

    _real_native: Optional[git_commit_p] = None

    @cached_property
    def parents(self) -> list["Commit"]:
        n_parents = self._lib.git_commit_parentcount(self._native)
        parents = []
        for n in range(n_parents):
            native = git_commit_p()
            error_code = self._lib.git_commit_parent(native, self._native, n)
            self.raise_if_error(error_code, "Error getting parent: {message}")
            parents.append(Commit(repo=self._repo, native=native))
        return parents

    @cached_property
    def tree(self) -> "Tree":
        native = git_tree_p()
        error_code = self._lib.git_commit_tree(native, self._native)
        self.raise_if_error(error_code, "Error retrieving tree: {message}")
        return Tree(repo=self._repo, native=native)

    @cached_property
    def commit_time(self) -> int:
        return self._lib.git_commit_time(self._native)

    @cached_property
    def commit_time_offset(self) -> int:
        return self._lib.git_commit_time_offset(self._native)

    @cached_property
    def author(self) -> "Signature":
        return Signature(native=self._lib.git_commit_author(self._native), _owner=self)

    @cached_property
    def committer(self) -> "Signature":
        return Signature(native=self._lib.git_commit_committer(self._native), _owner=self)

    @cached_property
    def message_encoding(self) -> Optional[str]:
        encoding = self._lib.git_commit_message_encoding(self._native)
        if encoding:
            encoding = encoding.decode("ascii")
        else:
            encoding = "utf-8"
        return encoding

    @cached_property
    def message(self) -> str:
        message = self._lib.git_commit_message(self._native)
        return message.decode(encoding=self.message_encoding, errors="replace")


class Tree(Object):
    """Represent a git tree."""

    _libgit2_native_finalizer = "git_tree_free"

    _object_type = git_tree_p
    _object_t = git_object_t.TREE

    _real_native: Optional[git_tree_p] = None

    def diff_to_tree(
        self,
        tree: "Tree",
        flags: git_diff_option_t = git_diff_option_t.NORMAL,
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
            a, b = tree._native, self._native
        else:
            a, b = self._native, tree._native

        error_code = self._lib.git_diff_tree_to_tree(diff_p, self._repo._native, a, b, diff_options)
        self.raise_if_error(error_code, "Error diffing tree to tree: {message}")

        return Diff(self._repo, diff_p)

    def diff_to_workdir(
        self,
        flags: git_diff_option_t = git_diff_option_t.NORMAL,
        context_lines: int = 3,
        interhunk_lines: int = 0,
    ) -> Diff:
        diff_options = git_diff_options()
        error_code = self._lib.git_diff_options_init(diff_options, GIT_DIFF_OPTIONS_VERSION)
        self.raise_if_error(error_code, "Can’t initialize diff options: {message}")

        diff_options.flags = flags
        diff_options.context_lines = context_lines
        diff_options.interhunk_lines = interhunk_lines

        diff_p = git_diff_p()

        error_code = self._lib.git_diff_tree_to_workdir(
            diff_p, self._repo._native, self._native, diff_options
        )
        self.raise_if_error(error_code, "Error diffing tree to workdir: {message}")

        return Diff(self._repo, diff_p)

    def _get_tree_entry_for_path(self, path: Union[str, bytes]) -> git_tree_entry_p:
        if isinstance(path, str):
            path = path.encode("utf-8")

        entry = git_tree_entry_p()
        error_code = self._lib.git_tree_entry_bypath(entry, self._native, path)
        if error_code == git_error_code.ENOTFOUND:
            raise KeyError
        self.raise_if_error(error_code, "Error looking up file in tree: {message}")

        return entry

    def __contains__(self, path: Union[str, bytes]) -> bool:
        try:
            entry = self._get_tree_entry_for_path(path)
        except KeyError:
            return False
        else:
            self._lib.git_tree_entry_free(entry)
            return True

    def _object_from_tree_entry(self, entry: git_tree_entry_p) -> Object:
        native = git_object_p()
        error_code = self._lib.git_tree_entry_to_object(native, self._repo._native, entry)
        self.raise_if_error(error_code, "Error accessing object for tree entry: {message}")
        return Object(repo=self._repo, native=native, _entry=entry)

    def __getitem__(self, path: Union[str, bytes]) -> Object:
        return self._object_from_tree_entry(self._get_tree_entry_for_path(path))

    def __len__(self) -> int:
        return self._lib.git_tree_entrycount(self._native)

    def __iter__(self) -> Iterator[Object]:
        for idx in range(len(self)):
            unowned_entry = self._lib.git_tree_entry_byindex(self._native, idx)
            self.raise_if_error(not unowned_entry, "Error looking up tree entry: {message}")

            owned_entry = git_tree_entry_p()
            error_code = self._lib.git_tree_entry_dup(byref(owned_entry), unowned_entry)
            self.raise_if_error(error_code, "Error duplicating tree entry: {message}")

            yield self._object_from_tree_entry(owned_entry)


class Tag(Object):
    """Represent a git tag."""

    _libgit2_native_finalizer = "git_tag_free"

    _object_type = git_tag_p
    _object_t = git_object_t.TAG

    _real_native: Optional[git_tag_p] = None


class Blob(Object):
    """Represent a git blob."""

    _libgit2_native_finalizer = "git_blob_free"

    _object_type = git_blob_p
    _object_t = git_object_t.BLOB

    _real_native: Optional[git_blob_p] = None

    @cached_property
    def data(self) -> bytes:
        rawsize = self._lib.git_blob_rawsize(self._native)
        rawcontent_p = self._lib.git_blob_rawcontent(self._native)
        self.raise_if_error(not rawcontent_p, "Error accessing blob content: {message}")

        buf = (c_char * rawsize)()
        memmove(buf, rawcontent_p, rawsize)
        return bytes(buf)


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


class RevWalk(WrapperOfWrappings, Iterator):
    """Represent a walk over commits in a repository."""

    _libgit2_native_finalizer = "git_revwalk_free"

    _repo: Repository
    _native = Optional[git_revwalk_p]

    def __init__(self, repo: Repository, native: git_revwalk_p) -> None:
        self._repo = repo
        super().__init__(native=native)

    def __iter__(self) -> Iterator[Commit]:
        return self

    def __next__(self) -> Commit:
        oid = git_oid()
        oid_p = byref(oid)

        error_code = self._lib.git_revwalk_next(oid_p, self._native)
        if error_code == git_error_code.ITEROVER:
            raise StopIteration
        self.raise_if_error(error_code, "Can’t find next oid to walk: {message}")

        commit = git_commit_p()
        error_code = self._lib.git_commit_lookup(commit, self._repo._native, oid_p)
        self.raise_if_error(error_code, "Can’t lookup commit for oid: {message}")

        return Commit(repo=self._repo, native=commit)
