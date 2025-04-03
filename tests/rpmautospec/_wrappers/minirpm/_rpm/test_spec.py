from contextlib import nullcontext
from unittest import mock

import pytest

from rpmautospec._wrappers.minirpm._rpm import spec


class TestSpec:
    @pytest.mark.parametrize("success", (True, False), ids=("success", "parse-failure"))
    def test___init__(self, success: bool):
        sentinel = object()

        with mock.patch.object(spec, "librpmbuild") as librpmbuild:
            if success:
                librpmbuild.rpmSpecParse.return_value = sentinel
                expectation = nullcontext()
            else:
                librpmbuild.rpmSpecParse.return_value = None
                expectation = pytest.raises(ValueError, match="can't parse specfile")

            flags = object()

            with expectation:
                obj = spec.Spec("/path/to/spec.spec", flags=flags)

            librpmbuild.rpmSpecParse.assert_called_once_with(b"/path/to/spec.spec", flags, None)

            if success:
                assert obj._native is sentinel
                obj.__del__()

    def test___del__(self):
        with mock.patch.object(spec, "librpmbuild") as librpmbuild:
            obj = spec.Spec("/path/to/spec.spec")

            obj.__del__()
            assert obj._native is None
            obj.__del__()

            librpmbuild.rpmSpecFree.assert_called_once_with(librpmbuild.rpmSpecParse.return_value)

    def test_sourceHeader(self):
        with (
            mock.patch.object(spec, "librpmbuild") as librpmbuild,
            mock.patch.object(spec, "Header") as Header,
        ):
            obj = spec.Spec("/path/to/spec.spec")
            assert obj.sourceHeader == Header(obj=librpmbuild.rpmSpecSourceHeader.return_value)
            librpmbuild.rpmSpecSourceHeader.assert_called_once_with(obj._native)

            obj.__del__()
