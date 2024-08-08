import locale
import logging
import sys
from typing import Optional

import click
import click_plugins

from .compat import cli_plugin_entry_points


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


@click_plugins.with_plugins(cli_plugin_entry_points())
@click.group(
    name="rpmautospec",
    epilog="Environment variable $RPMAUTOSPEC_LESS can specify pager options"
    + " (pager is currently only used by 'generate-changelog').",
)
@click.option(
    "--pager/--no-pager", help="Start a pager automatically", default=True, show_default=True
)
@click.option("--quiet", "-q", "log_level", flag_value=logging.WARNING, help="Be less talkative")
@click.option(
    "--debug",
    "log_level",
    flag_value=logging.DEBUG,
    help="Enable debugging output",
)
@click.option(
    "--error-on-unparseable-spec/--no-error-on-unparseable-spec",
    default=True,
    help="Throw an error if the current version of the spec file can’t be parsed",
    show_default=True,
)
@click.pass_context
def cli(ctx: click.Context, pager: bool, log_level: Optional[int], error_on_unparseable_spec: bool):
    locale.setlocale(locale.LC_ALL, "")

    ctx.ensure_object(dict)
    ctx.obj["pager"] = pager
    ctx.obj["log_level"] = log_level
    ctx.obj["error_on_unparseable_spec"] = error_on_unparseable_spec

    setup_logging(log_level=log_level or logging.INFO)
