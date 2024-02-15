from pathlib import Path
from typing import Any, Union

from .. import pager
from ..exc import SpecParseFailure
from ..pkg_history import PkgHistoryProcessor


def register_subcommand(subparsers):
    subcmd_name = "generate-changelog"

    gen_changelog_parser = subparsers.add_parser(
        subcmd_name,
        help="Generate changelog entries from git commit logs",
    )

    gen_changelog_parser.add_argument(
        "spec_or_path",
        default=".",
        nargs="?",
        help="Path to package worktree or the spec file within",
    )

    return subcmd_name


def _coerce_to_str(str_or_bytes: Union[str, bytes]) -> str:
    if isinstance(str_or_bytes, bytes):
        str_or_bytes = str_or_bytes.decode("utf-8", errors="replace")
    return str_or_bytes


def collate_changelog(processor_results: dict[str, Any]) -> str:
    return "\n\n".join(_coerce_to_str(entry.format()) for entry in processor_results["changelog"])


def produce_changelog(
    spec_or_repo: Union[Path, str], *, error_on_unparseable_spec: bool = True
) -> str:
    processor = PkgHistoryProcessor(spec_or_repo)
    result = processor.run(visitors=(processor.release_number_visitor, processor.changelog_visitor))
    error = result["verflags"].get("error")
    if error and error_on_unparseable_spec:
        error_detail = result["verflags"]["error-detail"]
        raise SpecParseFailure(
            f"Couldn’t parse spec file {processor.specfile.name}", code=error, detail=error_detail
        )
    return collate_changelog(result)


def main(args):
    """Main method."""
    changelog = produce_changelog(
        args.spec_or_path, error_on_unparseable_spec=args.error_on_unparseable_spec
    )
    pager.page(changelog, enabled=args.pager)
