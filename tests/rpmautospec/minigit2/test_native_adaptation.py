from enum import IntEnum
from unittest import mock

import pytest

from rpmautospec.minigit2 import native_adaptation


class TestIntEnumMixin:
    def test_from_param(self):
        class TestEnum(native_adaptation.IntEnumMixin, IntEnum):
            VALUE = 1

        result = TestEnum.from_param(TestEnum.VALUE)
        assert type(result) is int
        assert result == 1


class TestNativeAdaptation:
    @pytest.mark.parametrize(
        "version, oid_type_exists",
        (
            pytest.param((1, 6, 99), False, id="version-1.6.99"),
            pytest.param((1, 7, 0), True, id="version-1.7.0"),
        ),
    )
    def test_apply_version_compat(self, version: tuple[int], oid_type_exists: bool) -> None:
        orig_fields = native_adaptation.git_diff_options._fields_

        if not any(f[0] == "oid_type" for f in orig_fields):
            # Make this test work with libgit2 < 1.7.0
            orig_fields.append(("oid_type", int))

        with mock.patch.object(native_adaptation, "git_diff_options") as git_diff_options:
            git_diff_options._fields_ = tuple(orig_fields)
            native_adaptation.apply_version_compat(version)
            oid_type_is_in_fields = any(f[0] == "oid_type" for f in git_diff_options._fields_)
            if oid_type_exists:
                assert oid_type_is_in_fields
            else:
                assert not oid_type_is_in_fields

    def test_install_func_decls(self) -> None:
        lib = mock.Mock()

        native_adaptation.install_func_decls(lib)

        for func_name, (restype, argtypes) in native_adaptation.FUNC_DECLS.items():
            func = getattr(lib, func_name)
            assert func.restype == restype
            assert func.argtypes == argtypes
