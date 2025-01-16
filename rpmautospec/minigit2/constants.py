from . import native_adaptation

GIT_CHECKOUT_FORCE = (1 << 1)

GIT_DIFF_OPTIONS_VERSION = 1

GIT_OID_RAWSZ = GIT_OID_SHA1_SIZE = 20
GIT_OID_HEXSZ = GIT_OID_SHA1_HEXSIZE = GIT_OID_SHA1_SIZE * 2

GIT_REPOSITORY_OPEN_NO_SEARCH = native_adaptation.git_repository_open_flag_t.NO_SEARCH

GIT_CONFIG_LEVEL_SYSTEM = native_adaptation.git_config_level_t.SYSTEM
GIT_CONFIG_LEVEL_XDG = native_adaptation.git_config_level_t.XDG
GIT_CONFIG_LEVEL_GLOBAL = native_adaptation.git_config_level_t.GLOBAL
GIT_CONFIG_LEVEL_LOCAL = native_adaptation.git_config_level_t.LOCAL
