from ctypes import pointer
from stat import filemode
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from rpmautospec._wrappers.minigit2.blob import Blob
from rpmautospec._wrappers.minigit2.commit import Commit
from rpmautospec._wrappers.minigit2.native_adaptation import git_object_p, git_object_t, lib
from rpmautospec._wrappers.minigit2.object_ import Object
from rpmautospec._wrappers.minigit2.oid import Oid
from rpmautospec._wrappers.minigit2.tree import Tree

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

    # Object.__init__() is tested with .from_native() and .from_oid()

    def test__from_native(self, repo: "Repository") -> None:
        oid = repo.head.target
        native = git_object_p()

        error_code = lib.git_object_lookup(
            pointer(native), repo._native, pointer(oid._native), git_object_t.ANY
        )
        assert error_code == 0

        head_commit = Object._from_native(repo=repo, native=native)

        assert isinstance(head_commit, Commit)

    def test__from_oid(self, repo: "Repository") -> None:
        oid = repo.head.target

        head_commit = Object._from_oid(repo=repo, oid=oid)

        assert isinstance(head_commit, Commit)

    def test___repr__(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]

        assert repr(head_commit) == f"Commit(oid={head_commit.id.hex!r})"

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
        assert Object._from_oid(repo=repo, oid=oid) == head_commit

    def test_short_id(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]
        assert head_commit.id.hex[: len(head_commit.short_id)] == head_commit.short_id

    def test_peel(self, repo: "Repository") -> None:
        # cf. test_reference::TestReference::test_peel()
        head_commit = repo[repo.head.target]
        assert head_commit.peel(Commit) == head_commit
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
