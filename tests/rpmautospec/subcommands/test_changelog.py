import datetime as dt
from unittest import mock

import pytest

from rpmautospec.changelog import ChangelogEntry
from rpmautospec.exc import SpecParseFailure
from rpmautospec.subcommands import changelog


def test_register_subcommand():
    subparsers = mock.Mock()
    cmd_parser = subparsers.add_parser.return_value

    subcmd_name = changelog.register_subcommand(subparsers)

    assert subcmd_name == "generate-changelog"
    subparsers.add_parser.assert_called_once_with(subcmd_name, help=mock.ANY)
    cmd_parser.add_argument.assert_any_call("spec_or_path", default=".", nargs="?", help=mock.ANY)


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


def test_produce_changelog(repo):
    result = changelog.produce_changelog(repo.workdir)
    assert "Jane Doe <jane.doe@example.com> - 1.0-2" in result
    assert "Jane Doe <jane.doe@example.com> - 1.0-1" in result
    assert "- Did something!" in result
    assert "- Initial commit" in result


def test_produce_changelog_error():
    with mock.patch.object(changelog, "PkgHistoryProcessor") as PkgHistoryProcessor:
        processor = PkgHistoryProcessor.return_value
        processor.run.return_value = {
            "verflags": {"error": "specfile-parse-error", "error-detail": "BOOP"}
        }
        processor.specfile.name = "test.spec"

        with pytest.raises(SpecParseFailure) as excinfo:
            changelog.produce_changelog("test")

    assert str(excinfo.value) == "Couldn’t parse spec file test.spec:\nBOOP"


def test_main():
    with mock.patch.object(changelog, "produce_changelog") as produce_changelog, mock.patch.object(
        changelog, "pager"
    ) as pager:
        args = mock.Mock()
        produced_changelog = produce_changelog.return_value

        changelog.main(args)

        produce_changelog.assert_called_once_with(
            args.spec_or_path, error_on_unparseable_spec=args.error_on_unparseable_spec
        )
        pager.page.assert_called_once_with(produced_changelog, enabled=args.pager)
