import datetime as dt
import logging
import re
import stat
import sys
import tempfile
from collections import defaultdict
from functools import reduce
from pathlib import Path, PurePath
from shutil import SpecialFileError
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Optional, Sequence, Union

from rpmautospec_core import AUTORELEASE_MACRO

from .changelog import ChangelogEntry
from .compat import BlobIO, pygit2, rpm
from .magic_comments import parse_magic_comments

log = logging.getLogger(__name__)


def _checkout_tree_files(
    commit: pygit2.Commit, tree: pygit2.Tree, topdir: Path, reldir: PurePath = PurePath(".")
) -> None:
    """Check out files, but don’t manipulate git status.

    :param commit:  The GIT commit being processed.
    :param tree:    The (sub)tree to check out files for.
    :param topdir:  The top directory for the contents to be checked out.
    :param reldir:  The relative directory being processed.
    """
    curdir = topdir / reldir
    curdir.mkdir(parents=True, exist_ok=True)
    for entry in tree:
        relpath = reldir / entry.name
        if isinstance(entry, pygit2.Tree):
            _checkout_tree_files(commit, entry, topdir, relpath)
        else:  # isinstance(entry, pygit2.Blob)
            fpath = curdir / entry.name
            if stat.S_ISLNK(entry.filemode):
                fpath.symlink_to(entry.data)
            else:  # stat.S_ISREG(entry.filemode)
                with BlobIO(entry, as_path=str(relpath), commit_id=commit.id) as f:
                    fpath.write_bytes(f.read())
                fpath.chmod(stat.S_IMODE(entry.filemode))


