import datetime as dt
import locale
import re
from pathlib import Path
from unittest import mock

import pytest
import yaml

from rpmautospec import changelog

HERE = Path(__file__).parent
COMMITLOG_CHANGELOG_DIR = HERE.parent / "test-data" / "commitlogs"
COMMITLOGFILE_RE = re.compile(r"^commit-(?P<variant>.*)\.txt$")
TESTDATA = {}


@pytest.mark.parametrize("testcase", ("success-immediately", "success-eventually", "failure"))
def test_TimeLocaleManager(testcase):
    with mock.patch.object(changelog.locale, "setlocale") as setlocale:
        locale_error = locale.Error("unsupported locale setting")
        setlocale.side_effect = [
            "BOO",
            "en_US" if testcase == "success-immediately" else locale_error,
            "C" if "success" in testcase else locale_error,
        ]

        expected_calls = [mock.call(locale.LC_TIME), mock.call(locale.LC_TIME, "en_US")]

        if testcase != "success-immediately":
            expected_calls.append(mock.call(locale.LC_TIME, "C"))

        with changelog.TimeLocaleManager("en_US", "C"):
            # testing __enter__()
            assert setlocale.call_args_list == expected_calls
            setlocale.reset_mock()

        # testing __exit__()
        setlocale.assert_called_once_with(locale.LC_TIME, "BOO")


def _read_commitlog_changelog_testdata():
    if not TESTDATA:
        for commitlog_path in sorted(COMMITLOG_CHANGELOG_DIR.glob("commit*.txt")):
            match = COMMITLOGFILE_RE.match(commitlog_path.name)
            variant = match.group("variant")
            chlog_items_path = commitlog_path.with_name(f"expected-{variant}.yaml")
            chlog_entry_path = commitlog_path.with_name(f"expected-{variant}.txt")
            with open(chlog_items_path, "r") as chlog_items_fp:
                d = yaml.safe_load(chlog_items_fp)

            TESTDATA[variant] = (
                commitlog_path.read_text(),
                d["changelog_items"],  # required field
                chlog_entry_path.read_text(),
            )
    return TESTDATA


def pytest_generate_tests(metafunc):
    if (
        "commitlog_chlogitems" in metafunc.fixturenames
        or "commitlog_chlogentry" in metafunc.fixturenames
    ):
        _read_commitlog_changelog_testdata()

        if "commitlog_chlogitems" in metafunc.fixturenames:
            metafunc.parametrize(
                "commitlog_chlogitems",
                [(val[0], val[1]) for val in TESTDATA.values()],
                ids=(f"commitlog-{variant}" for variant in TESTDATA),
            )

        if "commitlog_chlogentry" in metafunc.fixturenames:
            metafunc.parametrize(
                "commitlog_chlogentry",
                [(val[0], val[2]) for val in TESTDATA.values()],
                ids=(f"commitlog-{variant}" for variant in TESTDATA),
            )


class TestChangelogEntry:
    @staticmethod
    def _parametrize_commitlog(commitlog, *, subject_with_dash, trailing_newline):
        if subject_with_dash:
            commitlog = f"- {commitlog}"

        if trailing_newline:
            if commitlog[-1] != "\n":
                commitlog += "\n"
        else:
            commitlog = commitlog.rstrip("\n")

        return commitlog

    @pytest.mark.parametrize("subject_with_dash", (True, False))
    @pytest.mark.parametrize("trailing_newline", (True, False))
    def test_commitlog_to_changelog_items(
        self, subject_with_dash, trailing_newline, commitlog_chlogitems
    ):
        commitlog, expected_changelog_items = commitlog_chlogitems

        commitlog = self._parametrize_commitlog(
            commitlog, subject_with_dash=subject_with_dash, trailing_newline=trailing_newline
        )

        changelog_items = changelog.ChangelogEntry.commitlog_to_changelog_items(commitlog)
        assert changelog_items == expected_changelog_items

    @pytest.mark.parametrize("with_epoch_version_release", (True, "epoch-version", False))
    @pytest.mark.parametrize("with_error_is_none", (False, True))
    @pytest.mark.parametrize("subject_with_dash", (True, False))
    @pytest.mark.parametrize("trailing_newline", (True, False))
    def test_format(
        self,
        with_epoch_version_release,
        with_error_is_none,
        subject_with_dash,
        trailing_newline,
        commitlog_chlogentry,
    ):
        commitlog, expected_changelog_entry = commitlog_chlogentry

        commitlog = self._parametrize_commitlog(
            commitlog, subject_with_dash=subject_with_dash, trailing_newline=trailing_newline
        )

        changelog_entry = changelog.ChangelogEntry(
            {
                "timestamp": dt.datetime(1970, 1, 1, 0, 0, 0),
                "authorblurb": "An Author <anauthor@example.com>",
                "epoch-version": None,
                "release-complete": None,
                "commitlog": commitlog,
            }
        )

        expected_evr = ""
        if with_epoch_version_release:
            changelog_entry["epoch-version"] = "1.0"
            expected_evr = " - 1.0"
            if with_epoch_version_release != "epoch-version":
                changelog_entry["release-complete"] = "1"
                expected_evr = " - 1.0-1"

        if with_error_is_none:
            changelog_entry["error"] = None

        expected_changelog_entry = (
            f"* Thu Jan 01 1970 An Author <anauthor@example.com>{expected_evr}\n"
            + expected_changelog_entry
        )

        formatted_changelog_entry = changelog_entry.format()
        assert formatted_changelog_entry == expected_changelog_entry.rstrip("\n")

    @pytest.mark.parametrize("error", ("string", "list"))
    def test_format_error(self, error):
        changelog_entry = changelog.ChangelogEntry(
            {
                "timestamp": dt.datetime(1970, 1, 1, 0, 0, 0),
                "authorblurb": "An Author <anauthor@example.com>",
                "epoch-version": "1.0",
                "release-complete": "1",
            }
        )

        if error == "string":
            changelog_entry["error"] = "a string"
        else:  # error == "list"
            changelog_entry["error"] = ["a string", "and another"]

        expected_changelog_entry = (
            "* Thu Jan 01 1970 An Author <anauthor@example.com> - 1.0-1\n- RPMAUTOSPEC: a string"
        )

        if error == "list":
            expected_changelog_entry += "\n- RPMAUTOSPEC: and another"

        formatted_changelog_entry = changelog_entry.format()
        assert formatted_changelog_entry == expected_changelog_entry.rstrip("\n")
