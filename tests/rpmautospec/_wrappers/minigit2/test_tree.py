import subprocess
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from rpmautospec._wrappers.minigit2.diff import Diff
from rpmautospec._wrappers.minigit2.native_adaptation import lib
from rpmautospec._wrappers.minigit2.tree import Tree

if TYPE_CHECKING:
    from pathlib import Path

    from rpmautospec._wrappers.minigit2.repository import Repository


@pytest.fixture
def tree(repo: "Repository") -> Tree:
    head_commit = repo[repo.head.target]
    tree = head_commit.tree
    assert isinstance(tree, Tree)
    return tree


class TestTree:
    def test___contains__(self, tree: Tree) -> None:
        assert "a_file" in tree
        assert b"a_file" in tree
        assert "not_a_file" not in tree

    def test___getitem__(self, tree: Tree) -> None:
        blob = tree["a_file"]
        assert blob.name == "a_file"
        assert blob.data == b"A file.\n"

    def test___len__(self, tree: Tree) -> None:
        assert len(tree) == 1

    def test___iter__(self, tree: Tree) -> None:
        iterator = iter(tree)

        blobs = list(iterator)
        assert len(blobs) == 1

        blob = blobs[0]
        assert blob.name == "a_file"
        assert blob.data == b"A file.\n"

    def test_diff_to_tree(
        self, repo_root_str: str, repo_root: "Path", repo: "Repository", tree: Tree
    ) -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("Different contents.\n")
        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)], check=True)
        subprocess.run(
            ["git", "-C", repo_root_str, "commit", "-m", "Changed something"], check=True
        )

        new_tree = repo[repo.head.target].tree

        with mock.patch.object(
            lib, "git_diff_tree_to_tree", wraps=lib.git_diff_tree_to_tree
        ) as git_diff_tree_to_tree:
            diff = new_tree.diff_to_tree(tree)
            assert isinstance(diff, Diff)
            assert diff.stats.files_changed == 1
            git_diff_tree_to_tree.assert_called_once_with(
                mock.ANY, repo._native, new_tree._native, tree._native, mock.ANY
            )

        with mock.patch.object(
            lib, "git_diff_tree_to_tree", wraps=lib.git_diff_tree_to_tree
        ) as git_diff_tree_to_tree:
            diff = new_tree.diff_to_tree(tree, swap=True)
            assert isinstance(diff, Diff)
            assert diff.stats.files_changed == 1
            git_diff_tree_to_tree.assert_called_once_with(
                mock.ANY, repo._native, tree._native, new_tree._native, mock.ANY
            )

    def test_diff_to_workdir(self, repo_root: "Path", tree: Tree) -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("Different contents.\n")

        diff = tree.diff_to_workdir()
        assert isinstance(diff, Diff)
        assert diff.stats.files_changed == 1

    def test_diff_to_index(
        self, repo_root_str: str, repo_root: "Path", repo: "Repository", tree: Tree
    ) -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("Different contents.\n")
        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)], check=True)

        diff = tree.diff_to_index(repo.index)
        assert isinstance(diff, Diff)
        assert diff.stats.files_changed == 1
