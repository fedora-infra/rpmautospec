from pathlib import Path
from typing import Any, Optional, Union

from ..exc import SpecParseFailure
from ..pkg_history import PkgHistoryProcessor
from ..specparser import SpecParserError


def _coerce_to_str(str_or_bytes: Union[str, bytes]) -> str:
    if isinstance(str_or_bytes, bytes):
        str_or_bytes = str_or_bytes.decode("utf-8", errors="replace")
    return str_or_bytes


def collate_changelog(processor_results: dict[str, Any]) -> str:
    return "\n\n".join(_coerce_to_str(entry.format()) for entry in processor_results["changelog"])


def do_generate_changelog(
    spec_or_path: Union[Path, str],
    *,
    error_on_unparseable_spec: bool = True,
    git_tag_namespace: Optional[str] = None,
    changelog_mode: str = "accumulated",
    changelog_use_highest_release_tag: bool = False,
) -> str:
    try:
        processor = PkgHistoryProcessor(spec_or_path)
    except SpecParserError as exc:
        raise SpecParseFailure(exc) from exc

    result = processor.run(
        visitors=(processor.release_number_visitor, processor.changelog_visitor),
        git_tag_namespace=git_tag_namespace,
        changelog_mode=changelog_mode,
        changelog_use_highest_release_tag=changelog_use_highest_release_tag,
    )
    error = result["verflags"].get("error")
    if error and error_on_unparseable_spec:
        error_detail = result["verflags"]["error-detail"]
        raise SpecParseFailure(
            f"Couldn’t parse spec file {processor.specfile.name}", code=error, detail=error_detail
        )
    return collate_changelog(result)
