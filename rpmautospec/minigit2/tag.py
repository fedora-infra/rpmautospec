"""Minimal wrapper for libgit2 - Tag"""

from typing import Optional

from .native_adaptation import git_object_t, git_tag_p
from .object_ import Object


class Tag(Object):
    """Represent a git tag."""

    _libgit2_native_finalizer = "git_tag_free"

    _object_type = git_tag_p
    _object_t = git_object_t.TAG

    _real_native: Optional[git_tag_p] = None
