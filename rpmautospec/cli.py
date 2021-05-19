import argparse
import logging
import sys
import typing

from . import changelog, process_distgit, release


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


def get_cli_args(args: typing.List[str]) -> argparse.Namespace:
    global subcmd_modules_by_name

    parser = CustomArgumentParser(prog="rpmautospec")

    # global arguments

    parser.add_argument(
        "--koji-url",
        help="The base URL of the Koji hub",
        default="https://koji.fedoraproject.org/kojihub",
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

    # parsers for sub-commands

    # ArgumentParser.add_subparsers() only accepts the `required` argument from Python 3.7 on.
    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.required = True

    for subcmd_module in (changelog, release, process_distgit):
        subcmd_name = subcmd_module.register_subcommand(subparsers)

        if subcmd_name in subcmd_modules_by_name:
            raise RuntimeError(f"Sub-command specified more than once: {subcmd_name}.")

        subcmd_modules_by_name[subcmd_name] = subcmd_module

    return parser.parse_args(args)


def main():
    args = get_cli_args(sys.argv[1:])

    setup_logging(log_level=args.log_level)

    if args.subcommand:
        subcmd_module = subcmd_modules_by_name[args.subcommand]
        sys.exit(subcmd_module.main(args))
