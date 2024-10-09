from pathlib import Path
from typing import Any, Union

import click

from ..exc import SpecParseFailure
from ..pkg_history import PkgHistoryProcessor
from ..util import handle_expected_exceptions


def do_calculate_release(
    spec_or_path: Union[str, Path],
    *,
    complete_release: bool = True,
    error_on_unparseable_spec: bool = True,
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
    error = result["verflags"].get("error")
    if error and error_on_unparseable_spec:
        error_detail = result["verflags"]["error-detail"]
        raise SpecParseFailure(
            f"Couldn’t parse spec file {processor.specfile.name}", code=error, detail=error_detail
        )
    return result["release-complete" if complete_release else "release-number"]


def do_calculate_release_number(
    spec_or_path: Union[str, Path],
    *,
    error_on_unparseable_spec: bool = True,
) -> int:
    """Calculate release number of a package.

    This number can be passed into the %autorelease macro as
    %_rpmautospec_release_number.

    :param spec_or_path: The spec file or directory it is located in.
    :param error_on_unparseable_spec: Whether or not failure at parsing
        the current spec file should raise an exception.
    :return: the release number
    """
    return do_calculate_release(
        spec_or_path, complete_release=False, error_on_unparseable_spec=error_on_unparseable_spec
    )


@click.command()
@click.option(
    "--complete-release/--number-only",
    "-c/-n",
    default=True,
    help="Print the complete release with flags (without dist tag) or only the calculated release"
    + " number",
    show_default=True,
)
@click.argument("spec_or_path", type=click.Path(), default=".")
@click.pass_obj
@handle_expected_exceptions
def calculate_release(obj: dict[str, Any], complete_release: bool, spec_or_path: Path) -> None:
    """Calculate the next release tag for a package build"""
    try:
        release = do_calculate_release(
            spec_or_path,
            complete_release=complete_release,
            error_on_unparseable_spec=obj["error_on_unparseable_spec"],
        )
    except SpecParseFailure as exc:
        raise click.ClickException(*exc.args) from exc
    print("Calculated release number:", release)
