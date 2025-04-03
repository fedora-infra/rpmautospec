import ctypes
from random import randbytes

import pytest

from rpmautospec._wrappers.minigit2 import constants
from rpmautospec._wrappers.minigit2.native_adaptation import git_oid
from rpmautospec._wrappers.minigit2.oid import Oid


class TestOid:
    def test___init__(self) -> None:
        oid_bytes = randbytes(constants.GIT_OID_SHA1_SIZE)
        oid_hex = "".join(f"{x:02x}" for x in oid_bytes)
        oid_bytearray = bytearray(oid_bytes)
        native_oid = git_oid.from_buffer_copy(oid_bytearray)
        native_in = ctypes.pointer(native_oid)

        oid = Oid(native_in)

        assert oid.hex == str(oid) == oid_hex
        assert oid.hexb == oid_hex.encode("ascii")

    @pytest.mark.parametrize("testcase", ("oid", "oid-as-str", "oid-as-bytes"))
    def test__from_oid(self, testcase: str) -> None:
        oid_bytes = randbytes(constants.GIT_OID_SHA1_SIZE)
        oid_hex = "".join(f"{x:02x}" for x in oid_bytes)
        oid_in = oid_hex
        if "oid-as-bytes" in testcase:
            oid_in = oid_in.encode("ascii")
        elif "oid-as-str" not in testcase:
            oid_in = Oid._from_oid(oid=oid_in)

        oid = Oid._from_oid(oid_in)

        assert oid.hex == str(oid) == oid_hex
        assert oid.hexb == oid_hex.encode("ascii")

    @pytest.mark.parametrize("other_type", (Oid, str, bytes))
    def test___eq__(self, other_type: type) -> None:
        oid_hex = "".join(f"{x:02x}" for x in randbytes(constants.GIT_OID_SHA1_SIZE))

        self = Oid._from_oid(oid_hex)
        other = Oid._from_oid(oid_hex)

        if other_type is bytes:
            other = other.hexb
        elif other_type is str:
            other = other.hex

        assert self == other

    def test_hexb_hex___str__(self) -> None:
        oid_hex = "".join(f"{x:02x}" for x in randbytes(constants.GIT_OID_SHA1_SIZE))
        oid = Oid._from_oid(oid_hex)

        assert oid.hexb == oid_hex.encode("ascii")
        assert oid.hex == oid_hex
        assert str(oid) == oid_hex

    def test___repr__(self) -> None:
        oid_hex = "".join(f"{x:02x}" for x in randbytes(constants.GIT_OID_SHA1_SIZE))
        oid = Oid._from_oid(oid_hex)

        assert repr(oid) == f"Oid._from_oid({oid_hex!r})"
