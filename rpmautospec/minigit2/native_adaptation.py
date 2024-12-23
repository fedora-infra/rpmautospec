"""Minimal wrapper for libgit2 - Native Adaptation"""

from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    c_char,
    c_char_p,
    c_int,
    c_size_t,
    c_uint,
    c_uint32,
    c_uint64,
    c_void_p,
    cast,
)
from enum import IntEnum, IntFlag, auto

NULL = cast(POINTER(c_int)(), c_void_p)


# Simple types

git_off_t = c_uint64


class IntEnumMixin:
    @classmethod
    def from_param(cls, obj):
        return int(obj)


class git_error_code(IntEnumMixin, IntEnum):
    # @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        last_value = sorted(last_values)[0]
        return last_value - 1

    OK = 0
    ERROR = auto()
    ENOTFOUND = auto()
    EEXISTS = auto()
    EAMBIGUOUS = auto()
    EBUFS = auto()

    EUSER = auto()

    EBAREREPO = auto()
    EUNBORNBRANCH = auto()
    EUNMERGED = auto()
    ENONFASTFORWARD = auto()
    EINVALIDSPEC = auto()
    ECONFLICT = auto()
    ELOCKED = auto()
    EMODIFIED = auto()
    EAUTH = auto()
    ECERTIFICATE = auto()
    EAPPLIED = auto()
    EPEEL = auto()
    EEOF = auto()
    EINVALID = auto()
    EUNCOMMITTED = auto()
    EDIRECTORY = auto()
    EMERGECONFLICT = auto()

    PASSTHROUGH = -30
    ITEROVER = auto()
    RETRY = auto()
    EMISMATCH = auto()
    EINDEXDIRTY = auto()
    EAPPLYFAIL = auto()


class git_error_t(IntEnumMixin, IntEnum):
    NONE = 0
    NOMEMORY = auto()
    OS = auto()
    INVALID = auto()
    REFERENCE = auto()
    ZLIB = auto()
    REPOSITORY = auto()
    CONFIG = auto()
    REGEX = auto()
    ODB = auto()
    INDEX = auto()
    OBJECT = auto()
    NET = auto()
    TAG = auto()
    TREE = auto()
    INDEXER = auto()
    SSL = auto()
    SUBMODULE = auto()
    THREAD = auto()
    STASH = auto()
    CHECKOUT = auto()
    FETCHHEAD = auto()
    MERGE = auto()
    SSH = auto()
    FILTER = auto()
    REVERT = auto()
    CALLBACK = auto()
    CHERRYPICK = auto()
    DESCRIBE = auto()
    REBASE = auto()
    FILESYSTEM = auto()
    PATCH = auto()
    WORKTREE = auto()
    SHA = auto()
    HTTP = auto()
    INTERNAL = auto()


class git_repository_item_t(IntEnumMixin, IntEnum):
    GITDIR = 0
    WORKDIR = auto()
    COMMONDIR = auto()
    INDEX = auto()
    OBJECTS = auto()
    REFS = auto()
    PACKED_REFS = auto()
    REMOTES = auto()
    CONFIG = auto()
    INFO = auto()
    HOOKS = auto()
    LOGS = auto()
    MODULES = auto()
    WORKTREES = auto()


class git_repository_open_flag_t(IntEnumMixin, IntFlag):
    NO_SEARCH = 1 << 0
    CROSS_FS = auto()
    BARE = auto()
    NO_DOTGIT = auto()
    FROM_ENV = auto()


class git_reference_t(IntEnumMixin, IntFlag):
    INVALID = 0
    DIRECT = auto()
    SYMBOLIC = auto()
    ALL = auto()


class git_object_t(IntEnumMixin, IntEnum):
    ANY = -2
    INVALID = -1
    COMMIT = 1
    TREE = auto()
    BLOB = auto()
    TAG = auto()
    OFS_DELTA = auto()
    REF_DELTA = auto()


