import sys
from argparse import ArgumentParser
from inspect import getfullargspec

from ..exc import SpecParseFailure
from ..subcommands.process_distgit import do_process_distgit


class CliDisplayedError(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg

    def show(self) -> None:
        print(f"Error: {self.msg}", file=sys.stderr)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_distgit = subparsers.add_parser("process-distgit")
    process_distgit.add_argument("spec_or_path")
    process_distgit.add_argument("target")

    return parser


def process_distgit(spec_or_path: str, target: str) -> None:
    try:
        do_process_distgit(spec_or_path=spec_or_path, target=target)
    except SpecParseFailure as exc:
        raise CliDisplayedError(exc.args[0]) from exc


def cli() -> int:
    parser = build_parser()

    args = parser.parse_args()
    method = globals()[args.command.replace("-", "_")]
    method_kwargs = {k: v for k, v in vars(args).items() if k in getfullargspec(method).args}

    try:
        method(**method_kwargs)
    except CliDisplayedError as exc:
        exc.show()
        return 1

    return 0
