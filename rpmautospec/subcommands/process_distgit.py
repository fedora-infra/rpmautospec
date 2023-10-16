import logging
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Optional, Union

from rpmautospec_core import check_specfile_features

from ..pkg_history import PkgHistoryProcessor
from ..version import __version__


log = logging.getLogger(__name__)
__here__ = os.path.dirname(__file__)

RPMAUTOSPEC_TEMPLATE = """## START: Set by rpmautospec
## (rpmautospec version {version})
## RPMAUTOSPEC: {used_features}{autorelease_blurb_if_needed}
## END: Set by rpmautospec
"""

AUTORELEASE_TEMPLATE = """
%define autorelease(e:s:pb:n) %{{?-p:0.}}%{{lua:
    release_number = {autorelease_number:d};
    base_release_number = tonumber(rpm.expand("%{{?-b*}}%{{!?-b:1}}"));
    print(release_number + base_release_number - 1);
}}%{{?-e:.%{{-e*}}}}%{{?-s:.%{{-s*}}}}%{{!?-n:%{{?dist}}}}"""  # noqa: E501


def register_subcommand(subparsers):
    subcmd_name = "process-distgit"

    process_distgit_parser = subparsers.add_parser(
        subcmd_name,
    )

    process_distgit_parser.add_argument(
        "spec_or_path",
        help="Path to package worktree or the spec file within",
    )

    process_distgit_parser.add_argument(
        "target",
        help="Path where to write processed spec file",
    )

    return subcmd_name


def process_distgit(
    spec_or_path: Union[Path, str],
    target: Optional[Union[Path, str]] = None,
    *,
    enable_caching: bool = True,
) -> bool:
    """Process an RPM spec file in a distgit repository.

    :param spec_or_path: the spec file or path of the repository
    :param enable_caching: whether or not spec file feature test results
                           should be cached (disable in long-running
                           processes)
    :return: whether or not the spec file needed processing
    """
    processor = PkgHistoryProcessor(spec_or_path)

    specfile_mode = None
    if target is None:
        target = processor.specfile
        specfile_mode = stat.S_IMODE(target.stat().st_mode)
    elif isinstance(target, Path):
        target = Path(target)

    if enable_caching:
        features = check_specfile_features(processor.specfile)
    else:
        features = check_specfile_features.__wrapped__(processor.specfile)
    processing_necessary = (
        features.has_autorelease or features.has_autochangelog or not features.changelog_lineno
    )
    if not processing_necessary:
        return False

    needs_autochangelog = (
        features.changelog_lineno is None
        and features.autochangelog_lineno is None
        or features.has_autochangelog
    )

    visitors = [processor.release_number_visitor]
    if needs_autochangelog:
        visitors.append(processor.changelog_visitor)
    result = processor.run(visitors=visitors)

    autorelease_number = result["release-number"]

    with processor.specfile.open("r") as specfile, tempfile.NamedTemporaryFile("w") as tmp_specfile:
        # Process the spec file into a temporary file...
        if features.has_autorelease or needs_autochangelog:
            used_features = []

            if features.has_autorelease:
                autorelease_blurb_if_needed = AUTORELEASE_TEMPLATE.format(
                    autorelease_number=autorelease_number
                )
                used_features.append("autorelease")
            else:
                autorelease_blurb_if_needed = ""

            if needs_autochangelog:
                used_features.append("autochangelog")

            # Write %autorelease macro header
            print(
                RPMAUTOSPEC_TEMPLATE.format(
                    version=__version__,
                    used_features=", ".join(used_features),
                    autorelease_blurb_if_needed=autorelease_blurb_if_needed,
                ),
                file=tmp_specfile,
            )

        for lineno, line in enumerate(specfile, start=1):
            if features.changelog_lineno:
                if features.has_autochangelog and lineno > features.changelog_lineno:
                    break

            else:
                if features.has_autochangelog and lineno == features.autochangelog_lineno:
                    print("%changelog\n", file=tmp_specfile, end="")
                    break
            print(line, file=tmp_specfile, end="")

        if not features.has_autochangelog and features.changelog_lineno is None:
            print("\n%changelog\n", file=tmp_specfile, end="")

        if needs_autochangelog:
            print(
                "\n\n".join(entry.format() for entry in result["changelog"]),
                file=tmp_specfile,
            )

        tmp_specfile.flush()

        # ...and copy it back (potentially across device boundaries)
        shutil.copy2(tmp_specfile.name, target)
        if specfile_mode is not None:
            target.chmod(specfile_mode)


def main(args):
    """Main method."""
    spec_or_path = args.spec_or_path.rstrip(os.path.sep)
    process_distgit(spec_or_path, args.target)
