from contextlib import nullcontext
from ctypes import CDLL, pointer
from stat import filemode
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from rpmautospec.minigit2.blob import Blob
from rpmautospec.minigit2.commit import Commit
from rpmautospec.minigit2.native_adaptation import git_object_p, git_object_t
from rpmautospec.minigit2.object_ import Object
from rpmautospec.minigit2.oid import Oid
from rpmautospec.minigit2.tree import Tree

if TYPE_CHECKING:
    from rpmautospec.minigit2.repository import Repository


class TestObject:
    def test___init_subclass__(self) -> None:
        with mock.patch.dict(Object._object_t_to_cls, clear=True):

            class FakeBlobWorks(Object):
                _object_t = git_object_t.BLOB

            assert Object._object_t_to_cls == {git_object_t.BLOB: FakeBlobWorks}

            with pytest.raises(TypeError, match="Object type already registered"):

                class FakeBlobFails(Object):
                    _object_t = git_object_t.BLOB

    @pytest.mark.parametrize("testcase", ("from-oid", "from-native", "underspecified"))
    def test_construct_and_initialize(
        self, testcase: str, libgit2: "CDLL", repo: "Repository"
    ) -> None:
        from_native = "from-native" in testcase
        underspecified = "underspecified" in testcase

        if underspecified:
            oid = native = None
            expectation = pytest.raises(ValueError)
        else:
            expectation = nullcontext()
            oid = repo.head.target
            native = None
            if from_native:
                native = git_object_p()

                error_code = libgit2.git_object_lookup(
                    pointer(native), repo._native, pointer(oid._native), git_object_t.ANY
                )
                assert error_code == 0

                oid = None

        with expectation:
            head_commit = Object(repo=repo, native=native, oid=oid)

        if not underspecified:
            assert isinstance(head_commit, Commit)

    def test___repr__(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]

        assert repr(head_commit) == f"Commit(oid={head_commit.short_id!r})"

    def test___eq__(self, repo: "Repository") -> None:
        head_commits = [repo[repo.head.target] for i in range(2)]
        # Verify that different objects are compared
        assert head_commits[0] is not head_commits[1]

        assert head_commits[0] == head_commits[1]

    def test___hash__(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]
        assert isinstance(hash(head_commit), int)
        assert hash(head_commit) == hash(head_commit.id.hex)

    def test_id(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]
        oid = head_commit.id
        assert isinstance(oid, Oid)
        assert Object(repo=repo, oid=oid) == head_commit

    def test_short_id(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]
        assert head_commit.id.hex[: len(head_commit.short_id)] == head_commit.short_id

    def test_peel(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]
        assert head_commit.peel(git_object_t.COMMIT) == head_commit
        assert isinstance(head_commit.peel(), Tree)

    def test_name_and_filemode(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]
        tree = head_commit.peel(git_object_t.TREE)

        # Commits and their trees don’t have associated tree entries, so no names and file modes.
        assert head_commit.name is head_commit.filemode is None
        assert tree.name is tree.filemode is None

        blobs = list(tree)
        assert len(blobs) == 1
        blob = blobs[0]
        assert isinstance(blob, Blob)
        assert blob.name == "a_file"
        filemode_str = filemode(blob.filemode)
        assert filemode_str.startswith("-")
        assert all(x in "-rwx" for x in filemode_str)
