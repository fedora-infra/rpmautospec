from contextlib import nullcontext

import pytest

from rpmautospec import util


@pytest.mark.parametrize("log_level", ("DEBUG", "INFO"))
def test_in_debug(log_level, caplog):
    with caplog.at_level(log_level):
        assert util.in_debug() == (log_level == "DEBUG")


@pytest.mark.parametrize("log_level", ("DEBUG", "INFO"))
@pytest.mark.parametrize("exception", (BrokenPipeError, OSError))
@pytest.mark.parametrize("with_parms", (False, True), ids=("without-parms", "with-parms"))
def test_handle_expected_exceptions(log_level, exception, with_parms, caplog, capsys):
    def test_fn():
        raise exception("BOO")

    if with_parms:
        wrapped_test_fn = util.handle_expected_exceptions()(test_fn)
    else:
        wrapped_test_fn = util.handle_expected_exceptions(test_fn)

    if log_level == "DEBUG":
        expectation = pytest.raises(exception)
    else:
        if exception is OSError:
            expectation = pytest.raises(SystemExit)
        else:
            expectation = nullcontext()

    with caplog.at_level(log_level), expectation as exc_info:
        wrapped_test_fn()

    if exception is OSError and log_level != "DEBUG":
        assert str(exc_info.value) == "Error: BOO"
