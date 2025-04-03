from ctypes import CDLL, POINTER, Structure, c_char_p, c_int, c_uint32, c_void_p
from enum import IntFlag, auto
from typing import Optional

from ...common import IntEnumMixin, install_func_decls, load_lib

libc: Optional[CDLL] = None
libc_soname: Optional[str] = None
libc_version: Optional[str] = None
libc_version_tuple: Optional[tuple[int]] = None

librpm: Optional[CDLL] = None
librpm_soname: Optional[str] = None
librpm_version: Optional[str] = None
librpm_version_tuple: Optional[tuple[int]] = None

librpmio: Optional[CDLL] = None
librpmio_soname: Optional[str] = None
librpmio_version: Optional[str] = None
librpmio_version_tuple: Optional[tuple[int]] = None

librpmbuild: Optional[CDLL] = None
librpmbuild_soname: Optional[str] = None
librpmbuild_version: Optional[str] = None
librpmbuild_version_tuple: Optional[tuple[int]] = None


try:
    libc, libc_soname, libc_version, libc_version_tuple = load_lib("c")
    librpm, librpm_soname, librpm_version, librpm_version_tuple = load_lib("rpm")
    librpmio, librpmio_soname, librpmio_version, librpmio_version_tuple = load_lib("rpmio")
    librpmbuild, librpmbuild_soname, librpmbuild_version, librpmbuild_version_tuple = load_lib(
        "rpmbuild"
    )
except Exception as exc:  # pragma: no cover
    raise ImportError from exc


# libc types


class FILE(Structure):
    pass


FILE_p = POINTER(FILE)


# librpm* types

errmsg_t = c_char_p
rpmFlags = c_uint32


class rpmSourceFlags(IntEnumMixin, IntFlag):
    ISSOURCE = 1 << 0
    ISPATCH = auto()
    ISICON = auto()
    ISNO = auto()


class rpmSpecFlags(IntEnumMixin, IntFlag):
    NONE = 0
    ANYARCH = 1 << 0
    FORCE = auto()
    NOLANG = auto()
    NOUTF8 = auto()
    NOFINALIZE = auto()


class headerToken_s(Structure):
    pass


Header = POINTER(headerToken_s)


class rpmSpec_s(Structure):
    pass


rpmSpec = POINTER(rpmSpec_s)


# Native function declarations

LIBC_FUNC_DECLS = {
    "fdopen": (FILE_p, (c_int, c_char_p)),
    "free": (None, (c_void_p,)),
}

# The librpm* *Free() functions are actually `someObj someObjFree(someObj)`, but always return NULL.
LIBRPM_FUNC_DECLS = {
    "headerFormat": (c_char_p, (Header, c_char_p, POINTER(errmsg_t))),
    "headerFree": (None, (Header,)),
    "headerLink": (Header, (Header,)),
    "rpmFreeRpmrc": (None, ()),
    "rpmPushMacro": (c_int, (c_void_p, c_char_p, c_char_p, c_char_p, c_int)),
    "rpmReadConfigFiles": (c_int, (c_char_p, c_char_p)),
    "rpmlogSetFile": (FILE_p, (FILE_p,)),
}

LIBRPMIO_FUNC_DECLS = {
    "rpmExpandMacros": (c_int, (c_void_p, c_char_p, POINTER(c_char_p), c_int)),
    "rpmFreeMacros": (None, (c_void_p,)),
}

LIBRPMBUILD_FUNC_DECLS = {
    "rpmSpecFree": (None, (rpmSpec,)),
    "rpmSpecParse": (rpmSpec, (c_char_p, rpmSpecFlags, c_char_p)),
    "rpmSpecSourceHeader": (Header, (rpmSpec,)),
}


try:
    install_func_decls(libc, LIBC_FUNC_DECLS)
    install_func_decls(librpm, LIBRPM_FUNC_DECLS)
    install_func_decls(librpmio, LIBRPMIO_FUNC_DECLS)
    install_func_decls(librpmbuild, LIBRPMBUILD_FUNC_DECLS)
except Exception as exc:  # pragma: no cover
    raise ImportError from exc
