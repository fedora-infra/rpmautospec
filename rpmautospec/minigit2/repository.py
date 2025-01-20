"""Minimal wrapper for libgit2 - Repository"""

from collections.abc import Sequence
from ctypes import c_char_p, c_uint
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from .blob import Blob
from .exc import InvalidSpecError
from .index import Index
from .native_adaptation import (
    git_diff_option_t,
    git_index_p,
    git_object_p,
    git_object_t,
    git_reference_p,
    git_repository_p,
    git_revwalk_p,
    git_sort_t,
)
from .object_ import Object
from .oid import Oid, OidTypes
from .reference import Reference
from .revwalk import RevWalk
from .tree import Tree
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .commit import Commit
    from .diff import Diff


class Repository(WrapperOfWrappings):
    """Represent a git repository."""

    _libgit2_native_finalizer = "git_repository_free"

    _real_native: Optional[git_repository_p] = None

    def __init__(
        self, path: Union[str, Path], flags: int = 0, native: Optional[git_repository_p] = None
    ) -> None:
        if isinstance(path, Path):
            path = str(path)
        path_c = c_char_p(path.encode("utf-8"))

        self.path = path

        if not native:
            native = git_repository_p()
            error_code = self._lib.git_repository_open_ext(
                native, path_c, c_uint(flags), c_char_p()
            )
            self.raise_if_error(error_code, "Can’t open repository: {message}")

        super().__init__(native=native)

    @classmethod
    def init_repository(
        cls, path: Union[str, Path], initial_head: Optional[str] = None
    ) -> "Repository":
        # Currently, this is only used in tests, so implements only the bare minimum.
        if isinstance(path, Path):
            path = str(path)
        path_c = c_char_p(path.encode("utf-8"))

        native = git_repository_p()
        error_code = cls._get_library().git_repository_init(native, path_c, False)
        cls.raise_if_error(error_code)

        return cls(path=path, native=native)

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
            except InvalidSpecError:
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
