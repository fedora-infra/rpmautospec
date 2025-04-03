import re
from collections.abc import Sequence
from ctypes import CDLL
from ctypes.util import find_library
from typing import Optional
from warnings import warn


class LibError(Exception):
    pass


class LibNotFoundError(LibError):
    pass


class LibVersionError(LibError):
    pass


class LibWarning(UserWarning):
    pass


class LibVersionWarning(LibWarning):
    pass


class IntEnumMixin:
    @classmethod
    def from_param(cls, obj):
        return int(obj)


def load_lib(
    name: str, *, known_versions: Optional[Sequence[tuple[int]]] = None, load_unknown: bool = True
) -> (CDLL, str, str, tuple[int]):
    """Load a library, optionally filtering by known versions

    :param name: Name of the library (without "lib")
    :param known_versions: Sequence of version tuples which should be loaded
        preferentially, ordered from old to new
    :param load_unknown: If unknown newer versions than the known should be
        loaded

    :return: Tuple of: library object, soname, version string and tuple
    """

    lib = None

    for _version_tuple in reversed(known_versions or ()):
        # Prefer known to unknown versions
        _version = ".".join(str(num) for num in _version_tuple)
        soname = f"lib{name}.so.{_version}"
        try:
            lib = CDLL(soname)
        except Exception:
            continue
        else:
            soname = soname
            version_tuple = _version_tuple
            version = _version
            break

    if not lib:
        soname = find_library(name)
        if not soname:
            raise LibNotFoundError(f"lib{name} not found")
        if not (match := re.match(rf"lib{name}\.so\.(?P<version>\d+(?:\.\d+)*)", soname)):
            raise LibVersionError(f"Can’t parse lib{name} version: {soname}")
        version = match.group("version")
        version_tuple = tuple(int(x) for x in match.group("version").split("."))

        if known_versions:
            lib_min_version = known_versions[0]
            lib_max_version = known_versions[-1]

            if lib_min_version > version_tuple:
                lib_min_version_str = ".".join(str(x) for x in lib_min_version)
                raise LibVersionError(
                    f"Version {version} of lib{name} too low (must be ≥ {lib_min_version_str})"
                )

            if lib_max_version < version_tuple[: len(lib_max_version)]:
                lib_max_version_str = ".".join(str(x) for x in lib_max_version)
                msg = (
                    f"Version {version} of lib{name} is unknown (latest known is"
                    + f" {lib_max_version_str})."
                )
                if load_unknown:
                    warn(msg, LibVersionWarning)
                else:
                    raise LibVersionError(msg)

        lib = CDLL(soname)

    return lib, soname, version, version_tuple


def install_func_decls(lib: CDLL, decls: dict[str, tuple]) -> None:
    for func_name, (restype, argtypes) in decls.items():
        func = getattr(lib, func_name)
        func.restype = restype
        func.argtypes = argtypes
