import datetime as dt
from unittest import mock

import pytest

from rpmautospec.changelog import ChangelogEntry
from rpmautospec.exc import SpecParseFailure
from rpmautospec.subcommands import changelog


@pytest.mark.parametrize("testval", ("text", b"text"), ids=("str", "bytes"))
def test__coerce_to_str(testval):
    assert changelog._coerce_to_str(testval) == "text"


def test_collate_changelog():
    now = dt.datetime(2024, 1, 23, 12, 0)

    processor_results = {
        "changelog": (
            ChangelogEntry(
                {
                    "epoch-version": "1.0",
                    "release-complete": "2",
                    "timestamp": now,
                    "commitlog": "Just a commit",
                    "authorblurb": "Fred <vom@jupiter.planet>",
                }
            ),
            ChangelogEntry(
                {
                    "epoch-version": "1.0",
                    "release-complete": "1",
                    "data": "* Tue Jan 23 2024 Mork <vom@ork.planet> - 1.0-1\n- Foo",
                }
            ),
        ),
    }

    result = changelog.collate_changelog(processor_results)
    assert result == (
        "* Tue Jan 23 2024 Fred <vom@jupiter.planet> - 1.0-2\n"
        + "- Just a commit\n\n"
        + "* Tue Jan 23 2024 Mork <vom@ork.planet> - 1.0-1\n"
        + "- Foo"
    )


def test_do_generate_changelog(repo):
    result = changelog.do_generate_changelog(repo.workdir)
    assert "Jane Doe <jane.doe@example.com> - 1.0-2" in result
    assert "Jane Doe <jane.doe@example.com> - 1.0-1" in result
    assert "- Did something!" in result
    assert "- Initial commit" in result


def test_do_generate_changelog_error():
    with mock.patch.object(changelog, "PkgHistoryProcessor") as PkgHistoryProcessor:
        processor = PkgHistoryProcessor.return_value
        processor.run.return_value = {
            "verflags": {"error": "specfile-parse-error", "error-detail": "BOOP"}
        }
        processor.specfile.name = "test.spec"

        with pytest.raises(SpecParseFailure) as excinfo:
            changelog.do_generate_changelog("test")

    assert str(excinfo.value) == "Couldn’t parse spec file test.spec:\nBOOP"
