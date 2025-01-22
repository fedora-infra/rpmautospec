import ctypes
import ctypes.util
import gc
from contextlib import nullcontext
from typing import Any, Optional
from unittest import mock

import pytest

from rpmautospec.minigit2 import exc, wrapper
from rpmautospec.minigit2.native_adaptation import git_error_code

from .common import get_param_id_from_request


@pytest.fixture
def uncache_library_obj() -> None:
    with (
        mock.patch.object(wrapper.LibraryUser, "_library_obj"),
        mock.patch.object(wrapper.LibraryUser, "_soname"),
    ):
        try:
            wrapper.LibraryUser._library_obj = None
            wrapper.LibraryUser._soname = None
        except AttributeError:
            pass

        yield


class TestLibraryUser:
    @pytest.mark.parametrize(
        "success, cache_is_hot, found, soname",
        (
            pytest.param(True, False, True, "reallib", id="success-real-lib"),
            pytest.param(True, False, True, "libgit2.so.1.9", id="success"),
            pytest.param(
                True, False, True, "libgit2.so.1.9.5", id="success-max-version-with-minor"
            ),
            pytest.param(True, False, True, "libgit2.so.1.10", id="success-version-unknown"),
            pytest.param(True, True, None, None, id="success-cache-hot"),
            pytest.param(False, False, False, None, id="failure-libgit2-not-found"),
            pytest.param(False, False, True, "LIBGIT2.DLL", id="failure-illegal-soname"),
            pytest.param(False, False, True, "libgit2.so.1.0", id="failure-version-too-low"),
        ),
    )
    @pytest.mark.usefixtures("uncache_library_obj")
    def test__get_library(
        self,
        success: bool,
        cache_is_hot: bool,
        found: bool,
        soname: Optional[str],
        request: pytest.FixtureRequest,
    ) -> None:
        testcase = get_param_id_from_request(request)

        CDLL_wraps = ctypes.CDLL if not soname else None

        with (
            mock.patch.object(
                wrapper, "find_library", wraps=ctypes.util.find_library
            ) as find_library,
            mock.patch.object(wrapper, "CDLL", wraps=CDLL_wraps) as CDLL,
            mock.patch.object(wrapper, "install_func_decls") as install_func_decls,
        ):
            if cache_is_hot:
                wrapper.LibraryUser._library_obj = lib_sentinel = object()

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
                retval = wrapper.WrapperOfWrappings._get_library()

            if success:
                if cache_is_hot:
                    assert retval is lib_sentinel
                    return

                CDLL.assert_called_once()
                install_func_decls.assert_called_once_with(wrapper.LibraryUser._library_obj)

                if CDLL_wraps:
                    assert isinstance(retval, ctypes.CDLL)
                    assert retval._name.startswith("libgit2.so.")

    def test__lib(self) -> None:
        obj = wrapper.WrapperOfWrappings()
        with mock.patch.object(wrapper.WrapperOfWrappings, "_get_library") as _get_library:
            _get_library.return_value = lib_sentinel = object()
            assert obj._lib is lib_sentinel
            _get_library.assert_called_once_with()

    @pytest.mark.parametrize(
        "error_code, exc_msg_tmpl, key, last_error_set",
        (
            pytest.param(git_error_code.OK, None, None, False, id="without-error-code"),
            pytest.param(
                git_error_code.ERROR,
                "Something happened: {message}",
                None,
                True,
                id="with-unspecific-error-code-template",
            ),
            pytest.param(
                git_error_code.EEXISTS,
                None,
                None,
                True,
                id="with-already-exists-error-without-template",
            ),
            pytest.param(git_error_code.ENOTFOUND, None, "fifteen", False, id="with-key-error"),
            pytest.param(git_error_code.ERROR, None, None, False, id="with-unspecified-no-info"),
        ),
    )
    def test_raise_if_error(
        self, error_code: int, exc_msg_tmpl: Optional[str], key: str, last_error_set: bool
    ):
        if error_code:
            if error_code == git_error_code.ENOTFOUND:
                cls = KeyError
            elif error_code == git_error_code.EEXISTS:
                cls = exc.AlreadyExistsError
            else:
                cls = exc.GitError
            expectation = pytest.raises(cls)
        else:
            expectation = nullcontext()

        with mock.patch.object(wrapper.WrapperOfWrappings, "_get_library") as _get_library:
            _get_library.return_value = lib = mock.Mock()
            if last_error_set:
                error_p = mock.Mock()
                error_p.contents.message = b"BOO!"
            else:
                error_p = None
            lib.git_error_last.return_value = error_p

            with expectation as excinfo:
                wrapper.WrapperOfWrappings.raise_if_error(error_code, exc_msg_tmpl, key=key)

        if error_code:
            if error_code == git_error_code.ENOTFOUND:
                lib.git_error_last.assert_not_called()
            else:
                lib.git_error_last.assert_called_once_with()
                exc_str = str(excinfo.value)
                if last_error_set:
                    assert "BOO!" in exc_str
                else:
                    assert "No error information given" in exc_str
                if exc_msg_tmpl:
                    assert "Something happened:" in exc_str
                else:
                    assert "Something happened:" not in exc_str

