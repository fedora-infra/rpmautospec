import logging
from pathlib import Path
from typing import Union

from ..pkg_history import PkgHistoryProcessor


log = logging.getLogger(__name__)


def register_subcommand(subparsers):
    subcmd_name = "calculate-release"

    calc_release_parser = subparsers.add_parser(
        subcmd_name,
        help="Calculate the next release tag for a package build",
    )

    calc_release_parser.add_argument(
        "spec_or_path",
        default=".",
        nargs="?",
        help="Path to package worktree or the spec file within",
    )

    return subcmd_name


def calculate_release(spec_or_path: Union[str, Path]) -> int:
    processor = PkgHistoryProcessor(spec_or_path)
    result = processor.run(visitors=(processor.release_number_visitor,))
    return result["release-complete"]


def main(args):
    """Main method."""
    release = calculate_release(args.spec_or_path)
    log.info("calculate_release release: %s", release)
