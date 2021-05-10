#!/usr/bin/python3
import logging
from pathlib import Path
from typing import Union

from .pkg_history import PkgHistoryProcessor


_log = logging.getLogger(__name__)


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
    release_number = processor.calculate_release_number()
    return release_number


def main(args):
    """Main method."""
    release = calculate_release(srcdir=args.srcdir)
    _log.info("calculate_release release: %s", release)
