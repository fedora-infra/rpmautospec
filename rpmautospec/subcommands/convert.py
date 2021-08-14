import logging
from pathlib import Path
import re

import pygit2

from ..misc import autochangelog_re, autorelease_re, changelog_re


log = logging.getLogger(__name__)


class PkgConverter:
    def __init__(self, spec_or_path: Path):
        spec_or_path = spec_or_path.absolute()

        if not spec_or_path.exists():
            raise RuntimeError(f"Spec file or path {str(spec_or_path)!r} doesn't exist")
        elif spec_or_path.is_dir():
            self.path = spec_or_path
            name = spec_or_path.name
            self.specfile = spec_or_path / f"{name}.spec"
        elif spec_or_path.is_file():
            if spec_or_path.suffix != ".spec":
                raise ValueError(
                    f"Spec file {str(spec_or_path)!r} must have '.spec' as an extension"
                )
            self.path = spec_or_path.parent
            self.specfile = spec_or_path
        else:
            raise RuntimeError(f"Spec file or path {str(spec_or_path)!r} is not a regular file")

        if not self.specfile.exists():
            raise RuntimeError(
                f"Spec file {str(self.specfile)!r} doesn't exist in {str(self.path)!r}"
            )

        log.debug("Working on spec file %s", self.specfile)

        try:
            if hasattr(pygit2, "GIT_REPOSITORY_OPEN_NO_SEARCH"):
                kwargs = {"flags": pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH}
            else:
                # pygit2 < 1.4.0
                kwargs = {}
            self.repo = pygit2.Repository(self.path, **kwargs)
            log.debug("Found repository at %s", self.path)
        except pygit2.GitError:
            self.repo = None
            log.debug("Found no repository at %s", self.path)

        if self.repo is not None:
            try:
                spec_status = self.repo.status_file(self.specfile.relative_to(self.path))
            except KeyError:
                raise RuntimeError(
                    f"Spec file {str(self.specfile)!r} is in a repository, but isn't tracked"
                )
            # Allow converting unmodified, and saved-to-index files.
            if spec_status not in (pygit2.GIT_STATUS_CURRENT, pygit2.GIT_STATUS_INDEX_MODIFIED):
                raise RuntimeError(f"Spec file {str(self.specfile)!r} is modified")
            try:
                self.repo.status_file("changelog")
            except KeyError:
                pass  # Doesn't exist; good.
            else:
                raise RuntimeError("Changelog file 'changelog' is already in the repository")
            for filepath, flags in self.repo.status().items():
                if flags not in (
                    pygit2.GIT_STATUS_CURRENT,
                    pygit2.GIT_STATUS_IGNORED,
                    pygit2.GIT_STATUS_WT_NEW,
                ):
                    raise RuntimeError(f"Repository '{str(self.path)!r}' is dirty")

        self.changelog_lines = None
        self.spec_lines = None

    def load(self):
        with self.specfile.open(encoding="utf-8") as f:
            self.spec_lines = f.readlines()

    def save(self):
        with self.specfile.open("w", encoding="utf-8") as f:
            f.writelines(self.spec_lines)
        if self.changelog_lines is not None:
            with (self.path / "changelog").open("w", encoding="utf-8") as f:
                f.writelines(self.changelog_lines)

    def convert_to_autorelease(self):
        release_re = re.compile(r"^(?P<tag>Release\s*:\s*)", re.IGNORECASE)
        release_lines = ((i, release_re.match(line)) for i, line in enumerate(self.spec_lines))
        release_lines = [(i, match) for i, match in release_lines if match]
        line_numbers = ", ".join(f"{i+1}" for i, _ in release_lines)
        log.debug("Found Release tag on line(s) %s", line_numbers)

        if not release_lines:
            raise RuntimeError(f"Unable to locate Release tag in spec file {str(self.specfile)!r}")
        elif len(release_lines) > 1:
            raise RuntimeError(
                f"Found multiple Release tags on lines {line_numbers} "
                f"in spec file {str(self.specfile)!r}"
            )

        # Process the line so the inserted macro is aligned to the previous location of the tag.
        lineno, match = release_lines[0]
        if autorelease_re.match(self.spec_lines[lineno]):
            log.warning(f"{str(self.specfile)!r} is already using %autorelease")
            return
        self.spec_lines[lineno] = f"{match.group('tag')}%autorelease\n"

    def convert_to_autochangelog(self):
        changelog_lines = [i for i, line in enumerate(self.spec_lines) if changelog_re.match(line)]
        line_numbers = ", ".join(f"{i+1}" for i in changelog_lines)
        log.debug("Found %%changelog on line(s) %s", line_numbers)

        if not changelog_lines:
            raise RuntimeError(
                f"Unable to locate %changelog line in spec file {str(self.specfile)!r}"
            )
        elif len(changelog_lines) > 1:
            raise RuntimeError(
                f"Found multiple %changelog on lines {line_numbers} "
                f"in spec file {str(self.specfile)!r}"
            )

        lineno = changelog_lines[0] + 1
        if autochangelog_re.match(self.spec_lines[lineno]):
            log.warning(f"{str(self.specfile)!r} is already using %autochangelog")
            return
        self.changelog_lines = self.spec_lines[lineno:]
        self.spec_lines[lineno:] = ["%autochangelog\n"]
        log.debug("Split %d lines to 'changelog' file", len(self.changelog_lines))

    def commit(self, message: str):
        if self.repo is None:
            log.debug("Unable to open repository at '%s'", self.path)
            return

        index = self.repo.index
        index.add(self.specfile.relative_to(self.path))
        if self.changelog_lines is not None:
            index.add("changelog")
        index.write()
        tree = index.write_tree()

        parent, ref = self.repo.resolve_refish(refish=self.repo.head.name)
        signature = self.repo.default_signature
        log.debug(
            "Committing tree %s with author '%s <%s>' on branch '%s'",
            tree,
            signature.name,
            signature.email,
            ref.shorthand,
        )
        oid = self.repo.create_commit(ref.name, signature, signature, message, tree, [parent.oid])
        log.debug("Committed %s to repository", oid)


def register_subcommand(subparsers):
    subcmd_name = "convert"

    convert_parser = subparsers.add_parser(
        subcmd_name,
        help="Convert a package repository to use rpmautospec",
    )

    convert_parser.add_argument(
        "spec_or_path",
        default=".",
        nargs="?",
        help="Path to package worktree or spec file",
    )

    convert_parser.add_argument(
        "--message",
        "-m",
        default="Convert to rpmautospec",
        help="Message to use when committing changes",
    )

    convert_parser.add_argument(
        "--no-commit",
        "-n",
        action="store_true",
        help="Don't commit after making changes",
    )

    convert_parser.add_argument(
        "--no-changelog",
        action="store_true",
        help="Don't convert the %%changelog",
    )

    convert_parser.add_argument(
        "--no-release",
        action="store_true",
        help="Don't convert the Release field",
    )

    return subcmd_name


def main(args):
    """Main method."""
    if not args.no_commit:
        if not args.message:
            raise RuntimeError("Commit message cannot be empty")
    if args.no_changelog and args.no_release:
        raise RuntimeError("All changes are disabled")

    pkg = PkgConverter(Path(args.spec_or_path))
    pkg.load()
    if not args.no_changelog:
        pkg.convert_to_autochangelog()
    if not args.no_release:
        pkg.convert_to_autorelease()
    pkg.save()
    if not args.no_commit:
        pkg.commit(args.message)
