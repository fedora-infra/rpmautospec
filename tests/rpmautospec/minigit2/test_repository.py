import subprocess
from contextlib import nullcontext
from ctypes import byref, c_char_p
from pathlib import Path

import pytest

from rpmautospec.minigit2.blob import Blob
from rpmautospec.minigit2.commit import Commit
from rpmautospec.minigit2.index import Index
from rpmautospec.minigit2.native_adaptation import (
    git_buf,
    git_object_t,
    git_oid,
    git_repository_item_t,
)
from rpmautospec.minigit2.object_ import Object
from rpmautospec.minigit2.oid import Oid
from rpmautospec.minigit2.reference import Reference
from rpmautospec.minigit2.repository import Repository
from rpmautospec.minigit2.tree import Tree


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
            repo = Repository(path)

        if exists:
            buf = git_buf()
            buf_p = byref(buf)
            error_code = repo._lib.git_repository_item_path(
                buf_p, repo._native, git_repository_item_t.WORKDIR
            )
            repo.raise_if_error(error_code)
            assert repo_root == Path(buf.ptr.decode("utf-8", errors="replace"))
            repo._lib.git_buf_dispose(buf_p)
        else:
            assert "Can’t open repository" in str(excinfo.value)
            assert str(path) in str(excinfo.value)

    def test___get_item__(self, repo: Repository):
        assert isinstance(repo[repo.head.target], Commit)
        assert repo.head.target.hex == repo[repo.head.target].id.hex

    @pytest.mark.parametrize(
        "obj_type, expected",
        (
            pytest.param(Object, True, id="Object"),
            pytest.param(str, True, id="str"),
            pytest.param(bytes, True, id="bytes"),
            pytest.param(Oid, True, id="Oid"),
            pytest.param(None, True, id="None"),
            pytest.param(Blob, False, id="unexpected"),
        ),
    )
    def test__coerce_to_object_and_peel(
        self, obj_type: type, expected: bool, repo: Repository
    ):
        if obj_type is None:
            obj = None
        elif obj_type is Object:
            obj = repo[repo.head.target]
        elif obj_type is str:
            obj = repo.head.target.hex
        elif obj_type is bytes:
            obj = repo.head.target.hexb
        elif obj_type is Oid:
            obj = repo.head.target
        elif obj_type is Blob:
            content = b"BLOB\n"
            buf = c_char_p(content)
            oid = git_oid()
            error_code = repo._lib.git_blob_create_from_buffer(
                oid, repo._native, buf, len(content) + 1
            )
            repo.raise_if_error(error_code)
            obj = Object(repo=repo, oid=Oid(native=byref(oid)))

        peel_types = (git_object_t.BLOB, git_object_t.TREE)

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

        assert isinstance(peeled, Tree)

    def test_head(self, repo: Repository):
        assert isinstance(repo.head, Reference)
        assert repo.head.target.hex == repo[repo.head.target].id.hex

    def test_index(self, repo: Repository):
        assert isinstance(repo.index, Index)

    def test_diff(self, repo_root: Path, repo: Repository):
        initial_commit = repo[repo.head.target]

        repo_root_str = str(repo_root)
        a_file = repo_root / "a_file"
        a_file.write_text("New content.\n")

        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)])
        subprocess.run(["git", "-C", repo_root_str, "commit", "-m", "Change a file"])

        second_commit = repo[repo.head.target]

        initial_commit, second_commit  # FIXME
        raise
