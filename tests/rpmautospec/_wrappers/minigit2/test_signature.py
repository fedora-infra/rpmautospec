import datetime as dt
import math
import time
from unittest import mock

import pytest

from rpmautospec._wrappers.minigit2.native_adaptation import git_signature_p, lib
from rpmautospec._wrappers.minigit2.signature import Signature


@pytest.fixture
def native_sig() -> git_signature_p:
    native = git_signature_p()
    user = b"Some User"
    email = b"someuser@example.com"

    error_code = lib.git_signature_now(native, user, email)
    assert error_code == 0

    return native


class TestSignature:
    @pytest.mark.parametrize("str_type", (str, bytes))
    @pytest.mark.parametrize("with_time", (True, False), ids=("with-time", "without-time"))
    @pytest.mark.parametrize(
        "with_encoding", (True, False), ids=("with-encoding", "without-encoding")
    )
    def test___init__(self, str_type: type, with_time: bool, with_encoding: bool) -> None:
        if str_type is bytes:
            name = b"Name"
            email = b"e@mail"
        else:
            name = "Name"
            email = "e@mail"

        before = math.floor(time.time())
        sig = Signature(
            name=name,
            email=email,
            time=0 if with_time else None,
            encoding="utf-8" if with_encoding else None,
        )
        after = math.ceil(time.time())

        assert sig.name == "Name"
        assert sig.email == "e@mail"
        if with_time:
            assert sig.time == 0
            assert sig.offset == 0
        else:
            # Give the “now” timestamp some wiggle room
            assert before - 10 <= sig.time <= after + 10
            # Signature.offset depends on the local time zone, its value can be anything.
            sig_dt = dt.datetime.fromtimestamp(sig.time).astimezone()
            tzoffset = sig_dt.tzinfo.utcoffset(sig_dt)
            tzoffset_minutes = int(tzoffset.total_seconds() / 60)
            assert sig.offset == tzoffset_minutes

    @pytest.mark.parametrize(
        "with_owner, with_owner_encoding",
        (
            pytest.param(True, True, id="with-owner"),
            pytest.param(True, False, id="with-owner-without-encoding"),
            pytest.param(False, False, id="without-owner"),
        ),
    )
    def test_everything_else(
        self, with_owner: bool, with_owner_encoding: bool, native_sig: git_signature_p
    ) -> None:
        if with_owner:
            owner = mock.Mock()
            if with_owner_encoding:
                owner.message_encoding = "ascii"
            else:
                del owner.message_encoding
        else:
            owner = None

        sig = Signature._from_native(native=native_sig, _owner=owner)

        assert sig.name == "Some User"
        assert sig.email == "someuser@example.com"

        if with_owner:
            assert sig.encoding == "ascii" if with_owner_encoding else "utf-8"
            lib.git_signature_free(native_sig)
        else:
            assert sig.encoding == "utf-8"
