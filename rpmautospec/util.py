import logging
import sys
from functools import partial, wraps
from typing import Callable, Optional


def in_debug() -> bool:
    """Determine if debugging is enabled.

    :return: True if the root logger is set to DEBUG
    """
    return logging.getLogger().level <= logging.DEBUG


def handle_expected_exceptions(
    func: Optional[Callable] = None,
    *,
    ignore_exceptions: tuple[Callable] = (BrokenPipeError,),
    report_exit_exceptions: tuple[Callable] = (OSError,),
) -> Callable:
    """Wrap a function to treat certain exceptions sensibly.

    :param ignore_exceptions: Exceptions to be ignored
    :param report_exit_exceptions: Exceptions to be reported with exit
    """
    if not func:
        return partial(
            handle_expected_exceptions,
            ignore_exceptions=ignore_exceptions,
            report_exit_exceptions=report_exit_exceptions,
        )

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ignore_exceptions:
            if in_debug():
                raise
        except report_exit_exceptions as e:
            if in_debug():
                raise
            else:
                sys.exit(f"Error: {e}")

    return wrapper
