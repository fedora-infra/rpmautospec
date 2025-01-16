from ctypes import byref, c_char, c_char_p, c_int, cast, memmove
from typing import Union

from .native_adaptation import git_buf, git_libgit2_opt_t
from .wrapper import LibraryUser


class SearchPathList(LibraryUser):
    def __getitem__(self, key: int) -> str:
        buf = git_buf()
        buf_p = byref(buf)

        error_code = self._lib.git_libgit2_opts(
            git_libgit2_opt_t.GET_SEARCH_PATH,
            c_int(key),
            buf_p,
        )
        print(f"{error_code=}")
        self.raise_if_error(error_code, "Error retrieving search path: {message}")

        path_encoded = (c_char * buf.size)()
        memmove(path_encoded, buf.ptr, buf.size)
        self._lib.git_buf_dispose(buf_p)
        return bytes(path_encoded).decode(encoding="utf-8", errors="replace")

    def __setitem__(self, key: int, value: Union[str, bytes]) -> None:
        if isinstance(value, str):
            value = value.encode("utf-8")

        error_code = self._lib.git_libgit2_opts(
            git_libgit2_opt_t.SET_SEARCH_PATH,
            c_int(key),
            cast(value, c_char_p),
        )
        self.raise_if_error(error_code)


search_path = SearchPathList()