class TestWrapperOfWrappings:
    @pytest.mark.parametrize("testcase", ("plain", "with-native", "with-_must_free"))
    def test___init__(self, testcase: str) -> None:
        with_native = "with-native" in testcase
        with_must_free = "with-_must_free" in testcase

        native_sentinel = object()
        _must_free_sentinel = object()

        native = native_sentinel if with_native else None
        _must_free = _must_free_sentinel if with_must_free else None

        obj = wrapper.WrapperOfWrappings(native=native, _must_free=_must_free)

        if with_native:
            assert obj._native is native_sentinel
        else:
            assert obj._native is None

        if with_must_free:
            assert obj._must_free is _must_free_sentinel
        else:
            assert obj._must_free is wrapper.WrapperOfWrappings._must_free

    def test___del__(self) -> None:
        mailbox = {"deleted": False}

        class _TestClass(wrapper.WrapperOfWrappings):
            @property
            def _native(self):
                return self._real_native

            @_native.deleter
            def _native(self):
                mailbox["deleted"] = True

        obj = _TestClass()
        del obj

        gc.collect()

        assert mailbox["deleted"]

    @pytest.mark.parametrize("real_native", (None, ctypes.c_void_p(), ctypes.c_void_p(1)))
    def test___bool__(self, real_native: Any) -> None:
        obj = wrapper.WrapperOfWrappings()
        obj._real_native = real_native

        assert bool(obj) is bool(real_native)

    def test__native__getter(self):
        sentinel = object()
        obj = wrapper.WrapperOfWrappings(native=sentinel)
        assert obj._native is sentinel

    @pytest.mark.parametrize(
        "testcase", ("normal", "already-set", "native-not-a-pointer", "set-null")
    )
    def test__native__setter(self, testcase: str) -> None:
        already_set = "already-set" in testcase
        native_is_pointer = "native-not-a-pointer" not in testcase
        set_null = "set-null" in testcase

        class ClassUnderTest(wrapper.WrapperOfWrappings):
            def __repr__(self):
                return "ClassUnderTest()"

        exception_expected = nullcontext()

        if native_is_pointer:
            ClassUnderTest._libgit2_native_finalizer = mock.Mock(name="finalizer")

        if already_set:
            obj = ClassUnderTest(native=ctypes.c_void_p(1))
            exception_expected = pytest.raises(ValueError, match="_native can’t be changed")
        else:
            obj = ClassUnderTest()

        if not set_null:
            sentinel = ctypes.c_void_p(12345)
        else:
            sentinel = ctypes.c_void_p()

        if native_is_pointer and set_null:
            exception_expected = pytest.raises(
                ValueError, match=r"_native must be a valid \(non-NULL\) pointer")

        with exception_expected:
            obj._native = sentinel

        if already_set or (native_is_pointer and set_null):
            return

        assert obj._real_native is sentinel

        if native_is_pointer:
            assert sentinel.value in obj._real_native_refcounts
            assert sentinel.value in obj._real_native_must_free
            assert wrapper.WrapperOfWrappings._real_native_refcounts[sentinel.value] == 1
            assert wrapper.WrapperOfWrappings._real_native_must_free[sentinel.value] is True

    @pytest.mark.parametrize("testcase", ("normal", "not-a-pointer", "must-not-free"))
    def test__native__deleter(self, testcase: str) -> None:
        native_is_pointer = "not-a-pointer" not in testcase
        must_free = "must-not-free" not in testcase

        finalizer = mock.Mock()

        class ClassUnderTest(wrapper.WrapperOfWrappings):
            _lib = mock.Mock(finalizer=finalizer)

        if native_is_pointer:
            sentinel = ctypes.c_void_p(12345)
            ClassUnderTest._libgit2_native_finalizer = "finalizer"
        else:
            sentinel = object()

        objs = [
            ClassUnderTest(native=sentinel, _must_free=must_free),
            ClassUnderTest(native=sentinel, _must_free=False),  # verify overriding of _must_free
        ]

        assert all(obj._real_native is sentinel for obj in objs)

        if native_is_pointer:
            assert wrapper.WrapperOfWrappings._real_native_refcounts[12345] == 2

        del objs[0]._native

        assert objs[0]._real_native is None
        assert objs[1]._real_native is sentinel

        if native_is_pointer:
            assert wrapper.WrapperOfWrappings._real_native_refcounts[12345] == 1

        del objs[1]._native

        assert all(obj._real_native is None for obj in objs)

        if native_is_pointer:
            if must_free:
                finalizer.assert_called_with(sentinel)
            else:
                finalizer.assert_not_called()
            assert 12345 not in wrapper.WrapperOfWrappings._real_native_refcounts
            assert 12345 not in wrapper.WrapperOfWrappings._real_native_must_free
