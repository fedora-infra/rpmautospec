from contextlib import nullcontext
from enum import IntEnum
from unittest import mock

import pytest

from rpmautospec.minigit2 import exc, native_adaptation


class TestIntEnumMixin:
    def test_from_param(self):
        class TestEnum(native_adaptation.IntEnumMixin, IntEnum):
            VALUE = 1

        result = TestEnum.from_param(TestEnum.VALUE)
        assert type(result) is int
        assert result == 1


class TestNativeAdaptation:
    @pytest.mark.parametrize(
        "testcase",
        (
            "explicit",
            "explicit-older",
            "implicit",
            "implicit-not-found",
            "implicit-illegal-soname",
            "implicit-version-too-low",
            "implicit-version-too-high",
        ),
    )
    def test__setup_lib(self, testcase: str) -> None:
        explicit = "explicit" in testcase

        older = "older" in testcase
        not_found = "not-found" in testcase
        illegal_soname = "illegal-soname" in testcase
        version_too_low = "version-too-low" in testcase
        version_too_high = "version-too-high" in testcase

        success = True
        expectation = nullcontext()
        if not_found:
            success = False
            expectation = pytest.raises(exc.Libgit2NotFoundError)
        elif illegal_soname or version_too_low:
            success = False
            expectation = pytest.raises(exc.Libgit2VersionError)
        elif version_too_high:
            expectation = pytest.warns(exc.Libgit2VersionWarning)

        mock_lib = mock.Mock()
        in_explicit = True

        SONAME_KNOWN_HIGHEST = f"libgit2.so.{native_adaptation.LIBGIT2_MAX_VERSION_STR}"
        SONAME_KNOWN_LOWEST = f"libgit2.so.{native_adaptation.LIBGIT2_MIN_VERSION_STR}"

        VERSION_TOO_LOW = tuple(str(v) for v in native_adaptation.LIBGIT2_MIN_VERSION[:-1]) + (
            str(native_adaptation.LIBGIT2_MIN_VERSION[-1] - 1),
        )
        SONAME_TOO_LOW = "libgit2.so." + ".".join(VERSION_TOO_LOW)

        VERSION_TOO_HIGH = tuple(str(v) for v in native_adaptation.LIBGIT2_MAX_VERSION[:-1]) + (
            str(native_adaptation.LIBGIT2_MAX_VERSION[-1] + 1),
        )
        SONAME_TOO_HIGH = "libgit2.so." + ".".join(VERSION_TOO_HIGH)

        def mock_CDLL(soname: str):
            nonlocal in_explicit

            if explicit:
                if in_explicit and (
                    older
                    and soname == SONAME_KNOWN_LOWEST
                    or not older
                    and soname == SONAME_KNOWN_HIGHEST
                ):
                    return mock_lib
            else:
                if not in_explicit:
                    return mock_lib

            raise OSError(f"{soname}: cannot open shared object file: No such file or directory")

        def mock_find_library(name: str):
            nonlocal in_explicit

            in_explicit = False

            if not_found:
                return None

            if illegal_soname:
                return "Hello-ho!"

            if version_too_low:
                return SONAME_TOO_LOW

            if version_too_high:
                print("version_too_high")
                return SONAME_TOO_HIGH

            print("default")
            return SONAME_KNOWN_HIGHEST

        with (
            mock.patch.object(native_adaptation, "CDLL", wraps=mock_CDLL) as CDLL,
            mock.patch.object(
                native_adaptation, "find_library", wraps=mock_find_library
            ) as find_library,
            mock.patch.object(native_adaptation, "_soname") as _soname,
            mock.patch.object(native_adaptation, "lib") as lib,
            mock.patch.object(native_adaptation, "version") as version,
            mock.patch.object(native_adaptation, "version_tuple") as version_tuple,
            expectation,
        ):
            native_adaptation._setup_lib()

            CDLL.assert_any_call(SONAME_KNOWN_HIGHEST)
            if not explicit:
                CDLL.assert_any_call(SONAME_KNOWN_LOWEST)
                find_library.assert_called_once_with("git2")
            else:
                find_library.assert_not_called()

            if success:
                if explicit:
                    if older:
                        assert native_adaptation._soname == SONAME_KNOWN_LOWEST
                        assert (
                            native_adaptation.version == native_adaptation.LIBGIT2_MIN_VERSION_STR
                        )
                    else:
                        assert native_adaptation._soname == SONAME_KNOWN_HIGHEST
                        assert (
                            native_adaptation.version == native_adaptation.LIBGIT2_MAX_VERSION_STR
                        )
                else:
                    if version_too_high:
                        assert native_adaptation._soname == SONAME_TOO_HIGH
                    else:
                        assert native_adaptation._soname == SONAME_KNOWN_HIGHEST

                assert native_adaptation.lib is mock_lib
                assert native_adaptation.version == ".".join(
                    str(x) for x in native_adaptation.version_tuple
                )
            else:
                assert native_adaptation._soname is _soname
                assert native_adaptation.lib is lib
                assert native_adaptation.version is version
                assert native_adaptation.version_tuple is version_tuple

    def test__install_func_decls(self) -> None:
        with mock.patch.object(native_adaptation, "lib") as lib:
            native_adaptation._install_func_decls()

            for func_name, (restype, argtypes) in native_adaptation.FUNC_DECLS.items():
                func = getattr(lib, func_name)
                assert func.restype == restype
                assert func.argtypes == argtypes
