import logging
import sys
from unittest import mock

import pytest

from rpmautospec import cli


@pytest.mark.parametrize("log_level_name", ("CRITICAL", "WARNING", "INFO", "DEBUG"))
def test_setup_logging(log_level_name):
    """Test the setup_logging() function."""
    log_level = getattr(logging, log_level_name)

    with (
        mock.patch.object(cli.logging, "StreamHandler") as StreamHandler,
        mock.patch.object(cli.logging, "lastResort") as lastResort,
        mock.patch.object(cli.logging, "basicConfig") as basicConfig,
    ):
        info_handler = StreamHandler.return_value
        cli.setup_logging(log_level)

    StreamHandler.assert_called_once_with(stream=sys.stdout)

    info_handler.setLevel.assert_called_with(log_level)
    info_handler.addFilter.assert_called_once()

    lastResort.addFilter.assert_called_once()

    if log_level_name == "INFO":
        info_handler.setFormatter.assert_called_once()
        lastResort.setFormatter.assert_called_once()
    else:
        info_handler.setFormatter.assert_not_called()
        lastResort.setFormatter.assert_not_called()

    basicConfig.assert_called_once_with(level=log_level, handlers=[info_handler, lastResort])


def test_cli_help(cli_runner):
    """Test that getting top-level help works"""
    cli_runner.mix_stderr = False
    result = cli_runner.invoke(cli.cli, ["--help"])

    assert result.exit_code == 0

    assert "Usage: rpmautospec" in result.stdout
    assert not result.stderr


def test_cli(cli_runner):
    @cli.cli.command(hidden=True)
    def test():
        pass

    with mock.patch.object(cli, "setup_logging") as setup_logging:
        result = cli_runner.invoke(cli.cli, ["test"])

    assert result.exit_code == 0

    setup_logging.assert_called_with(log_level=logging.INFO)
