from pathlib import Path
from typing import Any, Union

import click

from .. import pager
from ..exc import SpecParseFailure
from ..pkg_history import PkgHistoryProcessor
from ..util import handle_expected_exceptions


def _coerce_to_str(str_or_bytes: Union[str, bytes]) -> str:
    if isinstance(str_or_bytes, bytes):
        str_or_bytes = str_or_bytes.decode("utf-8", errors="replace")
    return str_or_bytes


def collate_changelog(processor_results: dict[str, Any]) -> str:
    return "\n\n".join(_coerce_to_str(entry.format()) for entry in processor_results["changelog"])


def do_generate_changelog(
    spec_or_path: Union[Path, str], *, error_on_unparseable_spec: bool = True
) -> str:
    processor = PkgHistoryProcessor(spec_or_path)
    result = processor.run(visitors=(processor.release_number_visitor, processor.changelog_visitor))
    error = result["verflags"].get("error")
    if error and error_on_unparseable_spec:
        error_detail = result["verflags"]["error-detail"]
        raise SpecParseFailure(
            f"Couldn’t parse spec file {processor.specfile.name}", code=error, detail=error_detail
        )
    return collate_changelog(result)


@click.command()
@click.argument("spec_or_path", type=click.Path(), default=".")
@click.pass_obj
@handle_expected_exceptions
def generate_changelog(obj: dict[str, Any], spec_or_path: Path) -> None:
    """Generate changelog entries from git commit logs"""
    changelog = do_generate_changelog(
        spec_or_path, error_on_unparseable_spec=obj["error_on_unparseable_spec"]
    )
    pager.page(changelog, enabled=obj["pager"])
