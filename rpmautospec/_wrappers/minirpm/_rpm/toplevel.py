from ctypes import byref, c_char_p, c_void_p, cast
from io import IOBase
from typing import Optional

from .exc import RpmError
from .native_adaptation import FILE_p, libc, librpm, librpmio


def setLogFile(file: Optional[IOBase]) -> None:
    if file:
        fileno = file.fileno()
        fp = libc.fdopen(fileno, b"a")
        if not fp:
            raise IOError
    else:
        fp = FILE_p()  # NULL

    librpmio.rpmlogSetFile(fp)


def reloadConfig() -> bool:
    librpmio.rpmFreeMacros(None)
    librpm.rpmFreeRpmrc()
    errcode = librpm.rpmReadConfigFiles(None, None)
    return errcode == 0


def addMacro(name: str, value: str) -> None:
    librpmio.rpmPushMacro(None, name.encode("utf-8"), None, value.encode("utf-8"), -1)


def expandMacro(macro: str) -> str:
    expanded = c_char_p()
    errcode = librpmio.rpmExpandMacros(None, macro.encode("utf-8"), byref(expanded), 0)
    if errcode < 0:
        raise RpmError("error expanding macro")
    decoded = expanded.value.decode("utf-8", errors="surrogateescape")
    libc.free(cast(expanded, c_void_p))
    return decoded