class git_diff_option_t(IntEnumMixin, IntFlag):
    NORMAL = 0
    REVERSE = auto()
    INCLUDE_IGNORED = auto()
    RECURSE_IGNORED_DIRS = auto()
    INCLUDE_UNTRACKED = auto()
    RECURSE_UNTRACKED_DIRS = auto()
    INCLUDE_UNMODIFIED = auto()
    INCLUDE_TYPECHANGE = auto()
    INCLUDE_TYPECHANGE_TREES = auto()
    IGNORE_FILEMODE = auto()
    IGNORE_SUBMODULES = auto()
    IGNORE_CASE = auto()
    INCLUDE_CASECHANGE = auto()
    DISABLE_PATHSPEC_MATCH = auto()
    SKIP_BINARY_CHECK = auto()
    ENABLE_FAST_UNTRACKED_DIRS = auto()
    UPDATE_INDEX = auto()
    INCLUDE_UNREADABLE = auto()
    INCLUDE_UNREADABLE_AS_UNTRACKED = auto()
    INDENT_HEURISTIC = auto()
    IGNORE_BLANK_LINES = auto()
    FORCE_TEXT = auto()
    FORCE_BINARY = auto()
    IGNORE_WHITESPACE = auto()
    IGNORE_WHITESPACE_CHANGE = auto()
    IGNORE_WHITESPACE_EOL = auto()
    SHOW_UNTRACKED_CONTENT = auto()
    SHOW_UNMODIFIED = auto()
    PATIENCE = auto()
    MINIMAL = auto()
    SHOW_BINARY = auto()


class git_submodule_ignore_t(IntEnumMixin, IntEnum):
    UNSPECIFIED = -1
    NONE = 1
    UNTRACKED = auto()
    DIRTY = auto()
    ALL = auto()


class git_oid_t(IntEnumMixin, IntEnum):
    SHA1 = 1


# Compound types


class git_error(Structure):
    _fields_ = (
        ("message", c_char_p),
        ("klass", c_int),
    )


git_error_p = POINTER(git_error)
git_error_p_p = POINTER(git_error_p)


class git_buf(Structure):
    _fields_ = (
        ("ptr", c_char_p),
        ("asize", c_size_t),
        ("size", c_size_t),
    )


git_buf_p = POINTER(git_buf)
git_buf_p_p = POINTER(git_buf_p)


class git_strarray(Structure):
    _fields_ = (
        ("strings", POINTER(c_char_p)),
        ("count", c_size_t),
    )


git_strarray_p = POINTER(git_strarray)
git_strarray_p_p = POINTER(git_strarray_p)


class git_repository(Structure):
    pass


git_repository_p = POINTER(git_repository)
git_repository_p_p = POINTER(git_repository_p)


class git_oid(Structure):
    _fields_ = (("id", c_char * 20),)


git_oid_p = POINTER(git_oid)
git_oid_p_p = POINTER(git_oid_p)


class git_reference(Structure):
    pass


git_reference_p = POINTER(git_reference)
git_reference_p_p = POINTER(git_reference_p)


class git_object(Structure):
    pass


git_object_p = POINTER(git_object)
git_object_p_p = POINTER(git_object_p)


class git_commit(Structure):
    pass


git_commit_p = POINTER(git_commit)
git_commit_p_p = POINTER(git_commit_p)


class git_tree(Structure):
    pass


git_tree_p = POINTER(git_tree)
git_tree_p_p = POINTER(git_tree_p)


class git_tag(Structure):
    pass


git_tag_p = POINTER(git_tag)
git_tag_p_p = POINTER(git_tag_p)


class git_blob(Structure):
    pass


git_blob_p = POINTER(git_blob)
git_blob_p_p = POINTER(git_blob_p)


class git_diff(Structure):
    pass


git_diff_p = POINTER(git_diff)
git_diff_p_p = POINTER(git_diff_p)


class git_diff_delta(Structure):
    pass


