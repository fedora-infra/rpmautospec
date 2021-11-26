import datetime as dt
import logging
import re
import subprocess
import sys
from collections import defaultdict
from fnmatch import fnmatchcase
from functools import lru_cache, reduce
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import TextWrapper
from typing import Any, Dict, Optional, Sequence, Union

import pygit2
from babel.dates import format_datetime

from .misc import AUTORELEASE_MACRO


log = logging.getLogger(__name__)


class PkgHistoryProcessor:

    changelog_ignore_patterns = [
        ".gitignore",
        # no need to ignore "changelog" explicitly
        "gating.yaml",
        "sources",
        "tests/*",
    ]

    autorelease_flags_re = re.compile(
        r"^E(?P<extraver>[^_]*)_S(?P<snapinfo>[^_]*)_P(?P<prerelease>[01])_B(?P<base>\d*)$"
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

    @staticmethod
    def _get_rpm_packager() -> str:
        fallback = "John Doe <packager@example.com>"
        try:
            return (
                subprocess.check_output(
                    ("rpm", "--eval", f"%{{?packager}}%{{!?packager:{fallback}}}"),
                    stderr=subprocess.DEVNULL,
                )
                .decode("UTF-8")
                .strip()
            )
        except Exception:
            return fallback

    @classmethod
    def _get_rpmverflags(cls, path: str, name: Optional[str] = None) -> Optional[str]:
        """Retrieve the epoch/version and %autorelease flags set in spec file.

        Returns None if an error is encountered.
        """
        path = Path(path)

        if not name:
            name = path.name

        specfile = path / f"{name}.spec"

        if not specfile.exists():
            return None

        query = "%|epoch?{%{epoch}:}:{}|%{version}\n%{release}\n"

        autorelease_definition = (
            AUTORELEASE_MACRO + " E%{?-e*}_S%{?-s*}_P%{?-p:1}%{!?-p:0}_B%{?-b*}"
        )

        python_version = str(sys.version_info[0]) + "." + str(sys.version_info[1])

        rpm_cmd = [
            "rpm",
            "--define",
            "_invalid_encoding_terminates_build 0",
            "--define",
            autorelease_definition,
            "--define",
            "autochangelog %nil",
            "--define",
            f"__python /usr/bin/python{python_version}",
            "--define",
            f"python_sitelib /usr/lib/python{python_version}/site-packages",
            "--qf",
            query,
            "--specfile",
            f"{name}.spec",
        ]

        try:
            output = (
                subprocess.check_output(rpm_cmd, cwd=path, stderr=subprocess.PIPE)
                .decode("UTF-8")
                .strip()
            )
        except Exception:
            return None

        split_output = output.split("\n")
        epoch_version = split_output[0]
        info = split_output[1]

        match = cls.autorelease_flags_re.match(info)
        if match:
            extraver = match.group("extraver") or None
            snapinfo = match.group("snapinfo") or None
            prerelease = match.group("prerelease") == "1"
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

    @lru_cache(maxsize=None)
    def _get_rpmverflags_for_commit(self, commit):
        with TemporaryDirectory(prefix="rpmautospec-") as workdir:
            try:
                specblob = commit.tree[self.specfile.name]
            except KeyError:
                # no spec file
                return None

            specpath = Path(workdir) / self.specfile.name
            with specpath.open("wb") as specfile:
                specfile.write(specblob.data)

            return self._get_rpmverflags(workdir, self.name)

    def release_number_visitor(self, commit: pygit2.Commit, child_info: Dict[str, Any]):
        """Visit a commit to determine its release number.

        The coroutine returned first determines if the parent chain(s) must be
        followed, i.e. if one parent has the same package epoch-version,
        suspends execution and yields that to the caller (usually the walk()
        method), who later sends the partial results for this commit (to be
        modified) and full results of parents back (as dictionaries), resuming
        execution to process these and finally yield back the results for this
        commit.
        """
        verflags = self._get_rpmverflags_for_commit(commit)

        if verflags:
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
                if verflags:
                    epoch_versions_to_check.append(verflags["epoch-version"])
            child_must_continue = epoch_version in epoch_versions_to_check

        # Suspend execution, yield whether caller should continue, and get back the (partial) result
        # for this commit and parent results as dictionaries on resume.
        commit_result, parent_results = yield {"child_must_continue": child_must_continue}

        commit_result["epoch-version"] = epoch_version

        # Find the maximum applicable parent release number and increment by one.
        commit_result["release-number"] = release_number = (
            max(
                (
                    res["release-number"] if res and epoch_version == res["epoch-version"] else 0
                    for res in parent_results
                ),
                default=0,
            )
            + 1
        )

        prerel_str = "0." if prerelease else ""
        release_number_with_base = release_number + base - 1
        commit_result["release-complete"] = f"{prerel_str}{release_number_with_base}{tag_string}"

        yield commit_result

    @staticmethod
    def _files_changed_in_diff(diff: pygit2.Diff):
        files = set()
        for delta in diff.deltas:
            if delta.old_file:
                files.add(delta.old_file.path)
            if delta.new_file:
                files.add(delta.new_file.path)
        return files

    def changelog_visitor(self, commit: pygit2.Commit, child_info: Dict[str, Any]):
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

        if commit.parents:
            changelog_changed = True
            for parent in commit.parents:
                try:
                    par_changelog_blob = parent.tree["changelog"]
                except KeyError:
                    par_changelog_blob = None
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
            not (changelog_changed or merge_unresolvable)
            and specfile_present
            and child_must_continue
        )

        log.debug("\tchangelog changed: %s", changelog_changed)
        log.debug("\tmerge unresolvable: %s", merge_unresolvable)
        log.debug("\tspec file present: %s", specfile_present)
        log.debug("\tchild must continue (incoming): %s", child_must_continue)
        log.debug("\tchild must continue (outgoing): %s", our_child_must_continue)

        commit_result, parent_results = yield {"child_must_continue": our_child_must_continue}

        changelog_entry = {
            "commit-id": commit.id,
        }

        changelog_author = f"{commit.author.name} <{commit.author.email}>"
        changelog_date = format_datetime(
            dt.datetime.utcfromtimestamp(commit.commit_time),
            format="EEE MMM dd Y",
            locale="en",
        )

        changelog_evr = f"{commit_result['epoch-version']}-{commit_result['release-complete']}"

        changelog_header = f"* {changelog_date} {changelog_author} {changelog_evr}"

        skip_for_changelog = False

        if not specfile_present:
            # no spec file => start fresh
            log.debug("\tno spec file present")
            commit_result["changelog"] = ()
        elif merge_unresolvable:
            log.debug("\tunresolvable merge")
            changelog_entry["data"] = f"{changelog_header}\n- RPMAUTOSPEC: unresolvable merge"
            changelog_entry["error"] = "unresolvable merge"
            previous_changelog = ()
            commit_result["changelog"] = (changelog_entry,)
        elif changelog_changed:
            log.debug("\tchangelog file changed")
            if changelog_blob:
                changelog_entry["data"] = changelog_blob.data.decode("utf-8", errors="replace")
            else:
                # Changelog removed. Oops.
                log.debug("\tchangelog file removed")
                changelog_entry[
                    "data"
                ] = f"{changelog_header}\n- RPMAUTOSPEC: changelog file removed"
                changelog_entry["error"] = "changelog file removed"
            commit_result["changelog"] = (changelog_entry,)
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
                    if candidate["commit-id"] == parent_to_follow.id:
                        previous_changelog = candidate.get("changelog", ())
                        skip_for_changelog = True
                        break

            if not skip_for_changelog:
                # Check if this commit should be considered for the RPM changelog.
                if parent_to_follow:
                    diff = parent_to_follow.tree.diff_to_tree(commit.tree)
                else:
                    diff = commit.tree.diff_to_tree(swap=True)
                changed_files = self._files_changed_in_diff(diff)
                # Skip if no files changed (i.e. commit solely for changelog/build) or if any files
                # are not to be ignored.
                skip_for_changelog = changed_files and all(
                    any(fnmatchcase(f, pat) for pat in self.changelog_ignore_patterns)
                    for f in changed_files
                )

            if not skip_for_changelog:
                commit_subject = commit.message.split("\n", 1)[0].strip()
                if commit_subject.startswith("-"):
                    commit_subject = commit_subject[1:].lstrip()
                if not commit_subject:
                    commit_subject = "RPMAUTOSPEC: empty commit log subject after stripping"
                    changelog_entry["error"] = "empty commit log subject"
                wrapper = TextWrapper(width=75, subsequent_indent="  ")
                wrapped_msg = wrapper.fill(f"- {commit_subject}")
                changelog_entry["data"] = f"{changelog_header}\n{wrapped_msg}"
                commit_result["changelog"] = (changelog_entry,) + previous_changelog
            else:
                commit_result["changelog"] = previous_changelog

        yield commit_result

    @staticmethod
    def _merge_info(f1: Dict[str, Any], f2: Dict[str, Any]) -> Dict[str, Any]:
        mf = f1.copy()
        for k, v2 in f2.items():
            try:
                v1 = mf[k]
            except KeyError:
                mf[k] = v2
            else:
                if k == "child_must_continue":
                    mf[k] = v1 or v2
                else:
                    raise KeyError(f"Unknown information key: {k}")
        return mf

    def _run_on_history(
        self, head: pygit2.Commit, *, visitors: Sequence = ()
    ) -> Dict[pygit2.Commit, Dict[str, Any]]:
        """Process historical commits with visitors and gather results."""
        # maps visited commits to their (in-flight) visitors and if they must
        # continue
        commit_coroutines = {}
        commit_coroutines_info = {}

        # keep track of branches
        branch_heads = [head]
        branches = []

        ########################################################################################
        # Unfortunately, pygit2 only tells us what the parents of a commit are, not what other
        # commits a commit is parent to (its children). Fortunately, Repository.walk() is quick.
        ########################################################################################
        commit_children = defaultdict(list)
        for commit in self.repo.walk(head.id):
            for parent in commit.parents:
                commit_children[parent].append(commit)

        ##########################################################################################
        # To process, first walk the tree from the head commit downward, following all branches.
        # Check visitors whether they need parent results to do their work, i.e. the history needs
        # to be processed further, or just traversed.
        ##########################################################################################

        log.debug("===========================================================")
        log.debug("Extracting linear history snippets from branched history...")
        log.debug("===========================================================")

        # While new branch heads are encountered...
        while branch_heads:
            commit = branch_heads.pop(0)
            branch = []
            branches.append(branch)

            keep_processing = True

            while True:
                if commit in commit_coroutines:
                    log.debug("%s: coroutines exist, skipping", commit.short_id)
                    break

                if log.isEnabledFor(logging.DEBUG):
                    log.debug("commit %s: %s", commit.short_id, commit.message.split("\n", 1)[0])

                if commit == head:
                    children_visitors_info = [{"child_must_continue": True} for v in visitors]
                else:
                    this_children = commit_children[commit]
                    if not all(child in commit_coroutines for child in this_children):
                        # there's another branch that leads to this parent, put the remainder on the
                        # stack
                        branch_heads.append(commit)
                        if not branch:
                            # don't keep empty branches on the stack
                            branches.pop()
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
                        break

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

                    keep_processing = keep_processing and any(
                        info["child_must_continue"] for info in children_visitors_info
                    )

                branch.append(commit)

                if keep_processing:
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
                    # Only traverse this commit.
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
        # Now, `branches` contains disjunct lists of commits in new -> old order. Process these in
        # reverse, one at a time until encountering a commit where we don't know the results of all
        # parents. Then put the remainder back on the stack to be further processed later until we
        # run out of branches with commits.
        ###########################################################################################

        log.debug("=====================================")
        log.debug("Processing linear history snippets...")
        log.debug("=====================================")

        visited_results = {}

        while branches:
            branch = branches.pop(0)
            if branch:
                log.debug("Processing snippet %s", branch[0].short_id)
            while branch:
                # Take one commit from the tail end of the branch and process.
                commit = branch.pop()

                if log.isEnabledFor(logging.DEBUG):
                    log.debug("commit %s: %s", commit.short_id, commit.message.split("\n", 1)[0])

                if commit_coroutines[commit] is None:
                    # Only traverse, don't process commit.
                    log.debug("\tonly traverse")
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
                    log.debug("\tputting back")
                    # put the unprocessed commit back
                    branch.append(commit)
                    # put the unprocessed remainder back
                    branches.append(branch)

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
    ) -> Union[Dict[str, Any], Dict[pygit2.Commit, Dict[str, Any]]]:
        """Process a package repository including a changed worktree."""
        # whether or not the worktree differs and this needs to be reflected in the result(s)
        reflect_worktree = False

        if self.repo:
            if not head:
                head = self.repo[self.repo.head.target]
                diff_to_head = self.repo.diff(head)
                reflect_worktree = diff_to_head.stats.files_changed > 0
            elif isinstance(head, str):
                head = self.repo[head]

            visited_results = self._run_on_history(head, visitors=visitors)
            head_result = visited_results[head]
        else:
            reflect_worktree = True
            visited_results = {}
            head_result = {}

        if reflect_worktree:
            # Not a git repository, or the git worktree isn't clean.
            worktree_result = {}

            verflags = self._get_rpmverflags(self.path, name=self.name)
            if not verflags:
                # assume same as head commit, not ideal but hey
                verflags = self._get_rpmverflags_for_commit(self.repo[self.repo.head.target])
                if not verflags:
                    # cringe, head was unparseable, too
                    verflags = {
                        "epoch-version": None,
                        "prerelease": False,
                        "extraver": None,
                        "snapinfo": None,
                        "base": 1,
                    }

            # Mimic the bottom half of release_visitor
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
            worktree_result[
                "release-complete"
            ] = release_complete = f"{prerel_str}{release_number_with_base}{tag_string}"

            # Mimic the bottom half of the changelog visitor for a generic entry
            if not self.specfile.exists():
                changelog = ()
            else:
                previous_changelog = head_result.get("changelog", ())
                if self.repo:
                    changed_files = self._files_changed_in_diff(diff_to_head)
                    skip_for_changelog = all(
                        any(fnmatchcase(f, path) for path in self.changelog_ignore_patterns)
                        for f in changed_files
                    )
                else:
                    skip_for_changelog = False

                if not skip_for_changelog:
                    try:
                        signature = self.repo.default_signature
                        changelog_author = f"{signature.name} <{signature.email}>"
                    except AttributeError:
                        # self.repo == None -> no git repo
                        changelog_author = self._get_rpm_packager()
                    except KeyError:
                        changelog_author = "Unknown User <please-configure-git-user@example.com>"
                    changelog_date = format_datetime(
                        dt.datetime.utcnow(), format="EEE MMM dd Y", locale="en"
                    )
                    changelog_evr = f"{epoch_version}-{release_complete}"

                    changelog_header = f"* {changelog_date} {changelog_author} {changelog_evr}"
                    changelog_item = "- Uncommitted changes"

                    changelog_entry = {
                        "commit-id": None,
                        "data": f"{changelog_header}\n{changelog_item}",
                    }
                    changelog = (changelog_entry,) + previous_changelog
                else:
                    changelog = previous_changelog

            worktree_result["changelog"] = changelog
            visited_results[None] = worktree_result

        if all_results:
            return visited_results
        elif reflect_worktree:
            return worktree_result
        else:
            return head_result
