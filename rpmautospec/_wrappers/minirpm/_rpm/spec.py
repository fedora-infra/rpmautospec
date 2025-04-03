from os import PathLike, fspath
from typing import Optional, Union

from .header import Header
from .native_adaptation import librpmbuild, rpmSpec, rpmSpecFlags


class Spec:
    _native: Optional[rpmSpec] = None

    def __init__(
        self,
        specfile: Union[PathLike, str],
        flags: rpmSpecFlags = rpmSpecFlags.ANYARCH | rpmSpecFlags.FORCE,
    ) -> None:
        specfile = fspath(specfile).encode("utf-8")
        _native = librpmbuild.rpmSpecParse(specfile, flags, None)
        if not _native:
            raise ValueError("can't parse specfile\n")
        self._native = _native

    def __del__(self) -> None:
        if self._native:
            librpmbuild.rpmSpecFree(self._native)
            self._native = None

    @property
    def sourceHeader(self) -> Header:
        native = librpmbuild.rpmSpecSourceHeader(self._native)
        return Header(obj=native)
