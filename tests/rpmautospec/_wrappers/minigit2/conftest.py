import subprocess
from pathlib import Path

import pytest

from rpmautospec._wrappers.minigit2.repository import Repository


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "git_repo"
    repo_root.mkdir()
    repo_root_str = str(repo_root)
    subprocess.run(["git", "-C", repo_root_str, "init", "--initial-branch", "main"])

    a_file = repo_root / "a_file"
    a_file.write_text("A file.\n")
    subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)])
    subprocess.run(["git", "-C", repo_root_str, "commit", "-m", "Add a file"])

    return repo_root


@pytest.fixture
def repo_root_str(repo_root: Path) -> str:
    return str(repo_root)


@pytest.fixture
def repo(repo_root: Path) -> Repository:
    return Repository(repo_root)
