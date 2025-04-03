import subprocess
from ctypes import c_char_p, c_size_t, c_uint16, c_uint32
from typing import TYPE_CHECKING

import pytest

from rpmautospec._wrappers.minigit2.constants import GIT_OID_SHA1_HEXSIZE, GIT_OID_SHA1_SIZE
from rpmautospec._wrappers.minigit2.diff import DeltasIter, Diff, DiffDelta, DiffFile, DiffStats
from rpmautospec._wrappers.minigit2.enums import DeltaStatus, DiffFlag
from rpmautospec._wrappers.minigit2.native_adaptation import (
    git_delta_t,
    git_diff_file,
    git_diff_flag_t,
    git_diff_p,
    git_filemode_t,
    git_oid,
)

if TYPE_CHECKING:
    from pathlib import Path

    from rpmautospec._wrappers.minigit2.commit import Commit
    from rpmautospec._wrappers.minigit2.repository import Repository


class TestDiffFile:
    @pytest.mark.parametrize("with_path", (True, False), ids=("with-path", "without-path"))
    def test___init__(self, with_path: bool) -> None:
        if with_path:
            id = b"\xff" * GIT_OID_SHA1_SIZE
            path = b"folder/file.ext"
            size = 5
            flags = git_diff_flag_t.NOT_BINARY | git_diff_flag_t.EXISTS
            mode = git_filemode_t.BLOB
        else:
            id = b"\0" * GIT_OID_SHA1_SIZE
            path = None
            size = 0
            flags = 0
            mode = git_filemode_t.UNREADABLE

        native = git_diff_file(
            id=git_oid(id=id),
            path=c_char_p(path),
            size=c_size_t(size),
            flags=c_uint32(flags),
            mode=c_uint16(mode),
            id_abbrev=c_uint16(GIT_OID_SHA1_HEXSIZE),
        )

        diff_file = DiffFile(native)

        if with_path:
            assert diff_file.id.hex == "f" * GIT_OID_SHA1_HEXSIZE
            assert diff_file.path == "folder/file.ext"
            assert diff_file.raw_path == b"folder/file.ext"
            assert diff_file.size == 5
            assert diff_file.flags == git_diff_flag_t.NOT_BINARY | git_diff_flag_t.EXISTS
            assert diff_file.mode == git_filemode_t.BLOB
        else:
            assert diff_file.id.hex == "0" * GIT_OID_SHA1_HEXSIZE
            assert diff_file.path is None
            assert diff_file.raw_path is None
            assert diff_file.size == 0
            assert diff_file.flags == 0
            assert diff_file.mode == git_filemode_t.UNREADABLE


@pytest.fixture
def commits(repo_root: "Path", repo_root_str: str, repo: "Repository") -> tuple["Commit", "Commit"]:
    former_head_commit = repo[repo.head.target]

    a_file = repo_root / "a_file"
    a_file.write_text("Something new.")

    subprocess.run(
        ["git", "-C", repo_root_str, "commit", "-a", "-m", "Change something"], check=True
    )

    head_commit = repo[repo.head.target]

    return former_head_commit, head_commit


@pytest.fixture
def diff(repo: "Repository", commits: tuple["Commit", "Commit"]) -> Diff:
    return repo.diff(*commits)


@pytest.fixture
def delta(diff: Diff) -> DiffDelta:
    return list(diff.deltas)[0]


class TestDiffDelta:
    def test___init__(self, delta: DiffDelta, diff: Diff) -> None:
        assert delta._diff is diff

    def test_status(self, delta: DiffDelta) -> None:
        status = delta.status
        assert isinstance(status, DeltaStatus)
        # Verify status is cached.
        assert status is delta.status
        assert status == git_delta_t.MODIFIED

    def test_flags(self, delta: DiffDelta) -> None:
        assert isinstance(delta.flags, DiffFlag)

    def test_similarity(self, delta: DiffDelta) -> None:
        assert isinstance(delta.similarity, int)

    def test_nfiles(self, delta: DiffDelta) -> None:
        assert isinstance(delta.nfiles, int)
        assert delta.nfiles == 2  # old and new file

    @pytest.mark.parametrize("old_or_new", ("old", "new"))
    def test_old_new_file(self, old_or_new: str, delta: DiffDelta) -> None:
        file = getattr(delta, f"{old_or_new}_file")
        assert isinstance(file, DiffFile)
        assert file.path == "a_file"
        assert file.flags & git_diff_flag_t.VALID_ID
        assert file.flags & git_diff_flag_t.EXISTS
        if hasattr(git_diff_flag_t, "VALID_SIZE"):
            assert git_diff_flag_t.VALID_SIZE and file.size > 0 or file.size == 0


class TestDiff:
    def test___init__(self, diff: Diff, repo: "Repository") -> None:
        assert diff._repo is repo
        assert isinstance(diff._native, git_diff_p)

    def test_deltas(self, diff: Diff) -> None:
        deltas = diff.deltas
        assert isinstance(deltas, DeltasIter)
        # Verify the iterator isn’t cached.
        assert deltas is not diff.deltas

        deltas = list(deltas)
        assert len(deltas) == 1
        assert all(isinstance(delta, DiffDelta) for delta in deltas)

    def test_stats(self, diff: Diff) -> None:
        stats = diff.stats
        assert isinstance(stats, DiffStats)
        # Verify stats are cached.
        assert stats is diff.stats

        assert stats.files_changed == 1

    def test_patch(self, diff: Diff) -> None:
        patch = diff.patch
        patch_lines = patch.split("\n")
        assert "--- a/a_file" in patch_lines
        assert "+++ b/a_file" in patch_lines
        assert "-A file." in patch_lines
        assert "+Something new." in patch_lines
