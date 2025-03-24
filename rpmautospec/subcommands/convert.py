import logging
import re
from pathlib import Path
from shutil import SpecialFileError
from typing import Optional, Union

from rpmautospec_core.main import autochangelog_re, autorelease_re, changelog_re

from ..compat import pygit2
from ..exc import SpecParseFailure

log = logging.getLogger(__name__)

release_re = re.compile(r"^(?P<tag>(?i:Release)\s*:\s*)")


class ConversionError(Exception):
    """Exception specific to repository conversion."""


class FileModifiedError(ConversionError):
    """A file under version control has been modified."""


class FileUntrackedError(ConversionError):
    """A file is not tracked in the repository."""


class PkgConverter:
    def __init__(self, spec_or_path: Union[Path, str]):
        if isinstance(spec_or_path, str):
            spec_or_path = Path(spec_or_path)

        spec_or_path = spec_or_path.absolute()

        if not spec_or_path.exists():
            raise FileNotFoundError(f"Spec file or path '{spec_or_path}' doesn’t exist")
        elif spec_or_path.is_dir():
            self.path = spec_or_path
            name = spec_or_path.name
            self.specfile = spec_or_path / f"{name}.spec"
        elif spec_or_path.is_file():
            if spec_or_path.suffix != ".spec":
                raise ValueError(f"Spec file '{spec_or_path}' must have '.spec' as an extension")
            self.path = spec_or_path.parent
            self.specfile = spec_or_path
        else:
            raise SpecialFileError(f"Spec file or path '{spec_or_path}' is not a regular file")

        if not self.specfile.exists():
            raise FileNotFoundError(f"Spec file '{self.specfile}' doesn’t exist in '{self.path}'")

        log.debug("Working on spec file %s", self.specfile)

        try:
            self.repo = pygit2.Repository(self.path, flags=pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH)
            log.debug("Found repository at %s", self.path)
        except pygit2.GitError:
            self.repo = None
            log.debug("Found no repository at %s", self.path)

        if self.repo is not None:
            spec_status = self.repo.status_file(self.specfile.relative_to(self.path))

            if spec_status == pygit2.GIT_STATUS_WT_NEW:
                raise FileUntrackedError(
                    f"Spec file '{self.specfile}' exists in the repository, but is untracked"
                )
            # Allow converting unmodified, and saved-to-index files.
            if spec_status not in (pygit2.GIT_STATUS_CURRENT, pygit2.GIT_STATUS_INDEX_MODIFIED):
                raise FileModifiedError(f"Spec file '{self.specfile}' is modified")
            try:
                self.repo.status_file("changelog")
            except KeyError:
                pass  # Doesn't exist; good.
            else:
                raise FileExistsError("Changelog file 'changelog' is already in the repository")
            for filepath, flags in self.repo.status().items():
                if flags not in (
                    pygit2.GIT_STATUS_CURRENT,
                    pygit2.GIT_STATUS_IGNORED,
                    pygit2.GIT_STATUS_WT_NEW,
                ):
                    raise FileModifiedError(f"Repository '{self.path}' is dirty")

        self.changelog_lines = None
        self.spec_lines = None

        # Collect information about conversions and operations that were performed
        self.converted_release = False
        self.converted_changelog = False
        self.made_commit = False

    def describe_changes(self, for_git: bool):
        changes: list[str] = [
            change
            for change, shall_include in (
                ("%autorelease", self.converted_release),
                ("%autochangelog", self.converted_changelog),
                ("committed to git", not for_git and self.made_commit),
            )
            if shall_include
        ]

        if for_git:
            return f"Convert to {' and '.join(changes)}"
        else:
            if len(changes) > 2:
                changes[-2] += ","
            return f"Converted to {' and '.join(changes)}."

    def load(self):
        with self.specfile.open(encoding="utf-8") as f:
            self.spec_lines = f.readlines()

    def save(self):
        with self.specfile.open("w", encoding="utf-8") as f:
            f.writelines(self.spec_lines)
        if self.changelog_lines is not None:
            with (self.path / "changelog").open("w", encoding="utf-8") as f:
                f.write("\n".join(self.changelog_lines) + "\n")

    def convert_to_autorelease(self):
        release_autorelease_lines = {
            i: (release_re.match(line), autorelease_re.search(line))
            for i, line in enumerate(self.spec_lines)
        }
        release_lines = [i for i, (rel_m, autorel_m) in release_autorelease_lines.items() if rel_m]
        autorelease_lines = [
            i for i, (rel_m, autorel_m) in release_autorelease_lines.items() if autorel_m
        ]

        if not release_lines:
            raise SpecParseFailure(f"Unable to locate Release tag in spec file '{self.specfile}'")

        if autorelease_lines:
            log.warning(f"'{self.specfile}' already uses %autorelease")
            return

        line_numbers = ", ".join(f"{i + 1}" for i in release_lines)
        log.debug("Found Release tag on line(s) %s", line_numbers)

        if len(release_lines) > 1:
            raise SpecParseFailure(
                f"Found multiple Release tags on lines {line_numbers} "
                + f"in spec file '{self.specfile}'"
            )

        # Process the line so the inserted macro is aligned to the previous location of the tag.
        lineno = release_lines[0]
        release_match = release_autorelease_lines[lineno][0]
        self.spec_lines[lineno] = f"{release_match.group('tag')}%autorelease\n"
        self.converted_release = True

    def convert_to_autochangelog(self):
        changelog_lines = [i for i, line in enumerate(self.spec_lines) if changelog_re.match(line)]
        line_numbers = ", ".join(f"{i + 1}" for i in changelog_lines)
        log.debug("Found %%changelog on line(s) %s", line_numbers)

        if not changelog_lines:
            raise SpecParseFailure(
                f"Unable to locate %changelog line in spec file '{self.specfile}'"
            )
        elif len(changelog_lines) > 1:
            raise SpecParseFailure(
                f"Found multiple %changelog on lines {line_numbers} "
                + f"in spec file '{self.specfile}'"
            )

        lineno = changelog_lines[0] + 1
        if autochangelog_re.match(self.spec_lines[lineno]):
            log.warning(f"'{self.specfile}' already uses %autochangelog")
            return
        self.changelog_lines = [line.rstrip() for line in self.spec_lines[lineno:]]
        while self.changelog_lines and not self.changelog_lines[-1]:
            self.changelog_lines.pop()

        self.spec_lines[lineno:] = ["%autochangelog\n"]
        log.debug("Split %d lines to 'changelog' file", len(self.changelog_lines))
        self.converted_changelog = True

    def commit(self, message: Optional[str] = None, signoff: bool = False):
        if self.repo is None:
            log.debug("Unable to open repository at '%s'", self.path)
            return

        if message is None:
            message = self.describe_changes(for_git=True) + "\n\n[skip changelog]"

        signature = self.repo.default_signature

        if signoff:
            message += f"\n\nSigned-off-by: {signature.name} <{signature.email}>"

        index = self.repo.index
        index.add(self.specfile.relative_to(self.path))
        if self.changelog_lines is not None:
            index.add("changelog")
        index.write()
        tree = index.write_tree()

        parent, ref = self.repo.resolve_refish(refish=self.repo.head.name)
        log.debug(
            "Committing tree %s with author '%s <%s>' on branch '%s'",
            tree,
            signature.name,
            signature.email,
            ref.shorthand,
        )
        if self.repo.diff(tree, parent, cached=True).patch:
            oid = self.repo.create_commit(
                ref.name, signature, signature, message, tree, [parent.id]
            )
            log.debug("Committed %s to repository", oid)
            self.made_commit = True
        else:
            log.warning("Nothing to commit")
