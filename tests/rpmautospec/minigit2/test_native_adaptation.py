from unittest import mock

from rpmautospec.minigit2 import native_adaptation


class TestNativeAdaptation:
    def test_install_func_decls(self) -> None:
        lib = mock.Mock()

        native_adaptation.install_func_decls(lib)

        for func_name, (restype, argtypes) in native_adaptation.FUNC_DECLS.items():
            func = getattr(lib, func_name)
            assert func.restype == restype
            assert func.argtypes == argtypes
