import logging
import os
import re
import stat
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch
from tempfile import TemporaryDirectory

import pygit2
import pytest

from rpmautospec.pkg_history import PkgHistoryProcessor


SPEC_FILE_TEXT = """Summary: Boo
Name: boo
Version: 1.0
Release: %autorel
License: CC0

%description
Boo

%changelog
%autochangelog
"""


@pytest.fixture
def specfile():
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        repodir = tmpdir / "test"
        repodir.mkdir()
        specfile = repodir / "test.spec"
        specfile.write_text(SPEC_FILE_TEXT)

        yield specfile


@pytest.fixture
def repo(specfile):
    # pygit2 < 1.2.0 can't cope with pathlib.Path objects
    repopath = str(specfile.parent)

    pygit2.init_repository(repopath, initial_head="rawhide")
    if hasattr(pygit2, "GIT_REPOSITORY_OPEN_NO_SEARCH"):
        repo = pygit2.Repository(repopath, pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH)
    else:
        # pygit2 < 1.4.0
        repo = pygit2.Repository(repopath)

    repo.config["user.name"] = "Jane Doe"
    repo.config["user.email"] = "jane.doe@example.com"

    # create root commit in "rawhide" branch
    index = repo.index
    index.add(specfile.name)
    index.write()

    tree = index.write_tree()

    oid = repo.create_commit(
        None, repo.default_signature, repo.default_signature, "Initial commit", tree, []
    )
    repo.branches.local.create("rawhide", repo[oid])

    # add another commit (empty)
    parent, ref = repo.resolve_refish(repo.head.name)
    repo.create_commit(
        ref.name,
        repo.default_signature,
        repo.default_signature,
        "Did nothing!",
        tree,
        [parent.oid],
    )

    yield repo


@pytest.fixture
def processor(repo):
    processor = PkgHistoryProcessor(repo.workdir)
    return processor


class TestPkgHistoryProcessor:

    version_re = re.compile(r"^Version: .*$", flags=re.MULTILINE)

    @pytest.mark.parametrize(
        "testcase",
        (
            "str, is file",
            "str, is dir",
            "path, is file",
            "path, is file, wrong extension",
            "path, is dir",
            "doesn't exist",
            "spec doesn't exist, is dir",
            "no git repo",
            "not a regular file",
        ),
    )
    @patch("rpmautospec.pkg_history.pygit2")
    def test___init__(self, pygit2, testcase, specfile):
        if "wrong extension" in testcase:
            # Path.rename() only returns the new path from Python 3.8 on.
            specfile.rename(specfile.with_suffix(".foo"))
            specfile = specfile.with_suffix(".foo")

        spec_or_path = specfile

        if "is dir" in testcase:
            spec_or_path = spec_or_path.parent

        if "spec doesn't exist" in testcase:
            specfile.unlink()
        elif "doesn't exist" in testcase:
            rmtree(specfile.parent)

        if "str" in testcase:
            spec_or_path = str(spec_or_path)

        if "doesn't exist" in testcase:
            with pytest.raises(RuntimeError) as excinfo:
                PkgHistoryProcessor(spec_or_path)
            if "spec doesn't exist" in testcase:
                expected_message = f"Spec file '{specfile}' doesn't exist in '{specfile.parent}'."
            else:
                expected_message = f"Spec file or path '{spec_or_path}' doesn't exist."
            assert str(excinfo.value) == expected_message
            return

        if "not a regular file" in testcase:
            specfile.unlink()
            os.mknod(specfile, stat.S_IFIFO | stat.S_IRUSR | stat.S_IWUSR)
            with pytest.raises(RuntimeError) as excinfo:
                PkgHistoryProcessor(spec_or_path)
            assert str(excinfo.value) == "File specified as `spec_or_path` is not a regular file."
            return

        if "wrong extension" in testcase:
            with pytest.raises(ValueError) as excinfo:
                PkgHistoryProcessor(spec_or_path)
            assert str(excinfo.value) == (
                "File specified as `spec_or_path` must have '.spec' as an extension."
            )
            return

        if "no git repo" in testcase:

            class GitError(Exception):
                pass

            pygit2.GitError = GitError
            pygit2.Repository.side_effect = GitError

        processor = PkgHistoryProcessor(spec_or_path)

        assert processor.specfile == specfile
        assert processor.path == specfile.parent

        pygit2.Repository.assert_called_once()

        if "no git repo" in testcase:
            assert processor.repo is None
        else:
            assert processor.repo

    @pytest.mark.parametrize("testcase", ("normal", "no spec file"))
    def test__get_rpm_version_for_commit(self, testcase, specfile, repo, processor):
        head_commit = repo[repo.head.target]

        if testcase == "no spec file":
            index = repo.index
            index.remove(specfile.name)
            index.write()

            tree = index.write_tree()

            parent, ref = repo.resolve_refish(repo.head.name)

            head_commit = repo[
                repo.create_commit(
                    ref.name,
                    repo.default_signature,
                    repo.default_signature,
                    "Be gone, spec file!",
                    tree,
                    [parent.oid],
                )
            ]

            assert processor._get_rpm_version_for_commit(head_commit) is None
        else:
            assert processor._get_rpm_version_for_commit(head_commit) == "1.0"

    @pytest.mark.parametrize("testcase", ("without commit", "with commit", "all results"))
    def test_run(self, testcase, repo, processor):
        def noop_visitor(commit, children_must_continue):
            current_result, parent_results = yield len(commit.parents) > 0
            yield current_result

        all_results = "all results" in testcase

        head_commit = repo[repo.head.target]

        if testcase == "with commit":
            args = [head_commit]
        else:
            args = []

        res = processor.run(*args, visitors=[noop_visitor], all_results=all_results)

        assert isinstance(res, dict)
        if all_results:
            assert all(isinstance(key, pygit2.Commit) for key in res)
            # only verify outcome for head commit below
            res = res[head_commit]
        else:
            assert all(isinstance(key, str) for key in res)

        assert res["commit-id"] == head_commit.id

    @pytest.mark.parametrize(
        "testcase",
        (
            "normal",
            "no git repo",
            "no commit specified",
            "root commit",
            "bump version",
        ),
    )
    def test_calculate_release_number(self, testcase, specfile, repo, processor, caplog):
        commit = repo[repo.head.target]
        if testcase not in ("no git repo", "root commit", "bump version"):
            expected_release_number = 2
        else:
            expected_release_number = 1

        if testcase == "no git repo":
            rmtree(specfile.parent / ".git")
            processor = PkgHistoryProcessor(specfile)
        elif testcase == "no commit specified":
            commit = None
        elif testcase == "root commit":
            commit = commit.parents[0]
        elif testcase == "bump version":
            with specfile.open("r") as sf:
                contents = sf.read()

            with specfile.open("w") as sf:
                sf.write(self.version_re.sub("Version: 2.0", contents))

            index = repo.index
            index.add(specfile.name)
            index.write()

            tree = index.write_tree()

            parent, ref = repo.resolve_refish(repo.head.name)
            repo.create_commit(
                ref.name,
                repo.default_signature,
                repo.default_signature,
                "Update to 2.0",
                tree,
                [parent.oid],
            )

        with caplog.at_level(logging.DEBUG):
            assert processor.calculate_release_number(commit) == expected_release_number
