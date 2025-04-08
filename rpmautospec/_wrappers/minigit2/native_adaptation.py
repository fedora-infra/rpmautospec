"""Minimal wrapper for libgit2 - Native Adaptation"""

from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    c_char,
    c_char_p,
    c_int,
    c_int32,
    c_int64,
    c_size_t,
    c_uint,
    c_uint16,
    c_uint32,
    c_uint64,
    c_void_p,
)
from enum import IntEnum, IntFlag, auto
from typing import Optional

from ..common import IntEnumMixin, install_func_decls, load_lib

lib: Optional[CDLL] = None
soname: Optional[str] = None
version: Optional[str] = None
version_tuple: Optional[tuple[int]] = None

LIBGIT2_KNOWN_VERSIONS = tuple((1, minor) for minor in range(1, 10))


try:
    lib, soname, version, version_tuple = load_lib("git2", known_versions=LIBGIT2_KNOWN_VERSIONS)
    lib.git_libgit2_init()
except Exception as exc:  # pragma: no cover
    raise ImportError from exc


# Simple types

git_object_size_t = c_uint64
git_off_t = c_uint64
git_time_t = c_int64


class git_error_code(IntEnumMixin, IntEnum):
    # @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        last_value = sorted(last_values)[0]
        return last_value - 1

    OK = 0
    ERROR = auto()

    ENOTFOUND = -3
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


class git_sort_t(IntEnumMixin, IntFlag):
    NONE = 0
    TOPOLOGICAL = auto()
    TIME = auto()
    REVERSE = auto()


class git_filemode_t(IntEnumMixin, IntFlag):
    UNREADABLE = 0
    TREE = 0o40000
    BLOB = 0o100644
    BLOB_EXECUTABLE = 0o100755
    LINK = 0o120000
    COMMIT = 0o160000


class git_delta_t(IntEnumMixin, IntEnum):
    UNMODIFIED = 0
    ADDED = auto()
    DELETED = auto()
    MODIFIED = auto()
    RENAMED = auto()
    COPIED = auto()
    IGNORED = auto()
    UNTRACKED = auto()
    TYPECHANGE = auto()
    UNREADABLE = auto()
    CONFLICTED = auto()


class git_config_level_t(IntEnumMixin, IntEnum):  # pragma: no cover
    PROGRAMDATA = 1
    SYSTEM = auto()
    XDG = auto()
    GLOBAL = auto()
    LOCAL = auto()
    if version_tuple >= (1, 8):
        WORKTREE = auto()
    APP = auto()
    HIGHEST = -1


class git_libgit2_opt_t(IntEnumMixin, IntEnum):
    # This is abridged.
    GET_SEARCH_PATH = 4
    SET_SEARCH_PATH = 5


class git_diff_flag_t(IntEnumMixin, IntFlag):
    BINARY = 1 << 0
    NOT_BINARY = auto()
    VALID_ID = auto()
    EXISTS = auto()
    if version_tuple >= (1, 4):  # pragma: no cover
        VALID_SIZE = auto()


class git_checkout_notify_t(IntEnumMixin, IntFlag):
    NONE = 0
    CONFLICT = 1 << 0
    DIRTY = auto()
    UPDATED = auto()
    UNTRACKED = auto()
    IGNORED = auto()
    ALL = (1 << 16) - 1


class git_checkout_strategy_t(IntEnumMixin, IntFlag):
    SAFE = 0
    FORCE = 1 << 1
    RECREATE_MISSING = auto()

    ALLOW_CONFLICTS = 1 << 4
    REMOVE_UNTRACKED = auto()
    REMOVE_IGNORED = auto()
    UPDATE_ONLY = auto()
    DONT_UPDATE_INDEX = auto()
    NO_REFRESH = auto()
    SKIP_UNMERGED = auto()
    USE_OURS = auto()
    USE_THEIRS = auto()
    DISABLE_PATHSPEC_MATCH = auto()

    SKIP_LOCKED_DIRECTORIES = 1 << 18
    DONT_OVERWRITE_IGNORED = auto()
    CONFLICT_STYLE_MERGE = auto()
    CONFLICT_STYLE_DIFF3 = auto()
    DONT_REMOVE_EXISTING = auto()
    DONT_WRITE_INDEX = auto()
    DRY_RUN = auto()
    CONFLICT_STYLE_ZDIFF3 = auto()

    NONE = 1 << 30

    UPDATE_SUBMODULES = 1 << 16
    UPDATE_SUBMODULES_IF_CHANGED = auto()


