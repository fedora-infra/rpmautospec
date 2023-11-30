import datetime as dt
import locale
import os
import re
import stat
from calendar import LocaleTextCalendar
from shutil import SpecialFileError, rmtree
from unittest.mock import patch

import pygit2
import pytest

from rpmautospec.pkg_history import PkgHistoryProcessor


@pytest.fixture
def processor(repo):
    processor = PkgHistoryProcessor(repo.workdir)
    return processor


@pytest.fixture
def setlocale():
    """Allow temporary modification of locale settings."""
    saved_locale_settings = {
        category: locale.getlocale(getattr(locale, category))
        for category in dir(locale)
        if category.startswith("LC_") and category != "LC_ALL"
    }

    yield locale.setlocale

    for category, locale_settings in saved_locale_settings.items():
        locale.setlocale(getattr(locale, category), locale_settings)


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
            with pytest.raises(FileNotFoundError) as excinfo:
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
            with pytest.raises(SpecialFileError) as excinfo:
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
    def test__get_rpmverflags_for_commit(self, testcase, specfile, repo, processor):
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

            assert processor._get_rpmverflags_for_commit(head_commit) is None
        else:
            assert processor._get_rpmverflags_for_commit(head_commit)["epoch-version"] == "1.0"

    def test__get_rpmverflags_for_commit_cache(self, repo, processor):
        head_commit = repo[repo.head.target]

        with patch.object(processor, "_get_rpmverflags") as _get_rpmverflags:
            _get_rpmverflags.return_value = sentinel = object()

            assert processor._get_rpmverflags_for_commit(head_commit) is sentinel

            _get_rpmverflags.assert_called_once()
            _get_rpmverflags.reset_mock()

            assert processor._get_rpmverflags_for_commit(head_commit) is sentinel

            _get_rpmverflags.assert_not_called()

    @pytest.mark.parametrize(
        "testcase", ("without commit", "with commit", "all results", "locale set", "without repo")
    )
    def test_run(self, testcase, repo, processor, setlocale):
        if testcase == "locale set":
            setlocale(locale.LC_ALL, "de_DE.UTF-8")

        all_results = "all results" in testcase

        if testcase == "without repo":
            rmtree(repo.path)
            processor = PkgHistoryProcessor(repo.workdir)
            head_commit = None
        else:
            head_commit = repo[repo.head.target]

        if testcase == "with commit":
            args = [head_commit]
        else:
            args = []

        res = processor.run(
            *args,
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            all_results=all_results,
        )

        assert isinstance(res, dict)
        if all_results:
            assert all(isinstance(key, pygit2.Commit) for key in res)
            # only verify outcome for head commit below
            res = res[head_commit]
        else:
            assert all(isinstance(key, str) for key in res)

        changelog = res["changelog"]
        top_entry = changelog[0]

        if testcase == "without repo":
            assert res["release-number"] == 1

            for snippet in (
                processor._get_rpm_packager(),
                "- Uncommitted changes",
            ):
                assert snippet in top_entry.format()
        else:
            assert res["commit-id"] == head_commit.id
            assert res["release-number"] == 2
            assert top_entry["commit-id"] == head_commit.id

            for snippet in (
                "Jane Doe <jane.doe@example.com>",
                "- Did nothing!",
            ):
                assert snippet in top_entry.format()

            cal = LocaleTextCalendar(firstweekday=0, locale="C.UTF-8")
            commit_time = dt.datetime.fromtimestamp(head_commit.commit_time, dt.timezone.utc)
            weekdayname = cal.formatweekday(day=commit_time.weekday(), width=3)
            monthname = cal.formatmonthname(
                theyear=commit_time.year,
                themonth=commit_time.month,
                width=1,
                withyear=False,
            )[:3]
            expected_date_blurb = (
                f"* {weekdayname} {monthname} {commit_time.day:02} {commit_time.year}"
            )
            assert top_entry.format().startswith(expected_date_blurb)

        assert all("error" not in entry for entry in changelog)
