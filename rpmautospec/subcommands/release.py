from pathlib import Path
from typing import Union

from ..exc import SpecParseFailure
from ..pkg_history import PkgHistoryProcessor


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
