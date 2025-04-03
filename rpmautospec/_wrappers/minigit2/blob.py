"""Minimal wrapper for libgit2 - Blob"""

from ctypes import c_char, memmove
from functools import cached_property
from typing import Optional

from .native_adaptation import git_blob_p, git_object_t, lib
from .object_ import Object


class Blob(Object):
    """Represent a git blob."""

    _libgit2_native_finalizer = "git_blob_free"

    _object_type = git_blob_p
    _object_t = git_object_t.BLOB

    _real_native: Optional[git_blob_p] = None

    @cached_property
    def data(self) -> bytes:
        rawsize = lib.git_blob_rawsize(self._native)
        rawcontent_p = lib.git_blob_rawcontent(self._native)
        self.raise_if_error(not rawcontent_p, "Error accessing blob content: {message}")

        buf = (c_char * rawsize)()
        memmove(buf, rawcontent_p, rawsize)
        return bytes(buf)
