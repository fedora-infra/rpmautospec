from glob import glob
import logging
import os
import re
import shutil
import tempfile


from rpmautospec.changelog import produce_changelog
from rpmautospec.misc import koji_init
from rpmautospec.release import holistic_heuristic_algo

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
    process_distgit_parser.add_argument("dist", help="The dist tag")

    return subcmd_name


def is_autorel(line):
    return autorel_re.match(line)


def get_autorel(name, dist, session):
    koji_init(session)
    # evr=None forces to search from lower bound
    release = holistic_heuristic_algo(package=name, dist=dist, evr=None, strip_dist=True)
    return release


def process_distgit(srcdir, dist, session):
    name = os.path.basename(srcdir)
    new_rel = get_autorel(name, dist, session)
    specfile_names = glob(f"{srcdir}/*.spec")
    if len(specfile_names) != 1:
        # callback should be run only in if there is a single spec-file
        return

    specfile_name = specfile_names[0]

    has_autorel = False
    changelog_lineno = None
    has_autochangelog = None

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

    if has_autorel or has_autochangelog:
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


def main(args):
    """ Main method. """

    repopath = args.worktree_path
    dist = args.dist
    kojiclient = koji_init(args.koji_url)

    process_distgit(repopath, dist, kojiclient)
