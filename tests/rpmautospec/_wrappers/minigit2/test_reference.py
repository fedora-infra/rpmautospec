import subprocess
from contextlib import nullcontext
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from rpmautospec._wrappers.minigit2.commit import Commit
from rpmautospec._wrappers.minigit2.native_adaptation import git_object_t, git_reference_p, lib
from rpmautospec._wrappers.minigit2.oid import Oid
from rpmautospec._wrappers.minigit2.reference import Reference

from .common import BaseTestWrapper

if TYPE_CHECKING:
    from rpmautospec._wrappers.minigit2.repository import Repository


class TestReference(BaseTestWrapper):
    cls = Reference

    def test___eq__(self, repo: "Repository") -> None:
        ref1 = repo.head
        ref2 = repo.head

        assert ref1 is not ref2
        assert ref1 == ref2

    def test_name(self, repo: "Repository") -> None:
        assert repo.head.name == "refs/heads/main"
        assert repo.head.shorthand == "main"

    @pytest.mark.parametrize("testcase", ("direct", "symbolic", "symbolic-invalid"))
    def test_target(self, testcase: str, repo_root_str: str, repo: "Repository") -> None:
        direct = "direct" in testcase
        invalid = "invalid" in testcase

        expectation = nullcontext()
        if direct:
            ref = repo.head
        else:
            native = git_reference_p()
            refname = b"HEAD"
            error_code = lib.git_reference_lookup(native, repo._native, refname)
            assert error_code == 0

            completed = subprocess.run(
                ["git", "-C", repo_root_str, "branch", "--show-current"],
                check=True,
                capture_output=True,
            )
            branch_name = completed.stdout.strip().decode(
                encoding=getfilesystemencoding(), errors=getfilesystemencodeerrors()
            )

            ref = Reference(repo=repo, native=native)

        if invalid:
            expectation = pytest.raises(ValueError)
            simulate_invalid = mock.patch.object(lib, "git_reference_symbolic_target")
        else:
            simulate_invalid = nullcontext()

        with expectation, simulate_invalid as git_reference_symbolic_target:
            if invalid:
                git_reference_symbolic_target.return_value = None
            target = ref.target

        if not invalid:
            if direct:
                assert isinstance(target, Oid)
            else:  # symbolic
                assert target == f"refs/heads/{branch_name}"

    def test_peel(self, repo: "Repository") -> None:
        # cf. test_object::TestObject::test_peel()
        ref = repo.head
        head_commit = repo[ref.target]

        assert ref.peel(Commit) == head_commit
        assert ref.peel(git_object_t.COMMIT) == head_commit
        assert isinstance(ref.peel(), Commit)

    def test_resolve(self, repo_root_str: str, repo: "Repository") -> None:
        # Create symbolic reference
        native = git_reference_p()
        assert (
            lib.git_reference_symbolic_create(
                native,  # out
                repo._native,  # repo
                b"refs/heads/devel",  # name
                b"refs/heads/main",  # target
                False,  # force
                b"Make 'devel' track 'main'",  # log_message
            )
            == 0
        )
        ref = Reference(repo=repo, native=native)

        # Resolve to native reference (i.e. to a commit)
        resolved = ref.resolve()
        assert resolved is not ref
        assert resolved == repo.head

        # Resolving further only yields itself back
        assert resolved.resolve() is resolved
