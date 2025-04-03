"""Minimal wrapper around librpm.

This is intended for bootstrapping situations and works as a drop-in
replacement for the `rpm` Python package, but only for the parts used in
rpmautospec.
"""

from ._rpm.header import Header as hdr
from ._rpm.native_adaptation import rpmSourceFlags as _rpmSourceFlags
from ._rpm.native_adaptation import rpmSpecFlags as _rpmSpecFlags
from ._rpm.spec import Spec as spec
from ._rpm.toplevel import addMacro, expandMacro, reloadConfig, setLogFile

# Enums

RPMBUILD_ISSOURCE = _rpmSourceFlags.ISSOURCE
RPMBUILD_ISPATCH = _rpmSourceFlags.ISPATCH
RPMBUILD_ISICON = _rpmSourceFlags.ISICON
RPMBUILD_ISNO = _rpmSourceFlags.ISNO

RPMSPEC_NONE = _rpmSpecFlags.NONE
RPMSPEC_ANYARCH = _rpmSpecFlags.ANYARCH
RPMSPEC_FORCE = _rpmSpecFlags.FORCE
RPMSPEC_NOLANG = _rpmSpecFlags.NOLANG
RPMSPEC_NOUTF8 = _rpmSpecFlags.NOUTF8
RPMSPEC_NOFINALIZE = _rpmSpecFlags.NOFINALIZE
