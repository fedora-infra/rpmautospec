import ctypes
import ctypes.util
import gc
import re
import subprocess
from contextlib import nullcontext
from pathlib import Path
from random import randbytes
from typing import Any, Optional
from unittest import mock

import pytest

from rpmautospec.minigit2 import constants, exc, native_adaptation, wrapper


def get_param_id_from_request(request: pytest.FixtureRequest) -> str:
    node = request.node
    name = node.name
    originalname = node.originalname
    if not (match := re.match(rf"^{originalname}\[(?P<id>[^\]]+)\]", name)):
        raise ValueError(f"Can’t extract parameter id from request: {name}")
    return match.group("id")


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


@pytest.fixture
def repo_root(tmp_path) -> Path:
    repo_root = tmp_path / "git_repo"
    repo_root.mkdir()
    repo_root_str = str(repo_root)
    subprocess.run(["git", "-C", repo_root_str, "init"])

    a_file = repo_root / "a_file"
    a_file.write_text("A file.\n")
    subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)])
    subprocess.run(["git", "-C", repo_root_str, "commit", "-m", "Add a file"])

    return repo_root


@pytest.fixture
def repo(repo_root) -> wrapper.Repository:
    return wrapper.Repository(repo_root)


class TestLibraryUser:
    @pytest.mark.parametrize(
        "success, cache_is_hot, found, soname",
        (
            pytest.param(True, False, True, "reallib", id="success-real-lib"),
            pytest.param(True, False, True, "libgit2.so.1.8", id="success"),
            pytest.param(
                True, False, True, "libgit2.so.1.8.5", id="success-max-version-with-minor"
            ),
            pytest.param(True, False, True, "libgit2.so.1.9", id="success-version-unknown"),
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
        test_case = get_param_id_from_request(request)

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
                if "version-unknown" in test_case:
                    expectation = pytest.warns(exc.Libgit2VersionWarning)
                else:
                    expectation = nullcontext()
            else:
                if "libgit2-not-found" in test_case:
                    expectation = pytest.raises(exc.Libgit2NotFoundError)
                elif "illegal-soname" in test_case or "version-too-low" in test_case:
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
        "error_code, exc_msg_tmpl",
        (
            pytest.param(0, None, id="without-error-code"),
            pytest.param(-1, "Something happened: {message}", id="with-error-code-template"),
            pytest.param(-1, None, id="with-error-code-without-template"),
        ),
    )
    def test_raise_if_error(self, error_code: int, exc_msg_tmpl: Optional[str]):
        if error_code:
            expectation = pytest.raises(exc.GitError)
        else:
            expectation = nullcontext()

        with mock.patch.object(wrapper.WrapperOfWrappings, "_get_library") as _get_library:
            _get_library.return_value = lib = mock.Mock()
            lib.git_error_last.return_value = error_p = mock.Mock()
            error_p.contents.message = b"BOO!"

            with expectation as excinfo:
                wrapper.WrapperOfWrappings.raise_if_error(error_code, exc_msg_tmpl)

        if not error_code:
            lib.git_error_last.assert_not_called()
        else:
            lib.git_error_last.assert_called_once_with()
            exc_str = str(excinfo.value)
            assert "BOO!" in exc_str
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

    @pytest.mark.parametrize("testcase", ("normal", "already-set", "not-a-pointer"))
    def test__native__setter(self, testcase: str) -> None:
        already_set = "already-set" in testcase
        native_is_pointer = "not-a-pointer" not in testcase

        class ClassUnderTest(wrapper.WrapperOfWrappings):
            def __repr__(self):
                return "ClassUnderTest()"

        if native_is_pointer:
            ClassUnderTest._libgit2_native_finalizer = mock.Mock(name="finalizer")

        if already_set:
            obj = ClassUnderTest(native=ctypes.c_void_p(1))
            exception_expected = pytest.raises(ValueError, match="_native can’t be changed")
        else:
            obj = ClassUnderTest()
            exception_expected = nullcontext()

        sentinel = ctypes.c_void_p(12345)

        with exception_expected:
            obj._native = sentinel

        if already_set:
            return

        assert obj._real_native is sentinel

        if native_is_pointer:
            assert sentinel.value in obj._real_native_refcounts
            assert sentinel.value in obj._real_native_must_free
            assert wrapper.WrapperOfWrappings._real_native_refcounts[sentinel.value] == 1
            assert wrapper.WrapperOfWrappings._real_native_must_free[sentinel.value] is True

    @pytest.mark.parametrize("testcase", ("normal", "not-a-pointer"))
    def test__native__deleter(self, testcase: str) -> None:
        native_is_pointer = "not-a-pointer" not in testcase

        class ClassUnderTest(wrapper.WrapperOfWrappings):
            pass

        if native_is_pointer:
            sentinel = ctypes.c_void_p(12345)
            ClassUnderTest._libgit2_native_finalizer = finalizer = mock.Mock()
        else:
            sentinel = object()

        objs = [
            ClassUnderTest(native=sentinel),
            ClassUnderTest(native=sentinel, _must_free=False),
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
            finalizer.assert_called_with(sentinel)
            assert 12345 not in wrapper.WrapperOfWrappings._real_native_refcounts
            assert 12345 not in wrapper.WrapperOfWrappings._real_native_must_free


class TestOid:
    @pytest.mark.parametrize(
        "test_case",
        ("native", "oid", "oid-as-str", "oid-as-bytes", "none", "native-and-oid"),
    )
    def test___init__(self, test_case: str):
        native_in = oid_in = None
        success = True

        oid_bytes = randbytes(constants.GIT_OID_SHA1_SIZE)
        oid_hex = "".join(f"{x:02x}" for x in oid_bytes)

        if "native" in test_case:
            oid_bytearray = bytearray(oid_bytes)
            native_oid = native_adaptation.git_oid.from_buffer_copy(oid_bytearray)
            native_in = ctypes.pointer(native_oid)

        if "oid" in test_case:
            oid_in = oid_hex
            if "oid-as-bytes" in test_case:
                oid_in = oid_in.encode("ascii")
            elif "oid-as-str" not in test_case:
                oid_in = wrapper.Oid(oid=oid_in)

        if "none" in test_case or "and" in test_case:
            expectation = pytest.raises(
                ValueError, match="Exactly one of native or oid has to be specified"
            )
            success = False
        else:
            expectation = nullcontext()

        with expectation:
            oid = wrapper.Oid(native=native_in, oid=oid_in)

        if success:
            assert oid.hex == str(oid) == oid_hex
            assert oid.hexb == oid_hex.encode("ascii")


class TestRepository:
    @pytest.mark.parametrize(
        "path_type, exists",
        (
            pytest.param(str, True, id="str"),
            pytest.param(Path, True, id="Path"),
            pytest.param(str, False, id="missing"),
        ),
    )
    def test___init__(self, path_type: type, exists: bool, repo_root: Path, tmp_path: Path) -> None:
        if exists:
            path = path_type(repo_root)
            expectation = nullcontext()
        else:
            not_a_repo = tmp_path / "not_a_repo"
            not_a_repo.mkdir()
            path = path_type(not_a_repo)
            expectation = pytest.raises(KeyError)

        with expectation as excinfo:
            repo = wrapper.Repository(path)

        if exists:
            buf = native_adaptation.git_buf()
            buf_p = ctypes.byref(buf)
            error_code = repo._lib.git_repository_item_path(
                buf_p, repo._native, native_adaptation.git_repository_item_t.WORKDIR
            )
            repo.raise_if_error(error_code)
            assert repo_root == Path(buf.ptr.decode("utf-8", errors="replace"))
            repo._lib.git_buf_dispose(buf_p)
        else:
            assert "Can’t open repository" in str(excinfo.value)
            assert str(path) in str(excinfo.value)

    def test___get_item__(self, repo: wrapper.Repository):
        assert isinstance(repo[repo.head.target], wrapper.Commit)
        assert repo.head.target.hex == repo[repo.head.target].id.hex

    @pytest.mark.parametrize(
        "obj_type, expected",
        (
            pytest.param(wrapper.Object, True, id="Object"),
            pytest.param(str, True, id="str"),
            pytest.param(bytes, True, id="bytes"),
            pytest.param(wrapper.Oid, True, id="Oid"),
            pytest.param(None, True, id="None"),
            pytest.param(wrapper.Blob, False, id="unexpected"),
        ),
    )
    def test__coerce_to_object_and_peel(
        self, obj_type: type, expected: bool, repo: wrapper.Repository
    ):
        if obj_type is None:
            obj = None
        elif obj_type is wrapper.Object:
            obj = repo[repo.head.target]
        elif obj_type is str:
            obj = repo.head.target.hex
        elif obj_type is bytes:
            obj = repo.head.target.hexb
        elif obj_type is wrapper.Oid:
            obj = repo.head.target
        elif obj_type is wrapper.Blob:
            content = b"BLOB\n"
            buf = ctypes.c_char_p(content)
            oid = native_adaptation.git_oid()
            error_code = repo._lib.git_blob_create_from_buffer(
                oid, repo._native, buf, len(content) + 1
            )
            repo.raise_if_error(error_code)
            obj = wrapper.Object(repo=repo, oid=wrapper.Oid(native=ctypes.byref(oid)))

        peel_types = (native_adaptation.git_object_t.BLOB, native_adaptation.git_object_t.TREE)

        if expected:
            expectation = nullcontext()
        else:
            peel_types = tuple(
                pt for pt in peel_types if pt != getattr(obj_type, "_object_t", None)
            )
            expectation = pytest.raises(TypeError, match="unexpected")

        with expectation:
            peeled = repo._coerce_to_object_and_peel(obj=obj, peel_types=peel_types)

        if not expected:
            return

        if obj_type is None:
            assert peeled is None
            return

        assert isinstance(peeled, wrapper.Tree)

    def test_head(self, repo: wrapper.Repository):
        assert isinstance(repo.head, wrapper.Reference)
        assert repo.head.target.hex == repo[repo.head.target].id.hex

    def test_index(self, repo: wrapper.Repository):
        assert isinstance(repo.index, wrapper.Index)

    def test_diff(self, repo_root: Path, repo: wrapper.Repository):
        initial_commit = repo[repo.head.target]

        repo_root_str = str(repo_root)
        a_file = repo_root / "a_file"
        a_file.write_text("New content.\n")

        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)])
        subprocess.run(["git", "-C", repo_root_str, "commit", "-m", "Change a file"])

        second_commit = repo[repo.head.target]
