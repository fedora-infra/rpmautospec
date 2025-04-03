from contextlib import nullcontext
from ctypes import c_int
from enum import IntEnum
from unittest import mock

import pytest

from rpmautospec._wrappers import common


class TestIntEnumMixin:
    def test_from_param(self):
        class TestEnum(common.IntEnumMixin, IntEnum):
            VALUE = 1

        result = TestEnum.from_param(TestEnum.VALUE)
        assert type(result) is int
        assert result == 1


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
        "implicit-version-too-high-fails-unknown",
        "no-known-versions",
    ),
)
def test_load_lib(testcase: str) -> None:
    explicit = "explicit" in testcase

    older = "older" in testcase
    not_found = "not-found" in testcase
    illegal_soname = "illegal-soname" in testcase
    version_too_low = "version-too-low" in testcase
    version_too_high = "version-too-high" in testcase
    fails_unknown = "fails-unknown" in testcase

    no_known_versions = "no-known-versions" in testcase

    success = True
    expectation = nullcontext()
    if not_found:
        success = False
        expectation = pytest.raises(common.LibNotFoundError)
    elif illegal_soname or version_too_low or version_too_high and fails_unknown:
        success = False
        expectation = pytest.raises(common.LibVersionError)
    elif version_too_high:
        expectation = pytest.warns(common.LibVersionWarning)

    # libgit2 is only an example here
    if no_known_versions:
        KNOWN_VERSIONS = None
    else:
        KNOWN_VERSIONS = tuple((1, minor) for minor in range(4, 10))

    SONAME_KNOWN_LOWEST = "libgit2.so.1.4"
    VERSION_KNOWN_LOWEST = "1.4"
    SONAME_TOO_LOW = "libgit2.so.1.3"

    SONAME_KNOWN_HIGHEST = "libgit2.so.1.9"
    VERSION_KNOWN_HIGHEST = "1.9"
    SONAME_TOO_HIGH = "libgit2.so.1.10"

    mock_lib = mock.Mock()
    in_explicit = True

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
            return SONAME_TOO_HIGH

        return SONAME_KNOWN_HIGHEST

    with (
        mock.patch.object(common, "CDLL", wraps=mock_CDLL) as CDLL,
        mock.patch.object(common, "find_library", wraps=mock_find_library) as find_library,
        expectation,
    ):
        lib, soname, version, version_tuple = common.load_lib(
            "git2", known_versions=KNOWN_VERSIONS, load_unknown=not fails_unknown
        )

        CDLL.assert_any_call(SONAME_KNOWN_HIGHEST)
        if not explicit:
            if no_known_versions:
                CDLL.assert_called_once_with(SONAME_KNOWN_HIGHEST)
            else:
                CDLL.assert_any_call(SONAME_KNOWN_LOWEST)
            find_library.assert_called_once_with("git2")
        else:
            find_library.assert_not_called()

        if success:
            if explicit:
                if older:
                    assert soname == SONAME_KNOWN_LOWEST
                    assert version == VERSION_KNOWN_LOWEST
                else:
                    assert soname == SONAME_KNOWN_HIGHEST
                    assert version == VERSION_KNOWN_HIGHEST
            else:
                if version_too_high:
                    assert soname == SONAME_TOO_HIGH
                else:
                    assert soname == SONAME_KNOWN_HIGHEST

            assert lib is mock_lib
            assert version == ".".join(str(x) for x in version_tuple)


def test_install_func_decls() -> None:
    lib = mock.Mock()
    FUNC_DECLS = {
        "foo": (None, (c_int,)),
    }

    common.install_func_decls(lib, FUNC_DECLS)

    for func_name, (restype, argtypes) in FUNC_DECLS.items():
        func = getattr(lib, func_name)
        assert func.restype == restype
        assert func.argtypes == argtypes
