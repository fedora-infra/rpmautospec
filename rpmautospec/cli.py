import argparse
import contextlib
import locale
import logging
import sys

from .exc import RpmautospecException
from .subcommands import changelog, convert, process_distgit, release

all_subcmds = (changelog, convert, process_distgit, release)
subcmd_modules_by_name = {}


def setup_logging(log_level: int):
    handlers = []

    # We want all messages logged at level INFO or lower to be printed to stdout
    info_handler = logging.StreamHandler(stream=sys.stdout)
    info_handler.setLevel(log_level)
    info_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    handlers.append(info_handler)

    # Don't log levels <= INFO to stderr
    logging.lastResort.addFilter(lambda record: record.levelno > logging.INFO)
    handlers.append(logging.lastResort)

    if log_level == logging.INFO:
        # In normal operation, don't decorate messages
        for handler in handlers:
            handler.setFormatter(logging.Formatter("%(message)s"))

    logging.basicConfig(level=log_level, handlers=handlers)


class CustomArgumentParser(argparse.ArgumentParser):
    """Custom argument parser class for this program

    This overrides the `formatter_class` globally, for all created subparsers.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", argparse.ArgumentDefaultsHelpFormatter)
        super().__init__(*args, **kwargs)


def get_arg_parser() -> CustomArgumentParser:
    global subcmd_modules_by_name

    parser = CustomArgumentParser(
        prog="rpmautospec",
        epilog="Environment variable $RPMAUTOSPEC_LESS can specify pager options"
        " (pager is currently only used by 'generate-changelog').",
    )

    # global arguments

    parser.add_argument(
        "--pager",
        action=argparse.BooleanOptionalAction,
        help="Start a pager automatically",
        default=True,
    )

    log_level_group = parser.add_mutually_exclusive_group()
    log_level_group.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        dest="log_level",
        const=logging.WARNING,
        default=logging.INFO,
        help="Be less talkative",
    )
    log_level_group.add_argument(
        "--debug",
        action="store_const",
        dest="log_level",
        const=logging.DEBUG,
        help="Enable debugging output",
    )

    parser.add_argument(
        "--error-on-unparseable-spec",
        help="Whether to throw an error if the current version of the spec file can’t be parsed",
        action=argparse.BooleanOptionalAction,
        default=True,
    )

    # parsers for sub-commands

    # ArgumentParser.add_subparsers() only accepts the `required` argument from Python 3.7 on.
    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.required = True

    for subcmd_module in all_subcmds:
        subcmd_name = subcmd_module.register_subcommand(subparsers)

        if subcmd_name in subcmd_modules_by_name:
            raise RuntimeError(f"Sub-command specified more than once: {subcmd_name}.")

        subcmd_modules_by_name[subcmd_name] = subcmd_module

    return parser


def get_cli_args(args: list[str]) -> argparse.Namespace:
    return get_arg_parser().parse_args(args)


@contextlib.contextmanager
def handle_expected_exceptions():
    """Suppress tracebacks on common "expected" exceptions"""
    try:
        yield
    except BrokenPipeError:
        pass
    except OSError as e:
        # this covers various cases like file not found / has wrong type / access is denied.
        sys.exit(f"error: {e}")


@handle_expected_exceptions()
def main():
    locale.setlocale(locale.LC_ALL, "")

    args = get_cli_args(sys.argv[1:])

    setup_logging(log_level=args.log_level)

    if args.subcommand:
        subcmd_module = subcmd_modules_by_name[args.subcommand]
        try:
            exit_code = subcmd_module.main(args)
        except RpmautospecException as exc:
            logging.error("%s", exc)
            exit_code = 1
        sys.exit(exit_code)
