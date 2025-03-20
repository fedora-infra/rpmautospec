"""Minimal wrapper for libgit2 - Exceptions and Warnings"""


class Libgit2Error(Exception):
    pass


class Libgit2NotFoundError(Libgit2Error):
    pass


class Libgit2VersionError(Libgit2Error):
    pass


class Libgit2VersionWarning(UserWarning):
    pass


# Exception classes present in pygit2


class AlreadyExistsError(ValueError):
    pass


class GitError(Exception):
    pass


class InvalidSpecError(ValueError):
    pass
