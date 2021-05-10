import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Union

import pygit2

from .misc import get_rpm_current_version


log = logging.getLogger(__name__)


class PkgHistoryProcessor:
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

        try:
            if hasattr(pygit2, "GIT_REPOSITORY_OPEN_NO_SEARCH"):
                kwargs = {"flags": pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH}
            else:
                # pygit2 < 1.4.0
                kwargs = {}
            # pygit2 < 1.2.0 can't cope with pathlib.Path objects
            self.repo = pygit2.Repository(str(self.path), **kwargs)
        except pygit2.GitError:
            self.repo = None

    def _get_rpm_version_for_commit(self, commit):
        with TemporaryDirectory(prefix="rpmautospec-") as workdir:
            try:
                specblob = commit.tree[self.specfile.name]
            except KeyError:
                # no spec file
                return None

            specpath = Path(workdir) / self.specfile.name
            with specpath.open("wb") as specfile:
                specfile.write(specblob.data)

            return get_rpm_current_version(workdir, self.name, with_epoch=True)

    def calculate_release_number(self, commit: Optional[pygit2.Commit] = None) -> Optional[int]:
        if not self.repo:
            # no git repo -> no history
            return 1

        if not commit:
            commit = self.repo[self.repo.head.target]

        version = get_rpm_current_version(str(self.path), with_epoch=True)

        release = 1

        while True:
            log.info(f"checking commit {commit.hex}, version {version} - release {release}")
            if not commit.parents:
                break
            assert len(commit.parents) == 1

            parent = commit.parents[0]
            parent_version = self._get_rpm_version_for_commit(parent)
            log.info(f"  comparing against parent commit {parent.hex}, version {parent_version}")

            if parent_version != version:
                break

            release += 1
            commit = parent

        return release
