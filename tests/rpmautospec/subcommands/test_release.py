import os.path
import tarfile
import tempfile
from contextlib import nullcontext
from pathlib import Path
from unittest import mock

import pytest

from rpmautospec.compat import rpm
from rpmautospec.exc import SpecParseFailure
from rpmautospec.subcommands import release

__here__ = os.path.dirname(__file__)


class TestRelease:
    """Test the rpmautospec.subcommands.release module"""

    @pytest.mark.parametrize(
        "testcase", ("complete-release", "numbers-only", "specfile-parse-failure")
    )
    def test_do_calculate_release(self, testcase):
        complete_release = "complete-release" in testcase
        specfile_parse_failure = "specfile-parse-failure" in testcase

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

            expected_release = "11" if complete_release else 11

            if specfile_parse_failure:
                expectation = pytest.raises(SpecParseFailure)
                specfile = unpacked_repo_dir / "dummy-test-package-gloster.spec"
                txt = specfile.read_text()
                specfile.write_text("Eat this!\n" + txt)
            else:
                expectation = nullcontext()

            with mock.patch.object(rpm, "setLogFile"), expectation as excinfo:
                result = release.do_calculate_release(
                    unpacked_repo_dir,
                    complete_release=complete_release,
                    error_on_unparseable_spec=True,
                )

            if specfile_parse_failure:
                assert str(excinfo.value) == f"Couldn’t parse spec file {specfile.name}"
            else:
                assert result == expected_release

    def test_do_calculate_release_number(self):
        with mock.patch.object(release, "do_calculate_release") as do_calculate_release:
            do_calculate_release.return_value = retval_sentinel = object()

            result = release.do_calculate_release_number("some.spec")

            assert result is retval_sentinel
            do_calculate_release.assert_called_once_with(
                "some.spec", complete_release=False, error_on_unparseable_spec=True
            )