class PkgHistoryProcessor:
    autorelease_flags_re = re.compile(
        r"^E(?P<extraver>[^_]*)_S(?P<snapinfo>[^_]*)_P(?P<prerelease>[01])_B(?P<base>\d*)$"
    )

    def __init__(self, spec_or_path: Union[str, Path]):
        if isinstance(spec_or_path, str):
            spec_or_path = Path(spec_or_path)

        spec_or_path = spec_or_path.absolute()

        if not spec_or_path.exists():
            raise FileNotFoundError(f"Spec file or path '{spec_or_path}' doesn't exist.")
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
            raise SpecialFileError("File specified as `spec_or_path` is not a regular file.")

        if not self.specfile.exists():
            raise FileNotFoundError(f"Spec file '{self.specfile}' doesn't exist in '{self.path}'.")

        try:
            self.repo = pygit2.Repository(self.path, flags=pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH)
        except pygit2.GitError:
            self.repo = None

        self._rpmverflags_for_commits = {}

    @staticmethod
    def _get_rpm_packager() -> str:
        fallback = "John Doe <packager@example.com>"
        try:
            return rpm.expandMacro(f"%{{?packager}}%{{!?packager:{fallback}}}")
        except Exception:
            return fallback

    @classmethod
    def _get_rpmverflags(
        cls, path: str, name: Optional[str] = None, log_error: bool = True
    ) -> dict[str, Union[str, int]]:
        """Retrieve the epoch/version and %autorelease flags set in spec file."""
        path = Path(path)

        if not name:
            name = path.name

        specfile = path / f"{name}.spec"

        if not specfile.exists():
            log.debug("spec file missing: %s", specfile)
            return {"error": "specfile-missing", "error-detail": "Spec file is missing."}

        query = "%|epoch?{%{epoch}:}:{}|%{version}\n%{release}\n"

        autorelease_definition = "E%{?-e*}_S%{?-s*}_P%{?-p:1}%{!?-p:0}_B%{?-b*}"

        python_version = str(sys.version_info[0]) + "." + str(sys.version_info[1])

        with (
            specfile.open(mode="rb") as unabridged,
            NamedTemporaryFile(
                mode="wb", prefix=f"rpmautospec-abridged-{name}-", suffix=".spec"
            ) as abridged,
        ):
            # Attempt to parse a shortened version of the spec file first, to speed up
            # processing in certain cases. This includes all lines before `%prep`, i.e. in most
            # cases everything which is needed to make RPM parsing succeed and contain the info
            # we want to extract.
            for line in unabridged:
                if line.strip() == b"%prep":
                    break
                abridged.write(line)
            abridged.flush()

            for spec_candidate in (abridged.name, str(specfile)):
                with tempfile.NamedTemporaryFile(mode="w", prefix="rpmautospec-rpmerr-") as rpmerr:
                    try:
                        # Note: These calls will alter the results of any subsequent macro expansion
                        # when the rpm Python module is used from
                        # within this very same Python instance.
                        # We call rpm.reloadConfig() immediately after parsing the spec,
                        # but it is likely not thread/multiprocess-safe.
                        # If another thread/process of this interpreter calls RPM Python bindings
                        # in the meantime, they might be surprised a bit,
                        # but there's not much we can do.
                        rpm.setLogFile(rpmerr)
                        rpm.addMacro("_invalid_encoding_terminates_build", "0")
                        # rpm.addMacro() doesn’t work for parametrized macros
                        rpm.expandMacro(f"%define {AUTORELEASE_MACRO} {autorelease_definition}")
                        rpm.addMacro("autochangelog", "%nil")
                        rpm.addMacro("__python", f"/usr/bin/python{python_version}")
                        rpm.addMacro(
                            "python_sitelib", f"/usr/lib/python{python_version}/site-packages"
                        )
                        rpm.addMacro("_sourcedir", f"{path}")
                        rpm.addMacro("_builddir", f"{path}")
                        spec = rpm.spec(spec_candidate)
                        output = spec.sourceHeader.format(query)
                    except Exception:
                        error = True
                        if spec_candidate == str(specfile):
                            with open(rpmerr.name, "r", errors="replace") as rpmerr_read:
                                rpmerr_out = rpmerr_read.read()
                    else:
                        error = False
                        rpmerr_out = None
                        break
                    finally:
                        rpm.setLogFile(sys.stderr)
                        rpm.reloadConfig()
            else:
                pass  # pragma: no cover
        if error:
            if log_error:
                log.debug("rpm query for %r failed: %s", query, rpmerr_out)
            return {"error": "specfile-parse-error", "error-detail": rpmerr_out}

        split_output = output.split("\n")
        epoch_version = split_output[0]
        info = split_output[1]

        match = cls.autorelease_flags_re.match(info)
        if match:
            extraver = match.group("extraver") or None
            snapinfo = match.group("snapinfo") or None
            prerelease = match.group("prerelease") == "1" or None
            base = match.group("base")
            if base:
                base = int(base)
            else:
                base = 1
        else:
            extraver = snapinfo = prerelease = base = None

        result = {
            "epoch-version": epoch_version,
            "extraver": extraver,
            "snapinfo": snapinfo,
            "prerelease": prerelease,
            "base": base,
        }

        return result

    def _get_rpmverflags_for_commit(self, commit: pygit2.Commit) -> dict[str, Union[str, int]]:
        if commit in self._rpmverflags_for_commits:
            return self._rpmverflags_for_commits[commit]

        with TemporaryDirectory(prefix="rpmautospec-") as workdir:
            workdir = Path(workdir)

            # Only unpack spec file at first.
            try:
                specblob = commit.tree[self.specfile.name]
            except KeyError:
                # no spec file
                error = {"error": "specfile-missing", "error-detail": "Spec file is missing."}
                self._rpmverflags_for_commits[commit] = error
                return error

            specpath = workdir / self.specfile.name
            specpath.write_bytes(specblob.data)

            rpmverflags = self._get_rpmverflags(workdir, self.name, log_error=False)

            if "error" in rpmverflags:
                # Provide all files for %include and %load directives.
                _checkout_tree_files(commit, commit.tree, workdir)
                rpmverflags = self._get_rpmverflags(workdir, self.name)

        self._rpmverflags_for_commits[commit] = rpmverflags
        return rpmverflags

    def release_number_visitor(self, commit: pygit2.Commit, child_info: dict[str, Any]):
        """Visit a commit to determine its release number.

        The coroutine returned first determines if the parent chain(s) must be
        followed, i.e. if one parent has the same package epoch-version,
        suspends execution and yields that to the caller (usually the walk()
        method), who later sends the partial results for this commit (to be
        modified) and full results of parents back (as dictionaries), resuming
        execution to process these and finally yield back the results for this
        commit.
        """
        commit_verflags = verflags = self._get_rpmverflags_for_commit(commit)

        if "error" not in verflags:
            epoch_version = verflags["epoch-version"]
            prerelease = verflags["prerelease"]
            base = verflags["base"]
            if base is None:
                base = 1
            tag_string = "".join(f".{t}" for t in (verflags["extraver"], verflags["snapinfo"]) if t)
        else:
            epoch_version = prerelease = None
            base = 1
            tag_string = ""

        if not epoch_version:
            child_must_continue = True
        else:
            epoch_versions_to_check = []
            for p in commit.parents:
                verflags = self._get_rpmverflags_for_commit(p)
                if "error" in verflags:
                    child_must_continue = True
                    break
                epoch_versions_to_check.append(verflags["epoch-version"])
            else:
                child_must_continue = (
                    epoch_version in epoch_versions_to_check or epoch_version is None
                )

        log.debug("\tepoch_version: %s", epoch_version)
        log.debug("\tchild must continue: %s", child_must_continue)

        # Suspend execution, yield whether caller should continue, and get back the (partial) result
        # for this commit and parent results as dictionaries on resume.
        commit_result, parent_results = yield {"child_must_continue": child_must_continue}

        commit_result["verflags"] = commit_verflags
        commit_result["epoch-version"] = epoch_version
        commit_result["magic-comment-result"] = parse_magic_comments(commit.message)

        log.debug("\tepoch_version: %s", epoch_version)
        log.debug(
            "\tparent rel numbers: %s",
            ", ".join(str(res["release-number"]) if res else "none" for res in parent_results),
        )

        # Find the maximum applicable parent release number and increment by one if the
        # epoch-version can be parsed from the spec file.
        parent_release_numbers = tuple(
            (
                res["release-number"]
                if res
                and (
                    # Paper over gaps in epoch-versions, these could be simple syntax errors in
                    # the spec file, or a retired, then unretired package.
                    epoch_version is None
                    or res["epoch-version"] is None
                    or epoch_version == res["epoch-version"]
                )
                else 0
            )
            for res in parent_results
        )
        release_number = max(parent_release_numbers, default=0)

        if self.specfile.name in commit.tree:
            release_number += 1

        release_number = max(release_number, commit_result["magic-comment-result"].bump_release)

        commit_result["release-number"] = release_number

        log.debug("\trelease_number: %s", release_number)

        prerel_str = "0." if prerelease else ""
        release_number_with_base = release_number + base - 1
        commit_result["release-complete"] = f"{prerel_str}{release_number_with_base}{tag_string}"

        yield commit_result

    def changelog_visitor(self, commit: pygit2.Commit, child_info: dict[str, Any]):
        """Visit a commit to generate changelog entries for it and its parents.

        It first determines if parent chain(s) must be followed, i.e. if the
        changelog file was modified in this commit and yields that to the
        caller, who later sends the partial results for this commit (to be
        modified) and full results of parents back (as dictionaries), which
        get processed and the results for this commit yielded again.
        """
        child_must_continue = child_info["child_must_continue"]
        # Check if the spec file exists, if not, there will be no changelog.
        specfile_present = f"{self.name}.spec" in commit.tree

        # Find out if the changelog is different from every parent (or present, in the case of the
        # root commit).
        try:
            changelog_blob = commit.tree["changelog"]
        except KeyError:
            changelog_blob = None

        child_changelog_removed = child_info.get("changelog_removed")
        our_changelog_removed = False
        if commit.parents:
            changelog_changed = True
            for parent in commit.parents:
                try:
                    par_changelog_blob = parent.tree["changelog"]
                except KeyError:
                    par_changelog_blob = None
                else:
                    our_changelog_removed = our_changelog_removed or not changelog_blob
                if changelog_blob == par_changelog_blob:
                    changelog_changed = False
        else:
            # With root commits, changelog present means it was changed
            changelog_changed = bool(changelog_blob)

        # Establish which parent to follow (if any, and if we can).
        parent_to_follow = None
        merge_unresolvable = False
        if len(commit.parents) < 2:
            if commit.parents:
                parent_to_follow = commit.parents[0]
        else:
            for parent in commit.parents:
                if commit.tree == parent.tree:
                    # Merge done with strategy "ours" or equivalent, i.e. (at least) one parent has
                    # the same content. Follow this parent
                    parent_to_follow = parent
                    break
            else:
                # Didn't break out of loop => no parent with same tree found. If the changelog
                # is different from all parents, it was updated in the merge commit and we don't
                # care. If it didn't change, we don't know how to continue and need to flag that.
                merge_unresolvable = not changelog_changed

        our_child_must_continue = (
            not (changelog_changed and changelog_blob or merge_unresolvable) and child_must_continue
        )

        log.debug("\tchangelog changed: %s", changelog_changed)
        log.debug("\tchild changelog removed: %s", child_changelog_removed)
        log.debug("\tour changelog removed: %s", our_changelog_removed)
        log.debug("\tmerge unresolvable: %s", merge_unresolvable)
        log.debug("\tspec file present: %s", specfile_present)
        log.debug("\tchild must continue (incoming): %s", child_must_continue)
        log.debug("\tchild must continue (outgoing): %s", our_child_must_continue)

        commit_result, parent_results = yield {
            "child_must_continue": our_child_must_continue,
            "changelog_removed": not (changelog_blob and changelog_changed)
            and (child_changelog_removed or our_changelog_removed),
        }

        changelog_entry = ChangelogEntry(
            {
                "commit-id": commit.id,
                "authorblurb": f"{commit.author.name} <{commit.author.email}>",
                "timestamp": dt.datetime.fromtimestamp(commit.commit_time, dt.timezone.utc),
                "commitlog": commit.message,
                "epoch-version": commit_result["epoch-version"],
                "release-complete": commit_result["release-complete"],
            }
        )

        skip_for_changelog = (
            commit_result["magic-comment-result"].skip_changelog or not specfile_present
        )

        if merge_unresolvable:
            log.debug("\tunresolvable merge")
            changelog_entry["error"] = "unresolvable merge"
            previous_changelog = ()
            commit_result["changelog"] = (changelog_entry,)
        elif changelog_changed and changelog_blob:
            log.debug("\tchangelog file changed")
            if not child_changelog_removed:
                changelog_entry["data"] = changelog_blob.data.decode("utf-8", errors="replace")
                commit_result["changelog"] = (changelog_entry,)
            else:
                # The `changelog` file was removed in a later commit, stop changelog generation.
                log.debug("\t  skipping")
                commit_result["changelog"] = ()
        else:
            # Pull previous changelog entries from parent result (if any).
            if len(commit.parents) == 1:
                log.debug("\tone parent: %s", commit.parents[0].short_id)
                previous_changelog = parent_results[0].get("changelog", ())
            else:
                if parent_to_follow:
                    log.debug("\tmultiple parents, follow: %s", parent_to_follow.short_id)
                else:
                    log.debug("\tno parent to follow")
                previous_changelog = ()
                for candidate in parent_results:
                    if not candidate:
                        continue
                    if candidate["commit-id"] == parent_to_follow.id:
                        previous_changelog = candidate.get("changelog", ())
                        skip_for_changelog = True
                        break

            log.debug("\tskip_for_changelog: %s", skip_for_changelog)

            changelog_entry["skip"] = skip_for_changelog

            if not skip_for_changelog:
                commit_result["changelog"] = (changelog_entry,) + previous_changelog
            else:
                commit_result["changelog"] = previous_changelog

        yield commit_result

    @staticmethod
    def _merge_info(f1: dict[str, Any], f2: dict[str, Any]) -> dict[str, Any]:
        """Merge dicts containing info of previously run visitors."""
        mf = f1.copy()
        for k, v2 in f2.items():
            try:
                v1 = mf[k]
            except KeyError:
                mf[k] = v2
            else:
                if k == "child_must_continue":
                    mf[k] = v1 or v2
                elif k == "changelog_removed":
                    mf[k] = v1 and v2
                else:
                    raise KeyError(f"Unknown information key: {k}")
        return mf

    def _run_on_history(
        self,
        head: pygit2.Commit,
        *,
        visitors: Sequence = (),
        seed_info: Optional[dict[str, Any]] = None,
    ) -> dict[pygit2.Commit, dict[str, Any]]:
        """Process historical commits with visitors and gather results."""
        # This sets the “playing field” for the head commit, it subs for the partial result of a
        # child commit which doesn’t exist.
        seed_info = {"child_must_continue": True} | (seed_info or {})

        # These map visited commits to their (in-flight) visitor coroutines and tracks if they must
        # continue and other auxiliary information.
        commit_coroutines = {}
        commit_coroutines_info = {}

        # This keeps track of the heads of branches that need to be processed.
        branch_heads = [head]
        # This stores the discovered snippets, i.e. linear chains of commits.
        snippets = []

        # Unfortunately, pygit2 only tells us what the parents of a commit are, not what other
        # commits a commit is parent to (its children). Fortunately, Repository.walk() is quick.
        # This maps parent commits to their children.
        commit_children = defaultdict(list)
        for commit in self.repo.walk(head.id):
            for parent in commit.parents:
                commit_children[parent].append(commit)

        ##########################################################################################
        # To process, first walk the tree from the head commit downward, following all branches.
        # Check visitors whether they need parent results to do their work, i.e. the history needs
        # to be processed further, or just traversed.
        #
        # Here, the “top halves” of visitors get merged information from their child commit(s) as
        # well as from visitors that ran prior on the same commit. In practice: during runtime,
        # `changelog_visitor()` gets information from `release_number_visitor()` for the same
        # commit.
        ##########################################################################################

        log.debug("===========================================================")
        log.debug("Extracting linear history snippets from branched history...")
        log.debug("===========================================================")

        # While new branch heads are encountered...
        while branch_heads:
            commit = branch_heads.pop(0)
            snippet = []
            snippets.append(snippet)

            keep_processing = True

            while True:
                if commit in commit_coroutines:
                    # This commit was processed already, so `snippet` can be cut off before it.
                    log.debug("%s: coroutines exist, skipping", commit.short_id)
                    break

                if log.isEnabledFor(logging.DEBUG):
                    log.debug("commit %s: %s", commit.short_id, commit.message.split("\n", 1)[0])

                if commit == head:
                    # Set the stage for the first commit: Visitors expect to get some information
                    # from their child commit(s), as there aren’t any yet, fake it.
                    children_visitors_info = [seed_info for v in visitors]
                else:
                    this_children = commit_children[commit]
                    if not all(child in commit_coroutines for child in this_children):
                        # There's another branch that leads to this parent, put the remainder on the
                        # stack.
                        branch_heads.append(commit)

                        if not snippet:
                            # Don't keep empty snippets on the stack. Unsure if this can be reached.
                            snippets.pop()  # pragma: no cover

                        if log.isEnabledFor(logging.DEBUG):
                            log.debug(
                                "\tunencountered children, putting remainder of snippet aside"
                            )
                            log.debug(
                                "\tmissing children: %s",
                                [
                                    child.short_id
                                    for child in this_children
                                    if child not in commit_coroutines
                                ],
                            )

                        break  # pragma: has-py310

                    # For all visitor coroutines, merge their produced info, e.g. to determine if
                    # any of the children must continue.
                    children_visitors_info = [
                        reduce(
                            lambda info, child: self._merge_info(
                                info, commit_coroutines_info[child][vindex]
                            ),
                            this_children,
                            {},
                        )
                        for vindex, v in enumerate(visitors)
                    ]

                    log.debug(
                        "children_visitors_info[]['child_must_continue']: %s",
                        [info["child_must_continue"] for info in children_visitors_info],
                    )

                    keep_processing = keep_processing and any(  # pragma: no branch
                        info["child_must_continue"] for info in children_visitors_info
                    )

                snippet.append(commit)

                if keep_processing:
                    log.debug("Keep processing: commit %s", commit.id)
                    # Create visitor coroutines for the commit from the functions passed into this
                    # method. Pass the ordered list of "is there a child whose coroutine of the same
                    # visitor wants to continue" into it.
                    commit_coroutines[commit] = coroutines = [
                        v(commit, children_visitors_info[vi]) for vi, v in enumerate(visitors)
                    ]

                    # Consult all visitors for the commit on whether we should continue and store
                    # the results.
                    commit_coroutines_info[commit] = [next(c) for c in coroutines]
                else:
                    # Only traverse this commit. Traversal is important if parent commits are the
                    # root of branches that affect the results (computed release number and
                    # generated changelog).
                    log.debug("Only traversing: commit %s", commit.id)
                    commit_coroutines[commit] = coroutines = None
                    commit_coroutines_info[commit] = [
                        {"child_must_continue": False} for v in visitors
                    ]

                if not commit.parents:
                    log.debug("\tno parents, bailing out")
                    break

                if len(commit.parents) > 1:
                    # merge commit, store new branch head(s) to follow later
                    branch_parents = commit.parents[1:]
                    new_branches = [p for p in branch_parents if p not in commit_coroutines]
                    branch_heads.extend(new_branches)
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("\tnew branch heads %s", [x.short_id for x in new_branches])
                        log.debug("\tbranch heads: %s", [x.short_id for x in branch_heads])

                # follow (first) parent
                commit = commit.parents[0]
                log.debug("\tparent to follow: %s", commit.short_id)

        ###########################################################################################
        # Now, `snippets` contains disjunct lists of commits in new -> old order. Process these in
        # reverse, one at a time until encountering a commit where we don't know the results of all
        # parents. Then put the remainder back on the stack to be further processed later until we
        # run out of snippets with commits.
        #
        # Here, the “bottom halves” of visitors get results from their parent commit(s) as well as
        # visitors run prior on the same commit, i.e. `release_number_visitor()` ->
        # `changelog_visitor()`.
        ###########################################################################################

        log.debug("=====================================")
        log.debug("Processing linear history snippets...")
        log.debug("=====================================")

        # This maps commits to their results.
        visited_results = {}

        while snippets:
            snippet = snippets.pop(0)
            if snippet:
                log.debug("Processing snippet %s", snippet[0].short_id)
            while snippet:
                # Take one commit from the tail end of the snippet and process.
                commit = snippet.pop()

                if log.isEnabledFor(logging.DEBUG):
                    log.debug("commit %s: %s", commit.short_id, commit.message.split("\n", 1)[0])

                if commit_coroutines[commit] is None:
                    # Only traverse, but don't process this commit. Ancestral commits might have to
                    # be taken into account again, so we can’t simply stop here.
                    log.debug("\tonly traverse: %s", commit.id)
                    continue

                for p in commit.parents:
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug(
                            "\t%s: p in visited results: %s", p.short_id, p in visited_results
                        )
                        log.debug(
                            "\tcommit_coroutines[p] is None: %s", commit_coroutines[p] is None
                        )

                if not all(
                    p in visited_results or commit_coroutines[p] is None for p in commit.parents
                ):
                    # This commit doesn’t have all information it needs to be processed. Put it and
                    # the remainder of the snippet back to be processed later.
                    log.debug("\tputting back")
                    snippet.append(commit)
                    snippets.append(snippet)
                    break

                parent_results = [visited_results.get(p, {}) for p in commit.parents]

                # "Pipe" the (partial) result dictionaries through the second half of all visitors
                # for the commit.
                visited_results[commit] = reduce(
                    lambda commit_result, visitor: visitor.send((commit_result, parent_results)),
                    commit_coroutines[commit],
                    {"commit-id": commit.id},
                )

        return visited_results

    def run(
        self,
        head: Optional[Union[str, pygit2.Commit]] = None,
        *,
        visitors: Sequence = (),
        all_results: bool = False,
    ) -> Union[dict[str, Any], dict[pygit2.Commit, dict[str, Any]]]:
        """Process a package repository including a changed worktree."""
        # whether or not the worktree differs and this needs to be reflected in the result(s)
        reflect_worktree = False

        if self.repo:
            seed_info = None
            if not head:
                head = self.repo[self.repo.head.target]
                diff_to_head = self.repo.diff(head)
                reflect_worktree = diff_to_head.stats.files_changed > 0
                if (
                    reflect_worktree
                    and not (self.specfile.parent / "changelog").exists()
                    and "changelog" in head.tree
                ):
                    seed_info = {"changelog_removed": True}
            elif isinstance(head, str):
                head = self.repo[head]

            visited_results = self._run_on_history(head, visitors=visitors, seed_info=seed_info)
            head_result = visited_results[head]
        else:
            reflect_worktree = True
            visited_results = {}
            head_result = {}

        if reflect_worktree:
            # Not a git repository, or the git worktree isn't clean.
            worktree_result = {}

            verflags = self._get_rpmverflags(self.path, name=self.name)
            if "error" in verflags:
                # cringe, but what can you do?
                verflags |= {
                    "epoch-version": None,
                    "prerelease": False,
                    "extraver": None,
                    "snapinfo": None,
                    "base": 1,
                }

            # Mimic the bottom half of release_number_visitor
            worktree_result["verflags"] = verflags
            worktree_result["epoch-version"] = epoch_version = verflags["epoch-version"]
            if head_result and epoch_version == head_result["epoch-version"]:
                release_number = head_result["release-number"] + 1
            else:
                release_number = 1
            worktree_result["release-number"] = release_number

            prerel_str = "0." if verflags["prerelease"] else ""
            tag_string = "".join(f".{t}" for t in (verflags["extraver"], verflags["snapinfo"]) if t)
            base = verflags["base"]
            if base is None:
                base = 1
            release_number_with_base = release_number + base - 1
            worktree_result["release-complete"] = release_complete = (
                f"{prerel_str}{release_number_with_base}{tag_string}"
            )

            # Mimic the bottom half of the changelog visitor for a generic entry
            if not self.specfile.exists():
                changelog = ()
            else:
                previous_changelog = head_result.get("changelog", ())

                try:
                    signature = self.repo.default_signature
                    authorblurb = f"{signature.name} <{signature.email}>"
                except AttributeError:
                    # self.repo == None -> no git repo
                    authorblurb = self._get_rpm_packager()
                except KeyError:
                    authorblurb = "Unknown User <please-configure-git-user@example.com>"

                changelog_entry = ChangelogEntry(
                    {
                        "commit-id": None,
                        "authorblurb": authorblurb,
                        "timestamp": dt.datetime.now(dt.timezone.utc),
                        "commitlog": "Uncommitted changes",
                        "epoch-version": epoch_version,
                        "release-complete": release_complete,
                    }
                )

                changelog = (changelog_entry,) + previous_changelog

            worktree_result["changelog"] = changelog
            visited_results[None] = worktree_result

        if all_results:
            return visited_results
        elif reflect_worktree:
            return worktree_result
        else:
            return head_result
