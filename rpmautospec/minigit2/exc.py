"""Minimal wrapper for libgit2 - Exceptions and Warnings"""


class Libgit2Error(Exception):
    pass


class Libgit2NotFoundError(Libgit2Error):
    pass


class Libgit2VersionError(Libgit2Error):
    pass


class Libgit2VersionWarning(UserWarning):
    pass


class GitError(Exception):
    pass
