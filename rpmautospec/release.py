import logging
from pathlib import Path
from typing import Union

from .pkg_history import PkgHistoryProcessor


log = logging.getLogger(__name__)


def register_subcommand(subparsers):
    subcmd_name = "calculate-release"

    calc_release_parser = subparsers.add_parser(
        subcmd_name,
        help="Calculate the next release tag for a package build",
    )

    calc_release_parser.add_argument(
        "srcdir", help="Clone of the dist-git repository to use for input"
    )

    return subcmd_name


def calculate_release(srcdir: Union[str, Path]) -> int:
    processor = PkgHistoryProcessor(srcdir)
    result = processor.run(visitors=(processor.release_number_visitor,))
    return result["release-number"]


def main(args):
    """Main method."""
    release = calculate_release(srcdir=args.srcdir)
    log.info("calculate_release release: %s", release)
