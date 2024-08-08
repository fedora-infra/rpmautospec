from contextlib import nullcontext
from unittest import mock

import pytest

from rpmautospec import compat


def test_minimal_blob_io():
    test_data = b"Hello"
    blob = mock.Mock(data=test_data)
    with compat.MinimalBlobIO(blob) as f:
        assert f.read() == test_data


@pytest.mark.parametrize("testcase", ("real", "mock-current", "mock-legacy"))
def test_cli_plugin_entry_points(testcase):
    result_sentinel = object()

    side_effect = []

    if testcase == "real":
        wrap_ctx = nullcontext()
    else:
        if "legacy" in testcase:
            side_effect = [
                TypeError("entry_points() got an unexpected keyword argument 'group'"),
                {"rpmautospec.cli": result_sentinel},
            ]
        else:
            side_effect = [result_sentinel]
        wrap_ctx = mock.patch.object(compat, "entry_points")

    with wrap_ctx as wrapped_entry_points:
        if side_effect:
            wrapped_entry_points.side_effect = side_effect
        result = compat.cli_plugin_entry_points()

    if testcase == "real":
        assert {ep.name for ep in result} == {
            "calculate-release",
            "convert",
            "generate-changelog",
            "process-distgit",
        }
    else:
        assert result is result_sentinel
        if "legacy" in testcase:
            assert wrapped_entry_points.call_args_list == [
                mock.call(group="rpmautospec.cli"),
                mock.call(),
            ]
        else:
            wrapped_entry_points.assert_called_once_with(group="rpmautospec.cli")
