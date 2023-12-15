import os.path
import tarfile
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from rpmautospec.subcommands import release

__here__ = os.path.dirname(__file__)


class TestRelease:
    """Test the rpmautospec.subcommands.release module"""

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
                assert release.calculate_release(unpacked_repo_dir) == expected_release
            else:
                args = mock.Mock()
                args.spec_or_path = unpacked_repo_dir
                release.main(args)

                captured = capsys.readouterr()
                assert f"Calculated release number: {expected_release}" in captured.out
