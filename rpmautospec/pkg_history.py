import logging
from collections import defaultdict
from functools import lru_cache, reduce
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional, Sequence, Union

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

    @lru_cache(maxsize=None)
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

    def run(
        self,
        head: Optional[Union[str, pygit2.Commit]] = None,
        *,
        visitors: Sequence = (),
        all_results: bool = False,
    ) -> Union[Dict[str, Any], Dict[pygit2.Commit, Dict[str, Any]]]:
        if not head:
            head = self.repo[self.repo.head.target]

        # maps visited commits to their (in-flight) visitors and if they must
        # continue
        commit_coroutines = {}
        commit_coroutines_must_continue = {}

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
        # to be followed further.
        ##########################################################################################

        # While new branch heads are encountered...
        while branch_heads:
            commit = branch_heads.pop(0)
            branch = []
            branches.append(branch)

            while True:
                if commit in commit_coroutines:
                    break

                log.debug("%s: %s", commit.short_id, commit.message.split("\n")[0])

                if commit == head:
                    children_visitors_must_continue = [True for v in visitors]
                else:
                    this_children = commit_children[commit]
                    if not all(child in commit_coroutines for child in this_children):
                        # there's another branch that leads to this parent, put the remainder on the
                        # stack
                        branch_heads.append(commit)
                        if not branch:
                            # don't keep empty branches on the stack
                            branches.pop()
                        break

                    # For all visitor coroutines, determine if any of the children must continue.
                    children_visitors_must_continue = [
                        reduce(
                            lambda must_continue, child: (
                                must_continue or commit_coroutines_must_continue[child][vindex]
                            ),
                            this_children,
                            False,
                        )
                        for vindex, v in enumerate(visitors)
                    ]

                branch.append(commit)

                # Create visitor coroutines for the commit from the functions passed into this
                # method. Pass the ordered list of "is there a child whose coroutine of the same
                # visitor wants to continue" into it.
                commit_coroutines[commit] = coroutines = [
                    v(commit, children_visitors_must_continue[vi]) for vi, v in enumerate(visitors)
                ]

                # Consult all visitors for the commit on whether we should continue and store the
                # results.
                commit_coroutines_must_continue[commit] = coroutines_must_continue = [
                    next(c) for c in coroutines
                ]

                if not any(coroutines_must_continue) or not commit.parents:
                    break

                if len(commit.parents) > 1:
                    # merge commit, store new branch head(s) to follow later
                    branch_parents = commit.parents[1:]
                    new_branches = [p for p in branch_parents if p not in commit_coroutines]
                    branch_heads.extend(new_branches)

                # follow (first) parent
                commit = commit.parents[0]

        ###########################################################################################
        # Now, `branches` contains disjunct lists of commits in new -> old order. Process these in
        # reverse, one at a time until encountering a commit where we don't know the results of all
        # parents. Then put the remainder back on the stack to be further processed later until we
        # run out of branches with commits.
        ###########################################################################################

        visited_results = {}
        while branches:
            branch = branches.pop(0)
            while branch:
                # Take one commit from the tail end of the branch and process.
                commit = branch.pop()

                if not all(
                    p in visited_results or p not in commit_coroutines for p in commit.parents
                ):
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

        if all_results:
            return visited_results
        else:
            return visited_results[head]

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
