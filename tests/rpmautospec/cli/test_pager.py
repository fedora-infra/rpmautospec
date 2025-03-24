import os
from unittest import mock

import pytest

from rpmautospec.cli import pager


@pytest.mark.parametrize("testcase", ("enabled-withenv", "enabled-withoutenv", "disabled"))
@mock.patch.dict(os.environ)
def test_page(testcase):
    """Test the page() function."""
    if "withenv" in testcase:
        os.environ["RPMAUTOSPEC_LESS"] = "KMXF"
    else:
        os.environ.pop("RPMAUTOSPEC_LESS", None)

    with (
        mock.patch.object(pager.pydoc, "pager") as pydoc_pager,
        mock.patch.object(pager, "print") as print,
    ):
        pager.page("Hello!", enabled="enabled" in testcase)

    if "disabled" in testcase:
        pydoc_pager.assert_not_called()
        print.assert_called_with("Hello!")
    else:
        print.assert_not_called()
        pydoc_pager.assert_called_with("Hello!")
        if "withenv" in testcase:
            assert os.environ["LESS"] == "KMXF"
        else:
            assert os.environ["LESS"] == "FXMK"
