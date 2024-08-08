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

    @pytest.mark.parametrize("method_to_test", ("do_calculate_release", "calculate_release"))
    def test_calculate_release(self, method_to_test, cli_runner):
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

            with mock.patch("rpm.setLogFile"):
                if method_to_test == "do_calculate_release":
                    assert (
                        release.do_calculate_release(
                            unpacked_repo_dir, error_on_unparseable_spec=True
                        )
                        == expected_release
                    )
                else:
                    args = [str(unpacked_repo_dir)]
                    result = cli_runner.invoke(
                        release.calculate_release,
                        args,
                        obj={"error_on_unparseable_spec": True},
                    )

                    assert result.exit_code == 0

                    assert f"Calculated release number: {expected_release}" in result.stdout

    def test_do_calculate_release_error(self, cli_runner):
        with mock.patch.object(release, "PkgHistoryProcessor") as PkgHistoryProcessor:
            processor = PkgHistoryProcessor.return_value
            processor.run.return_value = {
                "verflags": {"error": "specfile-parse-error", "error-detail": "HAHA"}
            }
            processor.specfile.name = "test.spec"

            with pytest.raises(SpecParseFailure) as excinfo:
                release.do_calculate_release("test")

        assert str(excinfo.value) == "Couldn’t parse spec file test.spec:\nHAHA"

    def test_do_calculate_release_number(self):
        with mock.patch.object(release, "do_calculate_release") as do_calculate_release:
            do_calculate_release.return_value = retval_sentinel = object()

            result = release.do_calculate_release_number("some.spec")

            assert result is retval_sentinel
            do_calculate_release.assert_called_once_with(
                "some.spec", complete_release=False, error_on_unparseable_spec=True
            )
