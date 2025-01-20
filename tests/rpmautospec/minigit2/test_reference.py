import subprocess
from contextlib import nullcontext
from sys import getfilesystemencodeerrors, getfilesystemencoding
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from rpmautospec.minigit2.native_adaptation import git_reference_p
from rpmautospec.minigit2.oid import Oid
from rpmautospec.minigit2.reference import Reference

from .common import BaseTestWrapper

if TYPE_CHECKING:
    from ctypes import CDLL

    from rpmautospec.minigit2.repository import Repository


class TestReference(BaseTestWrapper):
    cls = Reference

    @pytest.mark.parametrize("testcase", ("direct", "symbolic", "symbolic-invalid"))
    def test_target(
        self, testcase: str, libgit2: "CDLL", repo_root_str: str, repo: "Repository"
    ) -> None:
        direct = "direct" in testcase
        invalid = "invalid" in testcase

        expectation = nullcontext()
        if direct:
            ref = repo.head
        else:
            native = git_reference_p()
            refname = b"HEAD"
            error_code = libgit2.git_reference_lookup(native, repo._native, refname)
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
            simulate_invalid = mock.patch.object(ref._lib, "git_reference_symbolic_target")
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
