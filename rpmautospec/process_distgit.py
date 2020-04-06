from glob import glob
import logging
import os
import re
import shutil
import tempfile

import rpm

from .changelog import produce_changelog
from .misc import koji_init
from .release import holistic_heuristic_algo
from .tag_package import tag_package


_log = logging.getLogger(__name__)
__here__ = os.path.dirname(__file__)

autorel_macro_path = os.path.join(__here__, "etc", "autorel-macro.txt")
autorel_template = """## START: Set by rpmautospec
%define _autorel_normal_cadence {autorel_normal}%{{?_autorel_extraver}}%{{?_autorel_snapinfo}}%{{?dist}}
%define _autorel_hotfix_cadence %nil
%define _autorel_prerel_cadence %nil
%define _autorel_prerel_hotfix_cadence %nil
## END: Set by rpmautospec
"""  # noqa: E501

autorel_re = re.compile(r"^\s*(?i:Release)\s*:\s+%(?:autorel(?:\s|$)|\{autorel[^\}]*\})")
changelog_re = re.compile(r"^%changelog(?:\s.*)?$", re.IGNORECASE)
autochangelog_re = re.compile(r"^\s*%(?:autochangelog|\{autochangelog\})\s*$")


def register_subcommand(subparsers):
    subcmd_name = "process-distgit"

    process_distgit_parser = subparsers.add_parser(
        subcmd_name, help="Modify the contents of the specfile according to the repo",
    )

    process_distgit_parser.add_argument("worktree_path", help="Path to the dist-git worktree")
    process_distgit_parser.add_argument(
        "dist", nargs="?", help="The dist tag (taken from the %%dist RPM macro if not specified)"
    )

    process_distgit_parser.add_argument(
        "--check",
        dest="actions",
        action="append_const",
        const="check",
        help="Check if the spec file uses %%autorel or %%autochangelog macros at all.",
    )

    process_distgit_parser.add_argument(
        "--tag-package",
        dest="actions",
        action="append_const",
        const="tag-package",
        help="Tag existing builds in the specified package repository.",
    )

    process_distgit_parser.add_argument(
        "--process-specfile",
        dest="action",
        action="append_const",
        const="process-specfile",
        help="Generate next release and changelog values and write them into the spec file.",
    )

    return subcmd_name


def is_autorel(line):
    return autorel_re.match(line)


def get_autorel(srcdir, dist, session):
    # Not setting latest_evr, next_epoch_version just goes with what's in the package and latest
    # builds.
    release = holistic_heuristic_algo(srcdir=srcdir, dist=dist, strip_dist=True)
    return release


def get_specfile_name(srcdir):
    specfile_names = glob(f"{srcdir}/*.spec")
    if len(specfile_names) != 1:
        raise RuntimeError(f"Didn't find exactly one spec file in {srcdir}.")

    return specfile_names[0]


def check_distgit(srcdir):
    has_autorel = False
    changelog_lineno = None
    has_autochangelog = None

    specfile_name = get_specfile_name(srcdir)

    # Detect if %autorel, %autochangelog are in use
    with open(specfile_name, "r") as specfile:
        # Process line by line to cope with large files
        for lineno, line in enumerate(iter(specfile), start=1):
            line = line.rstrip("\n")

            if not has_autorel and is_autorel(line):
                has_autorel = True

            if changelog_lineno is None:
                if changelog_re.match(line):
                    changelog_lineno = lineno
            elif has_autochangelog is None:
                if autochangelog_re.match(line):
                    has_autochangelog = True
                elif line.strip():
                    # Anything else than %autochangelog after %changelog -> hands off
                    has_autochangelog = False

    return has_autorel, has_autochangelog, changelog_lineno


def needs_processing(srcdir):
    has_autorel, has_autochangelog, changelog_lineno = check_distgit(srcdir)
    return has_autorel or has_autochangelog


def process_specfile(srcdir, dist, session, has_autorel, has_autochangelog, changelog_lineno):
    specfile_name = get_specfile_name(srcdir)

    if not dist:
        dist = rpm.expandMacro("%dist")

    if dist.startswith("."):
        dist = dist[1:]

    new_rel = get_autorel(srcdir, dist, session)
    with open(specfile_name, "r") as specfile, tempfile.NamedTemporaryFile("w") as tmp_specfile:
        # Process the spec file into a temporary file...
        if has_autorel:
            # Write %autorel macro header
            with open(autorel_macro_path, "r") as autorel_macro_file:
                print(autorel_template.format(autorel_normal=new_rel), file=tmp_specfile)
                for line in autorel_macro_file:
                    print(line, file=tmp_specfile, end="")

        for lineno, line in enumerate(specfile, start=1):
            if has_autochangelog and lineno > changelog_lineno:
                break

            print(line, file=tmp_specfile, end="")

        if has_autochangelog:
            print("\n".join(produce_changelog(srcdir, latest_rel=new_rel)), file=tmp_specfile)

        tmp_specfile.flush()

        # ...and copy it back (potentially across device boundaries)
        shutil.copy2(tmp_specfile.name, specfile_name)


def process_distgit(srcdir, dist, session, actions=None):
    if not actions:
        actions = ["process-specfile"]

    retval = True

    if "check" in actions or "process-specfile" in actions:
        has_autorel, has_autochangelog, changelog_lineno = check_distgit(srcdir)
        processing_necessary = has_autorel or has_autochangelog
        if "process-specfile" not in actions:
            retval = processing_necessary

        # Only print output if explicitly requested
        if "check" in actions:
            features_used = []
            if has_autorel:
                features_used.append("%autorel")
            if has_autochangelog:
                features_used.append("%autochangelog")

            if not features_used:
                _log.info("The spec file doesn't use automatic release or changelog.")
            else:
                _log.info("Features used by the spec file: %s", ", ".join(features_used))

    if "tag-package" in actions:
        tag_package(srcdir, session)

    if "process-specfile" in actions and processing_necessary:
        process_specfile(srcdir, dist, session, has_autorel, has_autochangelog, changelog_lineno)

    return retval


def main(args):
    """ Main method. """

    repopath = args.worktree_path.rstrip(os.path.sep)
    dist = args.dist
    kojiclient = koji_init(args.koji_url)

    if process_distgit(repopath, dist, kojiclient, actions=args.actions):
        return 0
    else:
        return 1
