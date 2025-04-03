"""Minimal wrapper for libgit2 - Config"""

from os import PathLike, fspath
from typing import Optional, Union

from .native_adaptation import git_config_entry_p, git_config_p, git_error_code, lib
from .wrapper import WrapperOfWrappings


class Config(WrapperOfWrappings):
    """Represent a git configuration file."""

    _libgit2_native_finalizer = "git_config_free"

    _real_native: Optional[git_config_p]

    def _get(self, key: str) -> tuple[int, git_config_entry_p]:
        native = git_config_entry_p()
        error_code = lib.git_config_get_entry(native, self._native, key.encode("utf-8"))
        return error_code, native

    def _get_entry(self, key: str) -> git_config_entry_p:
        error_code, native = self._get(key)
        self.raise_if_error(error_code)
        return native

    def __contains__(self, key: str) -> bool:
        error_code, native = self._get(key)
        if error_code == git_error_code.ENOTFOUND:
            return False
        self.raise_if_error(error_code)
        lib.git_config_entry_free(native)
        return True

    def __getitem__(self, key: str) -> str:
        native = self._get_entry(key)
        value = native.contents.value.decode("utf-8")
        lib.git_config_entry_free(native)
        return value

    def __setitem__(self, key: str, value: Union[bool, int, str, bytes, PathLike]) -> None:
        key = key.encode("utf-8")

        if isinstance(value, bool):
            error_code = lib.git_config_set_bool(self._native, key, value)
        elif isinstance(value, int):
            error_code = lib.git_config_set_int64(self._native, key, value)
        else:  # isinstance(value, Union[str, bytes, PathLike])
            value = fspath(value)
            if isinstance(value, str):
                value = value.encode("utf-8")
            error_code = lib.git_config_set_string(self._native, key, value)

        self.raise_if_error(error_code)

    def __delitem__(self, key: str) -> None:
        error_code = lib.git_config_delete_entry(self._native, key.encode("utf-8"))
        self.raise_if_error(error_code)
