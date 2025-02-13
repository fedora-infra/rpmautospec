from unittest import mock

import pytest

from rpmautospec.minigit2.native_adaptation import git_signature_p, lib
from rpmautospec.minigit2.signature import Signature


@pytest.fixture
def native_sig() -> git_signature_p:
    native = git_signature_p()
    user = b"Some User"
    email = b"someuser@example.com"

    error_code = lib.git_signature_now(native, user, email)
    assert error_code == 0

    return native


class TestSignature:
    @pytest.mark.parametrize("with_owner", (True, False), ids=("with-owner", "without-owner"))
    def test_everything(self, with_owner: bool, native_sig: git_signature_p) -> None:
        if with_owner:
            owner = mock.Mock(message_encoding="ascii")
        else:
            owner = None

        sig = Signature._from_native(native=native_sig, _owner=owner)

        assert sig.name == "Some User"
        assert sig.email == "someuser@example.com"

        if with_owner:
            assert sig.encoding == "ascii"
            lib.git_signature_free(native_sig)
        else:
            assert sig.encoding == "utf-8"
