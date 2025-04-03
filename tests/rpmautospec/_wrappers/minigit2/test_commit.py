import re
import subprocess
from typing import TYPE_CHECKING, Optional
from unittest import mock

import pytest

from rpmautospec._wrappers.minigit2 import commit, signature, tree

if TYPE_CHECKING:
    from pathlib import Path

    from rpmautospec._wrappers.minigit2.repository import Repository


class TestCommit:
    def test_parents(self, repo_root: "Path", repo_root_str: str, repo: "Repository") -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("A file. Was changed.")
        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)])
        subprocess.run(["git", "-C", repo_root_str, "commit", "-m", "Change a file"])

        head_commit = repo[repo.head.target]
        assert len(head_commit.parents) == 1
        assert head_commit.parents[0].message.strip() == "Add a file"

    def test_tree(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]
        assert isinstance(head_commit.tree, tree.Tree)

    def test_commit_time(self, repo_root_str: str, repo: "Repository") -> None:
        completed = subprocess.run(
            ["git", "-C", repo_root_str, "log", "-1", "--format=format:%ad", "--date=format:%s"],
            capture_output=True,
        )
        assert completed.returncode == 0
        expected_commit_time = int(completed.stdout)

        head_commit = repo[repo.head.target]
        commit_time = head_commit.commit_time

        assert expected_commit_time == commit_time

    def test_commit_time_offset(self, repo_root_str: str, repo: "Repository") -> None:
        completed = subprocess.run(
            ["git", "-C", repo_root_str, "log", "-1", "--format=format:%ad", "--date=format:%z"],
            capture_output=True,
        )
        assert completed.returncode == 0

        match = re.match(
            r"^(?P<sign>[-+])(?P<hours>\d\d)(?P<minutes>\d\d)$", completed.stdout.decode("ascii")
        )
        expected_offset = (-1 if match.group("sign") == "-" else 1) * (
            int(match.group("hours")) * 60 + int(match.group("minutes"))
        )

        head_commit = repo[repo.head.target]
        offset = head_commit.commit_time_offset

        assert expected_offset == offset

    @pytest.mark.parametrize("attribute", ("author", "committer"))
    def test_author_committer(self, attribute: str, repo_root_str: str, repo: "Repository") -> None:
        if attribute == "author":
            format = "%an%n%ae"
        else:
            format = "%cn%n%ce"

        completed = subprocess.run(
            ["git", "-C", repo_root_str, "log", "-1", f"--format=format:{format}"],
            capture_output=True,
        )
        assert completed.returncode == 0

        name, email = completed.stdout.decode("utf-8").strip().split("\n")

        sig = getattr(repo[repo.head.target], attribute)

        assert isinstance(sig, signature.Signature)
        assert name == sig.name
        assert email == sig.email

    @pytest.mark.parametrize("native_encoding", (None, b"utf-8"))
    def test_message_encoding(
        self, native_encoding: Optional[str], repo_root_str: str, repo: "Repository"
    ) -> None:
        head_commit = repo[repo.head.target]

        with mock.patch.object(commit, "lib") as lib:
            lib.git_commit_message_encoding.return_value = native_encoding
            assert head_commit.message_encoding == "utf-8"

        lib.git_commit_message_encoding.assert_called_once_with(head_commit._native)

    def test_message(self, repo: "Repository") -> None:
        head_commit = repo[repo.head.target]
        assert head_commit.message.strip() == "Add a file"
