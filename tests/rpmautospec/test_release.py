import logging
import os.path
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from rpmautospec import release


__here__ = os.path.dirname(__file__)


class TestRelease:
    """Test the rpmautospec.release module"""

    @pytest.mark.parametrize("method_to_test", ("calculate_release", "main"))
    def test_calculate_release(self, method_to_test, caplog):
        with tempfile.TemporaryDirectory() as workdir:
            with tarfile.open(
                os.path.join(
                    __here__,
                    os.path.pardir,
                    "test-data",
                    "repodata",
                    "dummy-test-package-gloster-git.tar.gz",
                )
            ) as tar:
                tar.extractall(path=workdir)

            unpacked_repo_dir = Path(workdir) / "dummy-test-package-gloster"

            expected_release_number = 11

            if method_to_test == "calculate_release":
                assert release.calculate_release(unpacked_repo_dir) == expected_release_number
            else:
                with caplog.at_level(logging.INFO):
                    args = Mock()
                    args.spec_or_path = unpacked_repo_dir
                    release.main(args)
                assert f"calculate_release release: {expected_release_number}" in caplog.text
