from pathlib import Path
from typing import Union

from ..exc import SpecParseFailure
from ..pkg_history import PkgHistoryProcessor


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

    complete_release_group = calc_release_parser.add_mutually_exclusive_group()

    complete_release_group.add_argument(
        "-c",
        "--complete-release",
        action="store_true",
        default=True,
        help="Print the complete release with flags (without dist tag)",
    )

    complete_release_group.add_argument(
        "-n",
        "--number-only",
        action="store_false",
        dest="complete_release",
        default=False,
        help="Print only the calculated release number",
    )

    return subcmd_name


def calculate_release(
    spec_or_path: Union[str, Path],
    *,
    complete_release: bool = True,
    error_on_unparseable_spec: bool,
) -> Union[str, int]:
    """Calculate release value (or number) of a package.

    :param spec_or_path: The spec file or directory it is located in.
    :param complete_release: Whether to return the complete release
        (without dist tag) or just the number.
    :param error_on_unparseable_spec: Whether or not failure at parsing
        the current spec file should raise an exception.
    :return: the release value or number
    """
    processor = PkgHistoryProcessor(spec_or_path)
    result = processor.run(visitors=(processor.release_number_visitor,))
    if error_on_unparseable_spec and result["epoch-version"] is None:
        # If epoch-version is None, this indicates that the spec file couldn’t be parsed.
        raise SpecParseFailure(f"Couldn’t parse spec file {processor.specfile.name}")
    return result["release-complete" if complete_release else "release-number"]


def calculate_release_number(
    spec_or_path: Union[str, Path],
    *,
    error_on_unparseable_spec: bool,
) -> int:
    """Calculate release number of a package.

    This number can be passed into the %autorelease macro as
    %_rpmautospec_release_number.

    :param spec_or_path: The spec file or directory it is located in.
    :param error_on_unparseable_spec: Whether or not failure at parsing
        the current spec file should raise an exception.
    :return: the release number
    """
    return calculate_release(
        spec_or_path, complete_release=False, error_on_unparseable_spec=error_on_unparseable_spec
    )


def main(args):
    """Main method."""
    release = calculate_release(
        args.spec_or_path,
        complete_release=args.complete_release,
        error_on_unparseable_spec=args.error_on_unparseable_spec,
    )
    print("Calculated release number:", release)