class git_repository_init_flag_t(IntEnumMixin, IntFlag):
    BARE = 1 << 0
    NO_REINIT = auto()

    MKDIR = 1 << 3
    MKPATH = auto()
    EXTERNAL_TEMPLATE = auto()
    RELATIVE_GITLINK = auto()


class git_status_t(IntEnumMixin, IntFlag):
    CURRENT = 0
    INDEX_NEW = 1 << 0
    INDEX_MODIFIED = auto()
    INDEX_DELETED = auto()
    INDEX_RENAMED = auto()
    INDEX_TYPECHANGE = auto()

    WT_NEW = 1 << 7
    WT_MODIFIED = auto()
    WT_DELETED = auto()
    WT_TYPECHANGE = auto()
    WT_RENAMED = auto()
    WT_UNREADABLE = auto()

    IGNORED = 1 << 14
    CONFLICTED = auto()


class git_status_show_t(IntEnumMixin, IntFlag):
    INDEX_AND_WORKDIR = 0
    INDEX_ONLY = auto()
    WORKDIR_ONLY = auto()


class git_status_opt_t(IntEnumMixin, IntFlag):
    INCLUDE_UNTRACKED = 1 << 0
    INCLUDE_IGNORED = auto()
    INCLUDE_UNMODIFIED = auto()
    EXCLUDE_SUBMODULES = auto()
    RECURSE_UNTRACKED_DIRS = auto()
    DISABLE_PATHSPEC_MATCH = auto()
    RECURSE_IGNORED_DIRS = auto()
    RENAMES_HEAD_TO_INDEX = auto()
    RENAMES_INDEX_TO_WORKDIR = auto()
    SORT_CASE_SENSITIVELY = auto()
    SORT_CASE_INSENSITIVELY = auto()
    RENAMES_FROM_REWRITES = auto()
    NO_REFRESH = auto()
    UPDATE_INDEX = auto()
    INCLUDE_UNREADABLE = auto()
    INCLUDE_UNREADABLE_AS_UNTRACKED = auto()


class git_diff_format_t(IntEnumMixin, IntEnum):
    PATCH = 1
    PATCH_HEADER = auto()
    RAW = auto()
    NAME_ONLY = auto()
    NAME_STATUS = auto()
    PATCH_ID = auto()


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
        ("ptr", POINTER(c_char)),
        ("reserved", c_size_t),
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


class git_revwalk(Structure):
    pass


git_revwalk_p = POINTER(git_revwalk)
git_revwalk_p_p = POINTER(git_revwalk_p)


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


class git_tree_entry(Structure):
    pass


git_tree_entry_p = POINTER(git_tree_entry)
git_tree_entry_p_p = POINTER(git_tree_entry_p)


class git_tag(Structure):
    pass


git_tag_p = POINTER(git_tag)
git_tag_p_p = POINTER(git_tag_p)


class git_blob(Structure):
    pass


git_blob_p = POINTER(git_blob)
git_blob_p_p = POINTER(git_blob_p)


class git_diff_stats(Structure):
    pass


git_diff_stats_p = POINTER(git_diff_stats)
git_diff_stats_p_p = POINTER(git_diff_stats_p)


class git_diff(Structure):
    pass


git_diff_p = POINTER(git_diff)
git_diff_p_p = POINTER(git_diff_p)


class git_diff_file(Structure):
    _fields_ = (
        ("id", git_oid),
        ("path", c_char_p),
        ("size", git_object_size_t),
        ("flags", c_uint32),
        ("mode", c_uint16),
        ("id_abbrev", c_uint16),
    )


