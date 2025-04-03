from contextlib import nullcontext
from unittest import mock

import pytest

from rpmautospec._wrappers.minirpm._rpm import exc, header


class TestHeader:
    def test___init__(self):
        sentinel = object()
        linked_sentinel = object()

        with mock.patch.object(header, "librpm") as librpm:
            librpm.headerLink.return_value = linked_sentinel

            hdr = header.Header(sentinel)

            assert hdr._native is linked_sentinel
            hdr.__del__()

            librpm.headerLink.assert_called_once_with(sentinel)

    def test___del__(self):
        sentinel = object()
        linked_sentinel = object()

        with mock.patch.object(header, "librpm") as librpm:
            librpm.headerLink.return_value = linked_sentinel

            hdr = header.Header(sentinel)
            hdr.__del__()
            assert hdr._native is None
            hdr.__del__()

            librpm.headerFree.assert_called_once_with(linked_sentinel)

    @pytest.mark.parametrize("success", (True, False), ids=("success", "failure"))
    def test_format(self, success: bool):
        sentinel = object()
        linked_sentinel = object()

        with (
            mock.patch.object(header, "librpm") as librpm,
            mock.patch.object(header, "errmsg_t") as errmsg_t,
        ):
            librpm.headerLink.return_value = linked_sentinel
            errmsg_encoded = errmsg_t.return_value
            if success:
                librpm.headerFormat.return_value = b"Boo"
                expectation = nullcontext()
            else:
                errmsg_encoded.value = b"What?"
                librpm.headerFormat.return_value = None
                expectation = pytest.raises(exc.RpmError, match="What?")

            hdr = header.Header(sentinel)
            with expectation:
                retval = hdr.format("%{boo}")

            hdr.__del__()

            librpm.headerFormat.assert_called_once_with(linked_sentinel, b"%{boo}", errmsg_encoded)

            if success:
                assert retval == "Boo"
