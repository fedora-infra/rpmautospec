import subprocess
from typing import TYPE_CHECKING

from rpmautospec.minigit2.index import Index

from .common import BaseTestWrapper

if TYPE_CHECKING:
    from pathlib import Path

    from rpmautospec.minigit2.repository import Repository


class TestIndex(BaseTestWrapper):
    cls = Index

    def test_diff_to_workdir(
        self, repo_root: "Path", repo_root_str: str, repo: "Repository"
    ) -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("Some changed text")

        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)], check=True)

        a_file.write_text("More changed text")

        diff = repo.index.diff_to_workdir()

        assert diff.stats.files_changed == 1
