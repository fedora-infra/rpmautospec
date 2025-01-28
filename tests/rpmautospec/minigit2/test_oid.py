import ctypes
from random import randbytes

import pytest

from rpmautospec.minigit2 import constants
from rpmautospec.minigit2.native_adaptation import git_oid
from rpmautospec.minigit2.oid import Oid


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

    def test___eq__(self) -> None:
        oid_hex = "".join(f"{x:02x}" for x in randbytes(constants.GIT_OID_SHA1_SIZE))

        assert Oid._from_oid(oid_hex) == Oid._from_oid(oid_hex)

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
