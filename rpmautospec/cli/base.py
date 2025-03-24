import logging
import sys


def setup_logging(log_level: int):
    handlers = []

    # We want all messages logged at level INFO or lower to be printed to stdout
    info_handler = logging.StreamHandler(stream=sys.stdout)
    info_handler.setLevel(log_level)
    info_handler.addFilter(lambda record: record.levelno <= logging.INFO)  # pragma: no cover
    handlers.append(info_handler)

    # Don't log levels <= INFO to stderr
    logging.lastResort.addFilter(lambda record: record.levelno > logging.INFO)  # pragma: no cover
    handlers.append(logging.lastResort)

    if log_level == logging.INFO:
        # In normal operation, don't decorate messages
        for handler in handlers:
            handler.setFormatter(logging.Formatter("%(message)s"))

    logging.basicConfig(level=log_level, handlers=handlers)
