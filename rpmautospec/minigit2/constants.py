from . import native_adaptation

GIT_DIFF_OPTIONS_VERSION = 1

GIT_OID_RAWSZ = GIT_OID_SHA1_SIZE = 20
GIT_OID_HEXSZ = GIT_OID_SHA1_HEXSIZE = GIT_OID_SHA1_SIZE * 2

GIT_REPOSITORY_OPEN_NO_SEARCH = native_adaptation.git_repository_open_flag_t.NO_SEARCH
