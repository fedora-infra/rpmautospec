import logging
import re
import shutil
from pathlib import Path
from subprocess import CalledProcessError
from tempfile import TemporaryDirectory
from typing import Union

from .misc import checkout_git_commit, get_rpm_current_version, query_current_git_commit_hash


log = logging.getLogger(__name__)


class PkgHistoryProcessor:

    pathspec_unknown_re = re.compile(
        r"error: pathspec '[^']+' did not match any file\(s\) known to git"
    )

    def __init__(self, spec_or_path: Union[str, Path]):
        if isinstance(spec_or_path, str):
            spec_or_path = Path(spec_or_path)

        spec_or_path = spec_or_path.absolute()

        if not spec_or_path.exists():
            raise RuntimeError(f"Spec file or path '{spec_or_path}' doesn't exist.")
        elif spec_or_path.is_dir():
            self.path = spec_or_path
            self.name = spec_or_path.name
            self.specfile = spec_or_path / f"{self.name}.spec"
        elif spec_or_path.is_file():
            if spec_or_path.suffix != ".spec":
                raise ValueError(
                    "File specified as `spec_or_path` must have '.spec' as an extension."
                )
            self.path = spec_or_path.parent
            self.name = spec_or_path.stem
            self.specfile = spec_or_path
        else:
            raise RuntimeError("File specified as `spec_or_path` is not a regular file.")

        if not self.specfile.exists():
            raise RuntimeError(f"Spec file '{self.specfile}' doesn't exist in '{self.path}'.")

    def calculate_release_number(self) -> int:
        # Count the number of commits between version changes to create the release
        releaseCount = 0

        with TemporaryDirectory(prefix="rpmautospec-") as workdir:
            repocopy = f"{workdir}/{self.name}"
            shutil.copytree(self.path, repocopy)

            # capture the hash of the current commit version
            head = query_current_git_commit_hash(repocopy)
            log.info("calculate_release head: %s", head)

            latest_version = current_version = get_rpm_current_version(repocopy, with_epoch=True)

            # in loop/recursively:
            while latest_version == current_version:
                try:
                    releaseCount += 1
                    # while it's the same, go back a commit
                    commit = checkout_git_commit(repocopy, head + "~" + str(releaseCount))
                    log.info("Checking commit %s ...", commit)
                    current_version = get_rpm_current_version(repocopy, with_epoch=True)
                    log.info("... -> %s", current_version)
                except CalledProcessError as e:
                    stderr = e.stderr.decode("UTF-8", errors="replace").strip()
                    match = self.pathspec_unknown_re.match(stderr)
                    if match:
                        break

            release = releaseCount

        log.info("calculate_release release: %s", release)
        return release
