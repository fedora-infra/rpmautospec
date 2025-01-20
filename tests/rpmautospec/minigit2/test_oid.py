import ctypes
from contextlib import nullcontext
from random import randbytes

import pytest

from rpmautospec.minigit2 import constants
from rpmautospec.minigit2.native_adaptation import git_oid
from rpmautospec.minigit2.oid import Oid


class TestOid:
    @pytest.mark.parametrize(
        "testcase",
        ("native", "oid", "oid-as-str", "oid-as-bytes", "none", "native-and-oid"),
    )
    def test___init__(self, testcase: str):
        native_in = oid_in = None
        success = True

        oid_bytes = randbytes(constants.GIT_OID_SHA1_SIZE)
        oid_hex = "".join(f"{x:02x}" for x in oid_bytes)

        if "native" in testcase:
            oid_bytearray = bytearray(oid_bytes)
            native_oid = git_oid.from_buffer_copy(oid_bytearray)
            native_in = ctypes.pointer(native_oid)

        if "oid" in testcase:
            oid_in = oid_hex
            if "oid-as-bytes" in testcase:
                oid_in = oid_in.encode("ascii")
            elif "oid-as-str" not in testcase:
                oid_in = Oid(oid=oid_in)

        if "none" in testcase or "and" in testcase:
            expectation = pytest.raises(
                ValueError, match="Exactly one of native or oid has to be specified"
            )
            success = False
        else:
            expectation = nullcontext()

        with expectation:
            oid = Oid(native=native_in, oid=oid_in)

        if success:
            assert oid.hex == str(oid) == oid_hex
            assert oid.hexb == oid_hex.encode("ascii")

    def test___eq__(self) -> None:
        oid_hex = "".join(f"{x:02x}" for x in randbytes(constants.GIT_OID_SHA1_SIZE))

        assert Oid(oid=oid_hex) == Oid(oid=oid_hex)

    def test_hexb_hex___str__(self) -> None:
        oid_hex = "".join(f"{x:02x}" for x in randbytes(constants.GIT_OID_SHA1_SIZE))
        oid = Oid(oid=oid_hex)

        assert oid.hexb == oid_hex.encode("ascii")
        assert oid.hex == oid_hex
        assert str(oid) == oid_hex

    def test___repr__(self) -> None:
        oid_hex = "".join(f"{x:02x}" for x in randbytes(constants.GIT_OID_SHA1_SIZE))
        oid = Oid(oid=oid_hex)

        assert repr(oid) == f"Oid(oid={oid_hex!r})"
