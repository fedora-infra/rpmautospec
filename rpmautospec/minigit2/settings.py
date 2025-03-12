"""Minimal wrapper for libgit2 - SearchPathList"""

from ctypes import byref, c_char_p, c_int, cast
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import Union

from .native_adaptation import git_buf, git_libgit2_opt_t, lib
from .wrapper import LibraryUser


class SearchPathList(LibraryUser):
    def __getitem__(self, key: int) -> str:
        buf = git_buf()
        buf_p = byref(buf)

        error_code = lib.git_libgit2_opts(
            git_libgit2_opt_t.GET_SEARCH_PATH,
            c_int(key),
            buf_p,
        )
        self.raise_if_error(error_code, "Error retrieving search path: {message}")

        path_encoded = cast(buf.ptr, c_char_p).value
        path_decoded = path_encoded.decode(
            encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
        )
        lib.git_buf_dispose(buf_p)
        return path_decoded

    def __setitem__(self, key: int, value: Union[str, bytes]) -> None:
        if isinstance(value, str):
            value = value.encode(
                encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
            )

        error_code = lib.git_libgit2_opts(git_libgit2_opt_t.SET_SEARCH_PATH, c_int(key), value)
        self.raise_if_error(error_code)


search_path = SearchPathList()
