from . import native_adaptation

GIT_CHECKOUT_FORCE = native_adaptation.git_checkout_strategy_t.FORCE
GIT_CHECKOUT_OPTIONS_VERSION = 1

GIT_CONFIG_LEVEL_SYSTEM = native_adaptation.git_config_level_t.SYSTEM
GIT_CONFIG_LEVEL_XDG = native_adaptation.git_config_level_t.XDG
GIT_CONFIG_LEVEL_GLOBAL = native_adaptation.git_config_level_t.GLOBAL
GIT_CONFIG_LEVEL_LOCAL = native_adaptation.git_config_level_t.LOCAL

GIT_DIFF_OPTIONS_VERSION = 1

GIT_OID_RAWSZ = GIT_OID_SHA1_SIZE = 20
GIT_OID_HEXSZ = GIT_OID_SHA1_HEXSIZE = GIT_OID_SHA1_SIZE * 2

GIT_REPOSITORY_INIT_OPTIONS_VERSION = 1
GIT_REPOSITORY_OPEN_NO_SEARCH = native_adaptation.git_repository_open_flag_t.NO_SEARCH

GIT_STATUS_CURRENT = native_adaptation.git_status_t.CURRENT
GIT_STATUS_INDEX_NEW = native_adaptation.git_status_t.INDEX_NEW
GIT_STATUS_INDEX_MODIFIED = native_adaptation.git_status_t.INDEX_MODIFIED
GIT_STATUS_INDEX_DELETED = native_adaptation.git_status_t.INDEX_DELETED
GIT_STATUS_INDEX_RENAMED = native_adaptation.git_status_t.INDEX_RENAMED
GIT_STATUS_INDEX_TYPECHANGE = native_adaptation.git_status_t.INDEX_TYPECHANGE
GIT_STATUS_WT_NEW = native_adaptation.git_status_t.WT_NEW
GIT_STATUS_WT_MODIFIED = native_adaptation.git_status_t.WT_MODIFIED
GIT_STATUS_WT_DELETED = native_adaptation.git_status_t.WT_DELETED
GIT_STATUS_WT_TYPECHANGE = native_adaptation.git_status_t.WT_TYPECHANGE
GIT_STATUS_WT_RENAMED = native_adaptation.git_status_t.WT_RENAMED
GIT_STATUS_WT_UNREADABLE = native_adaptation.git_status_t.WT_UNREADABLE
GIT_STATUS_IGNORED = native_adaptation.git_status_t.IGNORED
GIT_STATUS_CONFLICTED = native_adaptation.git_status_t.CONFLICTED

GIT_STATUS_OPT_DEFAULTS = (
    native_adaptation.git_status_opt_t.INCLUDE_IGNORED
    | native_adaptation.git_status_opt_t.INCLUDE_UNTRACKED
    | native_adaptation.git_status_opt_t.RECURSE_UNTRACKED_DIRS
)

GIT_STATUS_OPTIONS_VERSION = 1
