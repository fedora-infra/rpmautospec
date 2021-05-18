#!/usr/bin/python3
import logging
import re
import shutil
import tempfile
from pathlib import Path
from subprocess import CalledProcessError
from typing import Union

from .misc import (
    get_rpm_current_version,
    query_current_git_commit_hash,
    checkout_git_commit,
)


_log = logging.getLogger(__name__)

pathspec_unknown_re = re.compile(
    r"error: pathspec '[^']+' did not match any file\(s\) known to git"
)


def register_subcommand(subparsers):
    subcmd_name = "calculate-release"

    calc_release_parser = subparsers.add_parser(
        subcmd_name,
        help="Calculate the next release tag for a package build",
    )

    calc_release_parser.add_argument(
        "srcdir", help="Clone of the dist-git repository to use for input"
    )

    return subcmd_name


def calculate_release(srcdir: Union[str, Path]) -> int:
    # Count the number of commits between version changes to create the release
    releaseCount = 0

    srcdir = Path(srcdir)

    with tempfile.TemporaryDirectory(prefix="rpmautospec-") as workdir:
        repocopy = f"{workdir}/{srcdir.name}"
        shutil.copytree(srcdir, repocopy)

        # capture the hash of the current commit version
        head = query_current_git_commit_hash(repocopy)
        _log.info("calculate_release head: %s", head)

        latest_version = current_version = get_rpm_current_version(repocopy, with_epoch=True)

        # in loop/recursively:
        while latest_version == current_version:
            try:
                releaseCount += 1
                # while it's the same, go back a commit
                commit = checkout_git_commit(repocopy, head + "~" + str(releaseCount))
                _log.info("Checking commit %s ...", commit)
                current_version = get_rpm_current_version(repocopy, with_epoch=True)
                _log.info("... -> %s", current_version)
            except CalledProcessError as e:
                stderr = e.stderr.decode("UTF-8", errors="replace").strip()
                match = pathspec_unknown_re.match(stderr)
                if match:
                    break

        release = releaseCount

    return release


def main(args):
    """Main method."""
    release = calculate_release(srcdir=args.srcdir)
    _log.info("calculate_release release: %s", release)
