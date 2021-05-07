import logging
import os
import subprocess
from unittest import mock

import pytest

from rpmautospec import misc

__here__ = os.path.dirname(__file__)


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
                returncode=139,
                cmd=["command"],
                output="Some command",
                stderr="And it failed!",
            )
            with pytest.raises(subprocess.CalledProcessError) as excinfo:
                misc.run_command(["command"])
            assert str(excinfo.value) == "Command '['command']' returned non-zero exit status 139."
            assert any(rec.levelno == logging.ERROR for rec in caplog.records)

    def test_specfile_uses_rpmautospec_no_macros(self, caplog):
        """Test no macros on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = os.path.join(
            __here__,
            os.path.pardir,
            "test-data",
            "test-specfiles",
            "no-macros.spec",
        )

        result = misc.specfile_uses_rpmautospec(specfile_path)

        assert result is False

    def test_specfile_uses_rpmautospec_autorelease_only(self, caplog):
        """Test autorelease only on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = os.path.join(
            __here__,
            os.path.pardir,
            "test-data",
            "test-specfiles",
            "autorelease-only.spec",
        )

        result = misc.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        result_no_autorelease = misc.specfile_uses_rpmautospec(
            specfile_path, check_autorelease=False
        )
        assert result_no_autorelease is False

    def test_specfile_uses_rpmautospec_autochangelog_only(self, caplog):
        """Test autochangelog only on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = os.path.join(
            __here__,
            os.path.pardir,
            "test-data",
            "test-specfiles",
            "autochangelog-only.spec",
        )

        result = misc.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        result_no_changelog = misc.specfile_uses_rpmautospec(
            specfile_path, check_autochangelog=False
        )
        assert result_no_changelog is False

    def test_specfile_uses_rpmautospec_throws_error(self, caplog):
        """Test specfile_uses_rpmautospec() throws an error when both params are false"""
        caplog.set_level(logging.DEBUG)

        specfile_path = os.path.join(
            __here__,
            os.path.pardir,
            "test-data",
            "test-specfiles",
            "autochangelog-only.spec",
        )

        result = misc.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        with pytest.raises(ValueError):
            misc.specfile_uses_rpmautospec(
                specfile_path, check_autochangelog=False, check_autorelease=False
            )
