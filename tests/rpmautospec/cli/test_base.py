import logging
import sys
from unittest import mock

import pytest

from rpmautospec.cli import base


@pytest.mark.parametrize("log_level_name", ("CRITICAL", "WARNING", "INFO", "DEBUG"))
def test_setup_logging(log_level_name):
    """Test the setup_logging() function."""
    log_level = getattr(logging, log_level_name)

    with (
        mock.patch.object(base.logging, "StreamHandler") as StreamHandler,
        mock.patch.object(base.logging, "lastResort") as lastResort,
        mock.patch.object(base.logging, "basicConfig") as basicConfig,
    ):
        info_handler = StreamHandler.return_value
        base.setup_logging(log_level)

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