git_diff_file_p = POINTER(git_diff_file)
git_diff_file_p_p = POINTER(git_diff_file_p)


class git_diff_delta(Structure):
    _fields_ = (
        ("status", c_uint),  # really git_delta_t
        ("flags", c_uint32),
        ("similarity", c_uint16),
        ("nfiles", c_uint16),
        ("old_file", git_diff_file),
        ("new_file", git_diff_file),
    )


git_diff_delta_p = POINTER(git_diff_delta)
git_diff_delta_p_p = POINTER(git_diff_delta_p)


git_diff_notify_cb = CFUNCTYPE(c_int, git_diff_p, git_diff_delta_p, c_char_p, c_void_p)
git_diff_progress_cb = CFUNCTYPE(c_int, git_diff_p, c_char_p, c_char_p, c_void_p)


class git_diff_options(Structure):
    _fields_ = tuple(
        (fname, ftype)
        for fname, ftype in (
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
        if fname != "oid_type" or version_tuple >= (1, 7)
    )


git_diff_options_p = POINTER(git_diff_options)
git_diff_options_p_p = POINTER(git_diff_options_p)


class git_index(Structure):
    pass


git_index_p = POINTER(git_index)
git_index_p_p = POINTER(git_index_p)


class git_index_time(Structure):
    _fields_ = (
        ("seconds", c_int32),
        ("nanoseconds", c_uint32),
    )


git_index_time_p = POINTER(git_index_time)
git_index_time_p_p = POINTER(git_index_time_p)


class git_index_entry(Structure):
    _fields_ = (
        ("ctime", git_index_time),
        ("mtime", git_index_time),
        ("dev", c_uint32),
        ("ino", c_uint32),
        ("mode", c_uint32),
        ("uid", c_uint32),
        ("gid", c_uint32),
        ("file_size", c_uint32),
        ("id", git_oid),
        ("flags", c_uint16),
        ("flags_extended", c_uint16),
        ("path", c_char_p),
    )


git_index_entry_p = POINTER(git_index_entry)
git_index_entry_p_p = POINTER(git_index_entry_p)


git_index_matched_path_cb = CFUNCTYPE(c_int, c_char_p, c_char_p, c_void_p)


class git_time(Structure):
    _fields_ = (
        ("time", git_time_t),
        ("offset", c_int),
        ("sign", c_char),
    )


class git_signature(Structure):
    _fields_ = (
        ("name", c_char_p),
        ("email", c_char_p),
        ("when", git_time),
    )


git_signature_p = POINTER(git_signature)
git_signature_p_p = POINTER(git_signature_p)


class git_config_entry(Structure):
    _fields_ = (
        ("name", c_char_p),
        ("value", c_char_p),
        ("backend_type", c_char_p),
        ("origin_path", c_char_p),
        ("include_depth", c_uint),
        ("level", c_int),  # really git_config_level_t
    )


git_config_entry_p = POINTER(git_config_entry)
git_config_entry_p_p = POINTER(git_config_entry_p)


class git_config(Structure):
    pass


git_config_p = POINTER(git_config)
git_config_p_p = POINTER(git_config_p)


git_checkout_notify_cb = CFUNCTYPE(
    c_int,
    git_checkout_notify_t,
    c_char_p,
    git_diff_file_p,
    git_diff_file_p,
    git_diff_file_p,
    c_void_p,
)
git_checkout_progress_cb = CFUNCTYPE(None, c_char_p, c_size_t, c_size_t, c_void_p)


class git_checkout_perfdata(Structure):
    _fields_ = (
        ("mkdir_calls", c_size_t),
        ("stat_calls", c_size_t),
        ("chmod_calls", c_size_t),
    )


git_checkout_perfdata_p = POINTER(git_checkout_perfdata)
git_checkout_perfdata_cb = CFUNCTYPE(None, git_checkout_perfdata_p, c_void_p)


class git_checkout_options(Structure):
    _fields_ = (
        ("version", c_uint),
        ("checkout_strategy", c_uint),
        ("disable_filters", c_int),
        ("dir_mode", c_uint),
        ("file_mode", c_uint),
        ("file_open_flags", c_int),
        ("notify_flags", c_uint),
        ("notify_cb", git_checkout_notify_cb),
        ("notify_payload", c_void_p),
        ("progress_cb", git_checkout_progress_cb),
        ("progress_payload", c_void_p),
        ("paths", git_strarray),
        ("baseline", git_tree_p),
        ("baseline_index", git_index_p),
        ("target_directory", c_char_p),
        ("ancestor_label", c_char_p),
        ("our_label", c_char_p),
        ("their_label", c_char_p),
        ("perfdata_cb", git_checkout_perfdata_cb),
        ("perfdata_payload", c_void_p),
    )


git_checkout_options_p = POINTER(git_checkout_options)
git_checkout_options_p_p = POINTER(git_checkout_options_p)


class git_repository_init_options(Structure):
    _fields_ = (
        ("version", c_uint),
        ("flags", c_uint32),  # really git_repository_init_flag_t
        ("mode", c_uint32),
        ("workdir_path", c_char_p),
        ("description", c_char_p),
        ("template_path", c_char_p),
        ("initial_head", c_char_p),
        ("origin_url", c_char_p),
    )


git_repository_init_options_p = POINTER(git_repository_init_options)
git_repository_init_options_p_p = POINTER(git_repository_init_options_p)


class git_status_options(Structure):
    _fields_ = (
        ("version", c_uint),
        ("show", c_uint),  # really git_status_show_t
        ("flags", c_uint),  # really git_status_options
        ("pathspec", git_strarray),
        ("baseline", git_tree_p),
        ("rename_threshold", c_uint16),
    )


git_status_options_p = POINTER(git_status_options)
git_status_options_p_p = POINTER(git_status_options_p)


class git_status_list(Structure):
    pass


git_status_list_p = POINTER(git_status_list)
git_status_list_p_p = POINTER(git_status_list_p)


class git_status_entry(Structure):
    _fields_ = (
        ("status", c_uint),  # really git_status_t
        ("head_to_index", git_diff_delta_p),
        ("index_to_workdir", git_diff_delta_p),
    )


git_status_entry_p = POINTER(git_status_entry)
git_status_entry_p_p = POINTER(git_status_entry_p)


# Native function declarations

FUNC_DECLS = {
    "git_blob_create_from_buffer": (c_int, (git_oid_p, git_repository_p, c_void_p, c_size_t)),
    "git_blob_free": (None, (git_blob_p,)),
    "git_blob_lookup": (c_int, (git_blob_p_p, git_repository_p, git_oid_p)),
    "git_blob_rawcontent": (c_void_p, (git_blob_p,)),
    "git_blob_rawsize": (git_object_size_t, (git_blob_p,)),
    "git_branch_create": (
        c_int,
        (git_reference_p_p, git_repository_p, c_char_p, git_commit_p, c_int),
    ),
    "git_buf_dispose": (None, (git_buf_p,)),
    "git_checkout_options_init": (c_int, (git_checkout_options_p, c_uint)),
    "git_checkout_head": (c_int, (git_repository_p, git_checkout_options_p)),
    "git_checkout_index": (c_int, (git_repository_p, git_index_p, git_checkout_options_p)),
    "git_checkout_tree": (c_int, (git_repository_p, git_object_p, git_checkout_options_p)),
    "git_commit_author": (git_signature_p, (git_commit_p,)),
    "git_commit_committer": (git_signature_p, (git_commit_p,)),
    "git_commit_create": (
        c_int,
        (
            git_oid_p,
            git_repository_p,
            c_char_p,
            git_signature_p,
            git_signature_p,
            c_char_p,
            c_char_p,
            git_tree_p,
            c_size_t,
            git_commit_p_p,
        ),
    ),
    "git_commit_free": (None, (git_commit_p,)),
    "git_commit_lookup": (c_int, (git_commit_p_p, git_repository_p, git_oid_p)),
    "git_commit_message": (c_char_p, (git_commit_p,)),
    "git_commit_message_encoding": (c_char_p, (git_commit_p,)),
    "git_commit_parent": (c_int, (git_commit_p_p, git_commit_p, c_uint)),
    "git_commit_parentcount": (c_uint, (git_commit_p,)),
    "git_commit_time": (git_time_t, (git_commit_p,)),
    "git_commit_time_offset": (c_int, (git_commit_p,)),
    "git_commit_tree": (c_int, (git_tree_p_p, git_commit_p)),
    "git_config_delete_entry": (c_int, (git_config_p, c_char_p)),
    "git_config_entry_free": (None, (git_config_entry_p,)),
    "git_config_get_entry": (c_int, (git_config_entry_p_p, git_config_p, c_char_p)),
    "git_config_open_ondisk": (c_int, (git_config_p_p, c_char_p)),
    "git_config_set_bool": (c_int, (git_config_p, c_char_p, c_int)),
    "git_config_set_int64": (c_int, (git_config_p, c_char_p, c_int64)),
    "git_config_set_string": (c_int, (git_config_p, c_char_p, c_char_p)),
    "git_config_free": (None, (git_config_p,)),
    "git_diff_get_delta": (git_diff_delta_p, (git_diff_p, c_size_t)),
    "git_diff_get_stats": (c_int, (git_diff_stats_p_p, git_diff_p)),
    "git_diff_index_to_workdir": (
        c_int,
        (git_diff_p_p, git_repository_p, git_index_p, git_diff_options_p),
    ),
    "git_diff_num_deltas": (c_size_t, (git_diff_p,)),
    "git_diff_options_init": (c_int, (git_diff_options_p, c_uint)),
    "git_diff_stats_free": (None, (git_diff_stats_p,)),
    "git_diff_to_buf": (c_int, (git_buf_p, git_diff_p, git_diff_format_t)),
    "git_diff_tree_to_index": (
        c_int,
        (git_diff_p_p, git_repository_p, git_tree_p, git_index_p, git_diff_options_p),
    ),
    "git_diff_tree_to_tree": (
        c_int,
        (git_diff_p_p, git_repository_p, git_tree_p, git_tree_p, git_diff_options_p),
    ),
    "git_diff_tree_to_workdir": (
        c_int,
        (git_diff_p_p, git_repository_p, git_tree_p, git_diff_options_p),
    ),
    "git_error_last": (git_error_p, ()),
    "git_index_add_all": (
        c_int,
        (git_index_p, git_strarray_p, c_uint, git_index_matched_path_cb, c_void_p),
    ),
    "git_index_add_bypath": (c_int, (git_index_p, c_char_p)),
    "git_index_free": (None, (git_index_p,)),
    "git_index_remove": (c_int, (git_index_p, c_char_p, c_int)),
    "git_index_write": (c_int, (git_index_p,)),
    "git_index_write_tree": (
        c_int,
        (
            git_oid_p,
            git_index_p,
        ),
    ),
    "git_libgit2_init": (c_int, ()),
    "git_libgit2_opts": (c_int, (c_int,)),  # variadic
    "git_object_free": (None, (git_object_p,)),
    "git_object_id": (git_oid_p, (git_object_p,)),
    "git_object_lookup": (c_int, (git_object_p_p, git_repository_p, git_oid_p)),
    "git_object_lookup_prefix": (
        c_int,
        (git_object_p_p, git_repository_p, git_oid_p, c_size_t, git_object_t),
    ),
    "git_object_peel": (c_int, (git_object_p_p, git_object_p, git_object_t)),
    "git_object_short_id": (c_int, (git_buf_p, git_object_p)),
    "git_object_type": (git_object_t, (git_object_p,)),
    "git_oid_fmt": (c_int, (c_char_p, git_oid_p)),
    "git_oid_fromstrp": (c_int, (git_oid_p, c_char_p)),
    "git_reference_dwim": (c_int, (git_reference_p_p, git_repository_p, c_char_p)),
    "git_reference_lookup": (c_int, (git_reference_p_p, git_repository_p, c_char_p)),
    "git_reference_name": (c_char_p, (git_reference_p,)),
    "git_reference_peel": (c_int, (git_object_p_p, git_reference_p, git_object_t)),
    "git_reference_resolve": (c_int, (git_reference_p_p, git_reference_p)),
    "git_reference_shorthand": (c_char_p, (git_reference_p,)),
    "git_reference_symbolic_create": (
        c_int,
        (git_reference_p_p, git_repository_p, c_char_p, c_char_p, c_int, c_char_p),
    ),
    "git_reference_symbolic_target": (c_char_p, (git_reference_p,)),
    "git_reference_target": (git_oid_p, (git_reference_p,)),
    "git_reference_type": (git_reference_t, (git_reference_p,)),
    "git_repository_config": (c_int, (git_config_p_p, git_repository_p)),
    "git_repository_free": (None, (git_repository_p,)),
    "git_repository_head": (c_int, (git_reference_p_p, git_repository_p)),
    "git_repository_index": (c_int, (git_index_p_p, git_repository_p)),
    "git_repository_init_ext": (
        c_int,
        (git_repository_p_p, c_char_p, git_repository_init_options_p),
    ),
    "git_repository_init_options_init": (c_int, (git_repository_init_options_p, c_uint)),
    "git_repository_item_path": (c_int, (git_buf_p, git_repository_p, git_repository_item_t)),
    "git_repository_open_ext": (c_int, (git_repository_p_p, c_char_p, c_uint, c_char_p)),
    "git_repository_set_head": (c_int, (git_repository_p, c_char_p)),
    "git_repository_set_head_detached": (c_int, (git_repository_p, git_oid_p)),
    "git_repository_path": (c_char_p, (git_repository_p,)),
    "git_repository_workdir": (c_char_p, (git_repository_p,)),
    "git_revparse_single": (c_int, (git_object_p_p, git_repository_p, c_char_p)),
    "git_revwalk_free": (None, (git_revwalk_p,)),
    "git_revwalk_new": (c_int, (git_revwalk_p_p, git_repository_p)),
    "git_revwalk_next": (c_int, (git_oid_p, git_revwalk_p)),
    "git_revwalk_push": (c_int, (git_revwalk_p, git_oid_p)),
    "git_revwalk_sorting": (c_int, (git_revwalk_p, c_uint)),
    "git_signature_default": (c_int, (git_signature_p_p, git_repository_p)),
    "git_signature_now": (c_int, (git_signature_p_p, c_char_p, c_char_p)),
    "git_status_byindex": (git_status_entry_p, (git_status_list_p, c_size_t)),
    "git_status_file": (c_int, (POINTER(c_uint), git_repository_p, c_char_p)),
    "git_status_list_entrycount": (c_size_t, (git_status_list_p,)),
    "git_status_list_free": (None, (git_status_list_p,)),
    "git_status_list_new": (c_int, (git_status_list_p_p, git_repository_p, git_status_options_p)),
    "git_status_options_init": (c_int, (git_status_options_p, c_uint)),
    "git_tag_free": (None, (git_tag_p,)),
    "git_tree_entry_byindex": (git_tree_entry_p, (git_tree_p, c_size_t)),
    "git_tree_entry_bypath": (c_int, (git_tree_entry_p_p, git_tree_p, c_char_p)),
    "git_tree_entry_dup": (c_int, (git_tree_entry_p_p, git_tree_entry_p)),
    "git_tree_entry_filemode": (git_filemode_t, (git_tree_entry_p,)),
    "git_tree_entry_free": (None, (git_tree_entry_p,)),
    "git_tree_entry_name": (c_char_p, (git_tree_entry_p,)),
    "git_tree_entry_to_object": (c_int, (git_object_p_p, git_repository_p, git_tree_entry_p)),
    "git_tree_entrycount": (c_size_t, (git_tree_p,)),
    "git_tree_free": (None, (git_tree_p,)),
}


# Set up native function argument types.


try:
    install_func_decls(lib, FUNC_DECLS)
except Exception as exc:  # pragma: no cover
    raise ImportError from exc