git_diff_delta_p = POINTER(git_diff_delta)
git_diff_delta_p_p = POINTER(git_diff_delta_p)


git_diff_notify_cb = CFUNCTYPE(c_int, git_diff_p, git_diff_delta_p, c_char_p, c_void_p)
git_diff_progress_cb = CFUNCTYPE(c_int, git_diff_p, c_char_p, c_char_p, c_void_p)


class git_diff_options(Structure):
    _fields_ = (
        ("version", c_uint),
        ("flags", c_uint32),
        ("ignore_submodules", c_int),
        ("pathspec", git_strarray),
        ("notify_cb", git_diff_notify_cb),
        ("progress_cb", git_diff_progress_cb),
        ("payload", c_void_p),
        ("context_lines", c_uint32),
        ("interhunk_lines", c_uint32),
        ("oid_type", c_int),  # Added in libgit2 v1.7.0
        ("id_abbrev", c_uint32),
        ("max_size", git_off_t),
        ("old_prefix", c_char_p),
        ("new_prefix", c_char_p),
    )


git_diff_options_p = POINTER(git_diff_options)
git_diff_options_p_p = POINTER(git_diff_options_p)


class git_index(Structure):
    pass


git_index_p = POINTER(git_index)
git_index_p_p = POINTER(git_index_p)


# Native function declarations

FUNC_DECLS = {
    "git_blob_create_from_buffer": (c_int, (git_oid_p, git_repository_p, c_void_p, c_size_t)),
    "git_blob_free": (None, (git_blob_p,)),
    "git_commit_free": (None, (git_commit_p,)),
    "git_diff_options_init": (c_int, (git_diff_options_p, c_uint)),
    "git_diff_tree_to_tree": (
        c_int,
        (git_diff_p_p, git_repository_p, git_tree_p, git_tree_p, git_diff_options_p),
    ),
    "git_error_last": (git_error_p, ()),
    "git_index_free": (None, (git_index_p,)),
    "git_libgit2_init": (c_int, ()),
    "git_object_free": (None, (git_object_p,)),
    "git_object_id": (git_oid_p, (git_object_p,)),
    "git_object_lookup_prefix": (
        c_int,
        (git_object_p_p, git_repository_p, git_oid_p, c_size_t, git_object_t),
    ),
    "git_object_peel": (c_int, (git_object_p_p, git_object_p, git_object_t)),
    "git_object_type": (git_object_t, (git_object_p,)),
    "git_oid_fmt": (c_int, (c_char_p, git_oid_p)),
    "git_oid_fromstrn": (c_int, (git_oid_p, c_char_p, c_size_t)),
    "git_reference_symbolic_target": (c_char_p, (git_reference_p,)),
    "git_reference_target": (git_oid_p, (git_reference_p,)),
    "git_reference_type": (git_reference_t, (git_reference_p,)),
    "git_repository_free": (None, (git_repository_p,)),
    "git_repository_head": (c_int, (git_reference_p_p, git_repository_p)),
    "git_repository_index": (c_int, (git_index_p_p, git_repository_p)),
    "git_repository_item_path": (c_int, (git_buf_p, git_repository_p, git_repository_item_t)),
    "git_repository_open_ext": (c_int, (git_repository_p_p, c_char_p, c_uint, c_char_p)),
    "git_revparse_single": (c_int, (git_object_p_p, git_repository_p, c_char_p)),
    "git_tag_free": (None, (git_tag_p,)),
    "git_tree_free": (None, (git_tree_p,)),
}


# Functions to set up the wrapper


def apply_version_compat(version: tuple[int]):
    if version < (1, 7, 0):
        git_diff_options._fields_ = tuple(
            (memname, memtype)
            for memname, memtype in git_diff_options._fields_
            if memname != "oid_type"
        )


def install_func_decls(lib: CDLL) -> None:
    for func_name, (restype, argtypes) in FUNC_DECLS.items():
        func = getattr(lib, func_name)
        func.restype = restype
        func.argtypes = argtypes
