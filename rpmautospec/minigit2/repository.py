"""Minimal wrapper for libgit2 - Repository"""

from collections.abc import Sequence
from ctypes import byref, c_char_p, c_uint, cast
from functools import cached_property
from os import PathLike, fspath
from pathlib import Path
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import TYPE_CHECKING, Any, Literal, Optional, Union

from .blob import Blob
from .branch import Branch
from .commit import Commit
from .config import Config
from .constants import (
    GIT_CHECKOUT_OPTIONS_VERSION,
    GIT_REPOSITORY_INIT_OPTIONS_VERSION,
    GIT_STATUS_OPT_DEFAULTS,
    GIT_STATUS_OPTIONS_VERSION,
)
from .exc import GitError, InvalidSpecError
from .index import Index
from .native_adaptation import (
    git_checkout_options,
    git_checkout_strategy_t,
    git_commit_p,
    git_config_p,
    git_diff_option_t,
    git_error_code,
    git_index_p,
    git_object_p,
    git_object_t,
    git_oid,
    git_reference_p,
    git_repository_init_flag_t,
    git_repository_init_options,
    git_repository_p,
    git_revwalk_p,
    git_signature_p,
    git_sort_t,
    git_status_list_p,
    git_status_opt_t,
    git_status_options,
    git_status_t,
    lib,
)
from .object_ import Object
from .oid import Oid, OidTypes
from .reference import Reference
from .revwalk import RevWalk
from .signature import Signature
from .tree import Tree
from .wrapper import WrapperOfWrappings

if TYPE_CHECKING:
    from .diff import Diff


