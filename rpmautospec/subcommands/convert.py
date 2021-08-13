import logging


log = logging.getLogger(__name__)


def register_subcommand(subparsers):
    subcmd_name = "convert"

    convert_parser = subparsers.add_parser(
        subcmd_name,
        help="Convert a package repository to use rpmautospec",
    )

    convert_parser.add_argument(
        "spec_or_path",
        default=".",
        nargs="?",
        help="Path to package worktree or spec file",
    )

    convert_parser.add_argument(
        "--message",
        "-m",
        default="Convert to rpmautospec",
        help="Message to use when committing changes",
    )

    convert_parser.add_argument(
        "--no-commit",
        "-n",
        action="store_true",
        help="Don't commit after making changes",
    )

    convert_parser.add_argument(
        "--no-changelog",
        action="store_true",
        help="Don't convert the %%changelog",
    )

    convert_parser.add_argument(
        "--no-release",
        action="store_true",
        help="Don't convert the Release field",
    )

    return subcmd_name


def main(args):
    """Main method."""
