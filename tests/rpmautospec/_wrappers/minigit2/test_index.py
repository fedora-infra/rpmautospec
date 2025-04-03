import subprocess
from typing import TYPE_CHECKING

import pytest

from rpmautospec._wrappers.minigit2.index import Index
from rpmautospec._wrappers.minigit2.oid import Oid

from .common import BaseTestWrapper

if TYPE_CHECKING:
    from pathlib import Path

    from rpmautospec._wrappers.minigit2.repository import Repository


class TestIndex(BaseTestWrapper):
    cls = Index

    @pytest.mark.parametrize("path_type", ("path", "str", "bytes"))
    def test_remove_etc(
        self, path_type: str, repo_root: "Path", repo: "Repository", repo_root_str: str
    ) -> None:
        a_file = repo_root / "a_file"
        a_file.unlink()

        index = repo.index
        remove_file = a_file.relative_to(repo_root)

        if path_type != "path":
            remove_file = str(remove_file)
            if path_type == "bytes":
                remove_file = remove_file.encode("utf-8")

        index.remove(remove_file)
        index.write()
        tree_oid = index.write_tree()

        assert isinstance(tree_oid, Oid)

        completed = subprocess.run(
            ["git", "-C", repo_root_str, "diff", "--cached"], check=True, capture_output=True
        )
        assert b"\n-A file.\n" in completed.stdout
        assert b"\n+++ /dev/null\n" in completed.stdout

    @pytest.mark.parametrize("path_type", ("path", "str", "bytes"))
    def test_add_etc(
        self, path_type: str, repo_root: "Path", repo: "Repository", repo_root_str: str
    ) -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("Boo!\n")

        index = repo.index
        add_file = a_file.relative_to(repo_root)

        if path_type != "path":
            add_file = str(add_file)
            if path_type == "bytes":
                add_file = add_file.encode("utf-8")

        index.add(add_file)
        index.write()
        tree_oid = index.write_tree()

        assert isinstance(tree_oid, Oid)

        completed = subprocess.run(
            ["git", "-C", repo_root_str, "diff", "--cached"], check=True, capture_output=True
        )
        assert b"\n-A file.\n" in completed.stdout
        assert b"\n+Boo!\n" in completed.stdout

    @pytest.mark.parametrize("path_type", ("path", "str", "bytes", "none"))
    def test_add_all(
        self, path_type: str, repo_root: "Path", repo: "Repository", repo_root_str: str
    ) -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("Boo!\n")

        index = repo.index

        if path_type == "none":
            pathspecs = None
        else:
            add_file = a_file.relative_to(repo_root)

            if path_type != "path":
                add_file = str(add_file)
                if path_type == "bytes":
                    add_file = add_file.encode("utf-8")

            pathspecs = [add_file]

        index.add_all(pathspecs)
        index.write()
        tree_oid = index.write_tree()

        assert isinstance(tree_oid, Oid)

        completed = subprocess.run(
            ["git", "-C", repo_root_str, "diff", "--cached"], check=True, capture_output=True
        )
        assert b"\n-A file.\n" in completed.stdout
        assert b"\n+Boo!\n" in completed.stdout

    def test_diff_to_workdir(
        self, repo_root: "Path", repo_root_str: str, repo: "Repository"
    ) -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("Some changed text")

        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)], check=True)

        a_file.write_text("More changed text")

        diff = repo.index.diff_to_workdir()

        assert diff.stats.files_changed == 1