class Repository(WrapperOfWrappings):
    """Represent a git repository."""

    _libgit2_native_finalizer = "git_repository_free"

    _real_native: Optional[git_repository_p] = None

    def __init__(self, path: Union[str, Path], flags: int = 0) -> None:
        if isinstance(path, Path):
            path = str(path)
        path_c = c_char_p(path.encode("utf-8"))

        native = git_repository_p()
        error_code = lib.git_repository_open_ext(native, path_c, c_uint(flags), c_char_p())
        if error_code == git_error_code.ENOTFOUND:
            raise GitError(f"Repository not found at {path}")
        self.raise_if_error(error_code)

        super().__init__(native=native)

    @classmethod
    def _from_native(cls, native: git_repository_p) -> "Repository":
        self = cls.__new__(cls)
        super(Repository, self).__init__(native=native)
        return self

    def __repr__(self) -> str:
        return f"{type(self).__name__}(path={self.path!r})"

    @classmethod
    def init_repository(
        cls,
        path: Union[str, Path],
        *,
        flags: git_repository_init_flag_t = git_repository_init_flag_t.MKPATH,
        initial_head: Optional[str] = None,
    ) -> "Repository":
        # Currently, this is only used in tests, so implements only the bare minimum.
        if isinstance(path, Path):
            path = str(path)
        path_bytes = path.encode(
            encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
        )

        options = git_repository_init_options()
        error_code = lib.git_repository_init_options_init(
            byref(options), GIT_REPOSITORY_INIT_OPTIONS_VERSION
        )
        cls.raise_if_error(error_code)

        options.flags = flags

        if initial_head:
            initial_head_bytes = initial_head.encode(
                encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
            )
            options.initial_head = initial_head_bytes

        native = git_repository_p()
        error_code = lib.git_repository_init_ext(native, path_bytes, byref(options))
        cls.raise_if_error(error_code)

        return cls._from_native(native)

    @cached_property
    def path(self) -> str:
        return lib.git_repository_path(self._native).decode(
            encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
        )

    @cached_property
    def workdir(self) -> Optional[str]:
        encoded = lib.git_repository_workdir(self._native)
        if not encoded:
            return None
        return encoded.decode(encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors())

    def __getitem__(self, oid: OidTypes) -> "Object":
        return Object._from_oid(repo=self, oid=oid)

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
        error_code = lib.git_repository_head(head_ref_p, self._native)
        self.raise_if_error(error_code, "Can’t resolve HEAD: {message}")
        return Reference(repo=self, native=head_ref_p)

    @property
    def index(self) -> "Index":
        index_p = git_index_p()
        error_code = lib.git_repository_index(index_p, self._native)
        self.raise_if_error(error_code, "Error getting repository index: {message}")
        return Index(repo=self, native=index_p)

    def revparse_single(self, revision: Union[str, bytes]) -> "Object":
        if isinstance(revision, str):
            revision = revision.encode("utf-8")

        git_object = git_object_p()
        error_code = lib.git_revparse_single(git_object, self._native, revision)
        self.raise_if_error(error_code, "Error parsing revision: {message}")
        return Object._from_native(repo=self, native=git_object)

    def diff(
        self,
        a: Optional[Union[Commit, "Reference"]] = None,
        b: Optional[Union[Commit, "Reference"]] = None,
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
        elif isinstance(a, Blob) and isinstance(b, Blob):  # pragma: no cover
            # return a.diff(b)
            raise NotImplementedError

        raise ValueError("Only blobs and treeish can be diffed")

    def walk(self, oid: Optional[Oid], sort: git_sort_t = git_sort_t.NONE) -> "RevWalk":
        revwalk = git_revwalk_p()
        error_code = lib.git_revwalk_new(revwalk, self._native)
        self.raise_if_error(error_code, "Can’t allocate revwalk: {message}")

        error_code = lib.git_revwalk_sorting(revwalk, sort)
        self.raise_if_error(error_code, "Can’t set sorting on revwalk: {message}")

        if oid is not None:
            error_code = lib.git_revwalk_push(revwalk, oid._native)
            self.raise_if_error(error_code, "Can’t set revwalk to Oid: {message}")

        return RevWalk(repo=self, native=revwalk)

    @cached_property
    def config(self) -> Config:
        native = git_config_p()
        error_code = lib.git_repository_config(native, self._native)
        self.raise_if_error(error_code)
        return Config(native=native)

    @property
    def default_signature(self) -> Signature:
        native = git_signature_p()
        error_code = lib.git_signature_default(native, self._native)
        self.raise_if_error(error_code)
        return Signature._from_native(native=native)

    def lookup_reference(self, reference_name: str) -> Reference:
        native = git_reference_p()
        error_code = lib.git_reference_lookup(
            byref(native),
            self._native,
            reference_name.encode(
                encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
            ),
        )
        self.raise_if_error(error_code)
        return Reference(repo=self, native=native)

    def lookup_reference_dwim(self, reference_name: str) -> Reference:
        native = git_reference_p()
        error_code = lib.git_reference_dwim(
            byref(native),
            self._native,
            reference_name.encode(
                encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
            ),
        )
        self.raise_if_error(error_code)
        return Reference(repo=self, native=native)

    def resolve_refish(self, refish: str) -> Commit:
        try:
            reference = self.lookup_reference_dwim(refish)
        except (KeyError, InvalidSpecError):
            reference = None
            commit = self.revparse_single(refish)
        else:
            commit = reference.peel(Commit)

        return commit, reference

    def create_commit(
        self,
        reference_name: str,
        author: Signature,
        committer: Signature,
        message: Union[str, bytes],
        tree_oid: Oid,
        parent_oids: list[Oid],
        encoding: str = "utf-8",
    ) -> Oid:
        if reference_name:
            refname = reference_name.encode("utf-8")
        else:
            refname = c_char_p()
        if isinstance(message, str):
            message = message.encode(encoding=encoding)

        tree = Tree._from_oid(self, tree_oid)

        pcount = len(parent_oids)
        parent_commits = [Commit._from_oid(self, poid) for poid in parent_oids]
        native_parent_commits = (git_commit_p * pcount)(*(c._native for c in parent_commits))

        native = git_oid()
        error_code = lib.git_commit_create(
            byref(native),
            self._native,
            refname,
            author._native,
            committer._native,
            encoding.encode("ascii"),
            message,
            tree._native,
            pcount,
            native_parent_commits,
        )
        self.raise_if_error(error_code)

        return Oid(native)

    def create_branch(self, reference_name: str, commit: Commit, force: bool = False) -> Branch:
        ref = git_reference_p()
        error_code = lib.git_branch_create(
            byref(ref), self._native, reference_name.encode("utf-8"), commit._native, force
        )
        self.raise_if_error(error_code)

        return Branch(repo=self, native=ref)

    def set_head(self, target: Union[Oid, str, bytes]) -> None:
        if isinstance(target, Oid):
            error_code = lib.git_repository_set_head_detached(self._native, target._native)
        else:
            if isinstance(target, str):
                target = target.encode(encoding="utf-8", errors="strict")
            error_code = lib.git_repository_set_head(self._native, target)

        self.raise_if_error(error_code)

    def checkout_head(
        self,
        *,
        strategy: git_checkout_strategy_t = git_checkout_strategy_t.NONE,
    ) -> None:
        options = git_checkout_options()
        error_code = lib.git_checkout_options_init(byref(options), GIT_CHECKOUT_OPTIONS_VERSION)
        self.raise_if_error(error_code)

        options.checkout_strategy = strategy

        error_code = lib.git_checkout_head(self._native, options)
        self.raise_if_error(error_code)

    def checkout_index(
        self,
        index: Optional[Index] = None,
        *,
        strategy: git_checkout_strategy_t = git_checkout_strategy_t.NONE,
    ) -> None:
        options = git_checkout_options()
        error_code = lib.git_checkout_options_init(byref(options), GIT_CHECKOUT_OPTIONS_VERSION)
        self.raise_if_error(error_code)

        options.checkout_strategy = strategy

        error_code = lib.git_checkout_index(self._native, index._native if index else None, options)
        self.raise_if_error(error_code)

    def checkout_tree(
        self,
        treeish: Optional[Object] = None,
        *,
        strategy: git_checkout_strategy_t = git_checkout_strategy_t.NONE,
    ) -> None:
        options = git_checkout_options()
        error_code = lib.git_checkout_options_init(byref(options), GIT_CHECKOUT_OPTIONS_VERSION)
        self.raise_if_error(error_code)

        options.checkout_strategy = strategy

        error_code = lib.git_checkout_tree(
            self._native, cast(treeish._native, git_object_p), options
        )
        self.raise_if_error(error_code)

    def checkout(
        self, refname: Optional[Union[Reference, str]] = None, **kwargs: dict[str, Any]
    ) -> None:
        if not refname:
            return self.checkout_index(**kwargs)

        if refname == "HEAD":
            return self.checkout_head(**kwargs)

        if isinstance(refname, Reference):
            reference = refname
            refname = reference.name
        else:
            reference = self.lookup_reference(refname)

        oid = reference.resolve().target
        treeish = self[oid]
        self.checkout_tree(treeish, **kwargs)

        # The delegated "paths" parameter isn’t implemented in .checkout_*().
        if "paths" not in kwargs:  # pragma: no branch
            self.set_head(refname)

    def status_file(self, path: Union[PathLike, str, bytes]) -> git_status_t:
        path = fspath(path)
        if isinstance(path, str):
            path = path.encode(encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors())

        native = c_uint()
        error_code = lib.git_status_file(byref(native), self._native, path)
        self.raise_if_error(error_code)

        return git_status_t(native.value)

    def status(
        self, untracked_files: Literal["all", "normal", "no"] = "all", ignored: bool = False
    ) -> dict[str, git_status_t]:
        options = git_status_options()
        error_code = lib.git_status_options_init(byref(options), GIT_STATUS_OPTIONS_VERSION)
        self.raise_if_error(error_code)

        options.flags = GIT_STATUS_OPT_DEFAULTS

        if untracked_files == "no":
            options.flags &= ~(
                git_status_opt_t.INCLUDE_UNTRACKED | git_status_opt_t.RECURSE_UNTRACKED_DIRS
            )
        elif untracked_files == "normal":
            options.flags &= ~git_status_opt_t.RECURSE_UNTRACKED_DIRS

        if not ignored:
            options.flags &= ~git_status_opt_t.INCLUDE_IGNORED

        status_list = git_status_list_p()
        error_code = lib.git_status_list_new(byref(status_list), self._native, options)
        self.raise_if_error(error_code)

        encoding = getfilesystemencoding()
        errors = getfilesystemencodeerrors()

        entries = {}
        for idx in range(lib.git_status_list_entrycount(status_list)):
            entry = lib.git_status_byindex(status_list, idx).contents
            if entry.head_to_index:
                diff_delta = entry.head_to_index.contents
            else:
                diff_delta = entry.index_to_workdir.contents
            path = diff_delta.old_file.path.decode(encoding=encoding, errors=errors)

            entries[path] = git_status_t(entry.status)

        lib.git_status_list_free(status_list)

        return entries
