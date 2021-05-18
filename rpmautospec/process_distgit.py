from glob import glob
import logging
import os
import re
import shutil
import tempfile


from .changelog import produce_changelog
from .misc import koji_init
from .release import calculate_release


_log = logging.getLogger(__name__)
__here__ = os.path.dirname(__file__)

autorelease_template = """## START: Set by rpmautospec
%define autorelease(e:s:p) %{{?-p:0.}}{autorelease_number}%{{?-e:.%{{-e*}}}}%{{?-s:.%{{-s*}}}}%{{?dist}}
## END: Set by rpmautospec
"""  # noqa: E501

autorelease_re = re.compile(r"\s*(?i:Release)\s*:.*%(?:autorelease(?:\s|$)|\{\??autorelease\})")
changelog_re = re.compile(r"^%changelog(?:\s.*)?$", re.IGNORECASE)
autochangelog_re = re.compile(r"\s*%(?:autochangelog|\{\??autochangelog\})\s*")


def register_subcommand(subparsers):
    subcmd_name = "process-distgit"

    process_distgit_parser = subparsers.add_parser(
        subcmd_name,
        help="Modify the contents of the specfile according to the repo",
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
        help="Check if the spec file uses %%autorelease or %%autochangelog macros at all.",
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


def is_autorelease(line):
    return autorelease_re.match(line)


def is_autochangelog(line):
    return autochangelog_re.match(line)


def get_autorelease(srcdir):
    # Not setting latest_evr, next_epoch_version just goes with what's in the package and latest
    # builds.
    release = calculate_release(srcdir=srcdir)
    return release


def get_specfile_name(srcdir):
    specfile_names = glob(f"{srcdir}/*.spec")
    if len(specfile_names) != 1:
        raise RuntimeError(f"Didn't find exactly one spec file in {srcdir}.")

    return specfile_names[0]


def check_distgit(srcdir):
    has_autorelease = False
    changelog_lineno = None
    has_autochangelog = None
    autochangelog_lineno = None

    specfile_name = get_specfile_name(srcdir)

    # Detect if %autorelease, %autochangelog are in use
    with open(specfile_name, "r") as specfile:
        # Process line by line to cope with large files
        for lineno, line in enumerate(iter(specfile), start=1):
            line = line.rstrip("\n")

            if not has_autorelease and is_autorelease(line):
                has_autorelease = True

            if changelog_lineno is None:
                if changelog_re.match(line):
                    changelog_lineno = lineno
            if has_autochangelog is None and is_autochangelog(line):
                has_autochangelog = True
                autochangelog_lineno = lineno

    return has_autorelease, has_autochangelog, changelog_lineno, autochangelog_lineno


def needs_processing(srcdir):
    has_autorelease, has_autochangelog, changelog_lineno, _ = check_distgit(srcdir)
    return has_autorelease or has_autochangelog or not changelog_lineno


def process_specfile(
    srcdir,
    has_autorelease=None,
    has_autochangelog=None,
    changelog_lineno=None,
    autochangelog_lineno=None,
):
    specfile_name = get_specfile_name(srcdir)

    autorelease_number = get_autorelease(srcdir)
    with open(specfile_name, "r") as specfile, tempfile.NamedTemporaryFile("w") as tmp_specfile:
        # Process the spec file into a temporary file...
        if has_autorelease:
            # Write %autorelease macro header
            print(
                autorelease_template.format(autorelease_number=autorelease_number),
                file=tmp_specfile,
            )

        for lineno, line in enumerate(specfile, start=1):
            if changelog_lineno:
                if has_autochangelog and lineno > changelog_lineno:
                    break

            else:
                if has_autochangelog and lineno == autochangelog_lineno:
                    print("%changelog\n", file=tmp_specfile, end="")
                    break
            print(line, file=tmp_specfile, end="")

        if has_autochangelog:
            print(
                "\n".join(produce_changelog(srcdir, latest_rel=autorelease_number)),
                file=tmp_specfile,
            )
        elif changelog_lineno is None:
            print("No changelog found, auto creating")
            print("\n%changelog\n", file=tmp_specfile, end="")
            print(
                "\n".join(produce_changelog(srcdir, latest_rel=autorelease_number)),
                file=tmp_specfile,
            )

        tmp_specfile.flush()

        # ...and copy it back (potentially across device boundaries)
        shutil.copy2(tmp_specfile.name, specfile_name)


def process_distgit(srcdir, dist, session, actions=None):
    if not actions:
        actions = ["process-specfile"]

    retval = True

    if "check" in actions or "process-specfile" in actions:
        has_autorelease, has_autochangelog, changelog_lineno, autochangelog_lineno = check_distgit(
            srcdir
        )
        processing_necessary = has_autorelease or has_autochangelog or not changelog_lineno
        if "process-specfile" not in actions:
            retval = processing_necessary

        # Only print output if explicitly requested
        if "check" in actions:
            features_used = []
            if has_autorelease:
                features_used.append("%autorelease")
            if has_autochangelog:
                features_used.append("%autochangelog")

            if not features_used:
                _log.info("The spec file doesn't use automatic release or changelog.")
            else:
                _log.info("Features used by the spec file: %s", ", ".join(features_used))

    if "process-specfile" in actions and processing_necessary:
        process_specfile(
            srcdir,
            dist,
            has_autorelease,
            has_autochangelog,
            changelog_lineno,
            autochangelog_lineno,
        )

    return retval


def main(args):
    """Main method."""

    repopath = args.worktree_path.rstrip(os.path.sep)
    dist = args.dist
    kojiclient = koji_init(args.koji_url)

    if process_distgit(repopath, dist, kojiclient, actions=args.actions):
        return 0
    else:
        return 1
