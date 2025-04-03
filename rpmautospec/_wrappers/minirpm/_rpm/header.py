from typing import Optional

from .exc import RpmError
from .native_adaptation import Header as _Header
from .native_adaptation import errmsg_t, librpm


class Header:
    _native: Optional[_Header] = None

    def __init__(self, obj: _Header) -> None:
        self._native = librpm.headerLink(obj)

    def __del__(self) -> None:
        if self._native:
            librpm.headerFree(self._native)
            self._native = None

    def format(self, format: str) -> str:
        errmsg_encoded = errmsg_t()
        encoded = librpm.headerFormat(
            self._native, format.encode("utf-8", errors="surrogateescape"), errmsg_encoded
        )

        if not encoded:
            # Don’t free errmsg_encoded, it points to thread-local storage managed by librpm.
            raise RpmError(errmsg_encoded.value.decode("utf-8", errors="surrogateescape"))

        return encoded.decode("utf-8", errors="surrogateescape")
