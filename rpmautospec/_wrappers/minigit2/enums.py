from enum import IntEnum, IntFlag

from . import native_adaptation

DeltaStatus = native_adaptation.git_delta_t
DiffFlag = native_adaptation.git_diff_flag_t


# The following are monkey-patched in rpmautospec.compat if old pygit2 versions are present. If
# anything is added here, it needs to be added there as well.


class CheckoutStrategy(IntFlag):
    FORCE = native_adaptation.git_checkout_strategy_t.FORCE


class ConfigLevel(IntEnum):
    SYSTEM = native_adaptation.git_config_level_t.SYSTEM
    XDG = native_adaptation.git_config_level_t.XDG
    GLOBAL = native_adaptation.git_config_level_t.GLOBAL
    LOCAL = native_adaptation.git_config_level_t.LOCAL


class FileStatus(IntFlag):
    CURRENT = native_adaptation.git_status_t.CURRENT
    INDEX_NEW = native_adaptation.git_status_t.INDEX_NEW
    INDEX_MODIFIED = native_adaptation.git_status_t.INDEX_MODIFIED
    INDEX_DELETED = native_adaptation.git_status_t.INDEX_DELETED
    INDEX_RENAMED = native_adaptation.git_status_t.INDEX_RENAMED
    INDEX_TYPECHANGE = native_adaptation.git_status_t.INDEX_TYPECHANGE
    WT_NEW = native_adaptation.git_status_t.WT_NEW
    WT_MODIFIED = native_adaptation.git_status_t.WT_MODIFIED
    WT_DELETED = native_adaptation.git_status_t.WT_DELETED
    WT_TYPECHANGE = native_adaptation.git_status_t.WT_TYPECHANGE
    WT_RENAMED = native_adaptation.git_status_t.WT_RENAMED
    WT_UNREADABLE = native_adaptation.git_status_t.WT_UNREADABLE
    IGNORED = native_adaptation.git_status_t.IGNORED
    CONFLICTED = native_adaptation.git_status_t.CONFLICTED


class RepositoryOpenFlag(IntFlag):
    NO_SEARCH = native_adaptation.git_repository_open_flag_t.NO_SEARCH
