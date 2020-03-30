import logging
import subprocess
from unittest import mock

import pytest

from rpmautospec import misc


class TestMisc:
    """Test the rpmautospec.misc module"""

    @mock.patch("rpmautospec.misc.subprocess.check_output")
    @pytest.mark.parametrize("raise_exception", (False, True))
    def test_run_command(self, check_output, raise_exception, caplog):
        """Test run_command()"""
        caplog.set_level(logging.DEBUG)

        if not raise_exception:
            check_output.return_value = "Some output"
            assert misc.run_command(["command"]) == "Some output"
            check_output.assert_called_once_with(["command"], cwd=None, stderr=subprocess.PIPE)
            assert not any(rec.levelno >= logging.WARNING for rec in caplog.records)
        else:
            check_output.side_effect = subprocess.CalledProcessError(
                returncode=139, cmd=["command"], output="Some command", stderr="And it failed!",
            )
            with pytest.raises(subprocess.CalledProcessError) as excinfo:
                misc.run_command(["command"])
            assert str(excinfo.value) == "Command '['command']' returned non-zero exit status 139."
            assert any(rec.levelno == logging.ERROR for rec in caplog.records)
