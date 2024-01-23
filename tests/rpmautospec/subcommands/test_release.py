import os.path
import tarfile
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from rpmautospec.exc import SpecParseFailure
from rpmautospec.subcommands import release

__here__ = os.path.dirname(__file__)


class TestRelease:
    """Test the rpmautospec.subcommands.release module"""

    def test_register_subcommand(self):
        subparsers = mock.Mock()
        calc_release_parser = subparsers.add_parser.return_value
        complete_release_group = calc_release_parser.add_mutually_exclusive_group.return_value

        subcmd_name = release.register_subcommand(subparsers)

        assert subcmd_name == "calculate-release"
        subparsers.add_parser.assert_called_once_with(subcmd_name, help=mock.ANY)
        calc_release_parser.add_argument.assert_called_once_with(
            "spec_or_path", default=".", nargs="?", help=mock.ANY
        )
        calc_release_parser.add_mutually_exclusive_group.assert_called_once_with()
        complete_release_group.add_argument.assert_has_calls(
            (
                mock.call(
                    "-c",
                    "--complete-release",
                    action="store_true",
                    default=True,
                    help=mock.ANY,
                ),
                mock.call(
                    "-n",
                    "--number-only",
                    action="store_false",
                    dest="complete_release",
                    default=False,
                    help=mock.ANY,
                ),
            ),
            any_order=True,
        )

    @pytest.mark.parametrize("method_to_test", ("calculate_release", "main"))
    def test_calculate_release(self, method_to_test, capsys):
        with tempfile.TemporaryDirectory() as workdir:
            with tarfile.open(
                os.path.join(
                    __here__,
                    os.path.pardir,
                    os.path.pardir,
                    "test-data",
                    "repodata",
                    "dummy-test-package-gloster-git.tar.gz",
                )
            ) as tar:
                # Ensure unpackaged files are owned by user
                for member in tar:
                    member.uid = os.getuid()
                    member.gid = os.getgid()

                try:
                    tar.extractall(path=workdir, numeric_owner=True, filter="data")
                except TypeError:
                    # Filtering was introduced in Python 3.12.
                    tar.extractall(path=workdir, numeric_owner=True)

            unpacked_repo_dir = Path(workdir) / "dummy-test-package-gloster"

            expected_release = "11"

            if method_to_test == "calculate_release":
                assert (
                    release.calculate_release(unpacked_repo_dir, error_on_unparseable_spec=True)
                    == expected_release
                )
            else:
                args = mock.Mock()
                args.spec_or_path = unpacked_repo_dir
                release.main(args)

                captured = capsys.readouterr()
                assert f"Calculated release number: {expected_release}" in captured.out

    def test_calculate_release_error(self):
        with mock.patch.object(release, "PkgHistoryProcessor") as PkgHistoryProcessor:
            processor = PkgHistoryProcessor.return_value
            processor.run.return_value = {"epoch-version": None}
            processor.specfile.name = "test.spec"

            with pytest.raises(SpecParseFailure) as excinfo:
                release.calculate_release("test")

        assert str(excinfo.value) == "Couldn’t parse spec file test.spec"

    def test_calculate_release_number(self):
        with mock.patch.object(release, "calculate_release") as calculate_release:
            calculate_release.return_value = retval_sentinel = object()
            spec_or_path = object()

            result = release.calculate_release_number(spec_or_path)

            assert result is retval_sentinel
            calculate_release.assert_called_once_with(
                spec_or_path, complete_release=False, error_on_unparseable_spec=True
            )
