import ctypes
from contextlib import nullcontext
from enum import IntEnum
from typing import Optional
from unittest import mock

import pytest

from rpmautospec.minigit2 import exc, native_adaptation

from .common import get_param_id_from_request


class TestIntEnumMixin:
    def test_from_param(self):
        class TestEnum(native_adaptation.IntEnumMixin, IntEnum):
            VALUE = 1

        result = TestEnum.from_param(TestEnum.VALUE)
        assert type(result) is int
        assert result == 1


class TestNativeAdaptation:
    @pytest.mark.parametrize(
        "success, found, soname",
        (
            pytest.param(True, True, "reallib", id="success-real-lib"),
            pytest.param(True, True, "libgit2.so.1.9", id="success"),
            pytest.param(True, True, "libgit2.so.1.9.5", id="success-max-version-with-minor"),
            pytest.param(True, True, "libgit2.so.1.10", id="success-version-unknown"),
            pytest.param(False, False, None, id="failure-libgit2-not-found"),
            pytest.param(False, True, "LIBGIT2.DLL", id="failure-illegal-soname"),
            pytest.param(False, True, "libgit2.so.1.0", id="failure-version-too-low"),
        ),
    )
    def test__setup_lib(
        self, success: bool, found: bool, soname: Optional[str], request: pytest.FixtureRequest
    ) -> None:
        testcase = get_param_id_from_request(request)

        CDLL_wraps = ctypes.CDLL if not soname else None

        with (
            mock.patch.object(native_adaptation, "_soname") as soname_sentinel,
            mock.patch.object(native_adaptation, "lib") as lib_sentinel,
            mock.patch.object(native_adaptation, "version"),
            mock.patch.object(native_adaptation, "version_tuple"),
            mock.patch.object(
                native_adaptation, "find_library", wraps=ctypes.util.find_library
            ) as find_library,
            mock.patch.object(native_adaptation, "CDLL", wraps=CDLL_wraps) as CDLL,
        ):
            if success:
                if "version-unknown" in testcase:
                    expectation = pytest.warns(exc.Libgit2VersionWarning)
                else:
                    expectation = nullcontext()
            else:
                if "libgit2-not-found" in testcase:
                    expectation = pytest.raises(exc.Libgit2NotFoundError)
                elif "illegal-soname" in testcase or "version-too-low" in testcase:
                    expectation = pytest.raises(exc.Libgit2VersionError)

            if soname != "reallib":
                find_library.return_value = soname

            with expectation:
                native_adaptation._setup_lib()

            if success:
                if soname != "reallib":
                    CDLL.assert_called_once_with(soname)
                else:
                    CDLL.assert_called_once()

                if CDLL_wraps:
                    assert isinstance(native_adaptation.lib, ctypes.CDLL)
                    assert native_adaptation.lib._name.startswith("libgit2.so.")
                else:
                    assert native_adaptation.lib is CDLL.return_value
            else:
                assert native_adaptation._soname is soname_sentinel
                assert native_adaptation.lib is lib_sentinel

    def test__install_func_decls(self) -> None:
        with mock.patch.object(native_adaptation, "lib") as lib:
            native_adaptation._install_func_decls()

            for func_name, (restype, argtypes) in native_adaptation.FUNC_DECLS.items():
                func = getattr(lib, func_name)
                assert func.restype == restype
                assert func.argtypes == argtypes
