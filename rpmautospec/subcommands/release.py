from pathlib import Path
from typing import Any, Union

from ..exc import SpecParseFailure
from ..pkg_history import PkgHistoryProcessor
from ..specparser import SpecParserError


def _run_release_number_visitor_full(
    spec_or_path: Union[str, Path],
    *,
    error_on_unparseable_spec: bool,
) -> dict[str, Any]:
    """Run release_number_visitor and return its full result.

    :param spec_or_path: The spec file or directory it is located in.
    :param error_on_unparseable_spec: Whether or not failure at parsing
        the current spec file should raise an exception.
    :return: the visitor's result
    """
    try:
        processor = PkgHistoryProcessor(spec_or_path)
    except SpecParserError as exc:
        raise SpecParseFailure(exc) from exc

    result = processor.run(visitors=(processor.release_number_visitor,))
    error = result["verflags"].get("error")
    if error and error_on_unparseable_spec:
        error_detail = result["verflags"]["error-detail"]
        raise SpecParseFailure(
            f"Couldn’t parse spec file {processor.specfile.name}", code=error, detail=error_detail
        )
    return result


def _run_release_number_visitor(
    spec_or_path: Union[str, Path],
    *,
    key: str,
    error_on_unparseable_spec: bool,
) -> Union[str, int, None]:
    """Run release_number_visitor and return a single key of its result.

    :param spec_or_path: The spec file or directory it is located in.
    :param key: The key to return from the visitor's result.
    :param error_on_unparseable_spec: Whether or not failure at parsing
        the current spec file should raise an exception.
    :return: the value stored under `key` in the visitor's result
    """
    return _run_release_number_visitor_full(
        spec_or_path, error_on_unparseable_spec=error_on_unparseable_spec
    )[key]


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
    return _run_release_number_visitor(
        spec_or_path,
        key="release-complete" if complete_release else "release-number",
        error_on_unparseable_spec=error_on_unparseable_spec,
    )


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


def do_calculate_release_number_and_z_base(
    spec_or_path: Union[str, Path],
    *,
    error_on_unparseable_spec: bool = True,
) -> tuple[int, int]:
    """Calculate the two numbers build tooling must inject for %autorelease -z to work.

    Runs the history walk only once for both numbers. Build tooling must define both macros
    together before building any spec through %autorelease, since it can generally not tell
    upfront whether -z is actually in use (z-base is 0 when it is not, which is also the correct
    value to inject in that case).

    :param spec_or_path: The spec file or directory it is located in.
    :param error_on_unparseable_spec: Whether or not failure at parsing
        the current spec file should raise an exception.
    :return: a (release_number, z_base) tuple, to be passed into the %autorelease macro as
        %_rpmautospec_release_number and %_rpmautospec_release_number_z_base, respectively
    """
    result = _run_release_number_visitor_full(
        spec_or_path, error_on_unparseable_spec=error_on_unparseable_spec
    )
    return result["release-number"], result["z-base"] or 0
