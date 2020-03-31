#!/usr/bin/python3
import datetime
import logging
import os
import re
import shutil
import tempfile
import textwrap
import typing

from .misc import run_command
from .py2compat.tagging import unescape_tag

_log = logging.getLogger(__name__)


def register_subcommand(subparsers):
    subcmd_name = "generate-changelog"

    gen_changelog_parser = subparsers.add_parser(
        subcmd_name, help="Generate changelog entries from git commit logs",
    )

    gen_changelog_parser.add_argument("worktree_path", help="Path to the dist-git worktree")

    return subcmd_name


def git_get_log(
    path: str,
    log_options: typing.Optional[typing.List[str]] = None,
    toref: typing.Optional[str] = None,
    target: typing.Optional[str] = None,
) -> typing.List[str]:
    """ Returns the list of the commit logs for the repo in ``path`` .

    This method runs the system's `git log --pretty=oneline --abbrev-commit`
    command.

    This command returns git log as follow:
    <short hash> <subject of the commit message>
    <short hash2> <subject of the commit message>
    <short hash3> <subject of the commit message>
    ...

    :kwarg log_options: options to pass to git log
    :kwarg toref: a reference/commit to use when generating the log
    :kwarg target: the target of the git log command, can be a ref, a
        file or nothing

    """
    cmd = ["git", "log", "--pretty=oneline", "--abbrev-commit", "--no-decorate"]
    if log_options:
        cmd.extend(log_options)
    if toref:
        cmd.append(f"{toref}..")
    if target:
        cmd.extend(["--", target])

    _log.debug(f"git_get_log {' '.join(cmd)}")
    return run_command(cmd, cwd=path).decode("UTF-8").strip().split("\n")


def git_get_commit_info(path: str, commithash: str) -> typing.List[str]:
    """This function calls `git show --no-patch --format="%P %ct"` on the
    specified commit and returns the output from git
    """
    cmd = ["git", "show", "--no-patch", "--format=%P|%H|%ct|%aN <%aE>|%s", commithash]
    _log.debug(f"git_get_commit_info {' '.join(cmd)}")
    return run_command(cmd, cwd=path).decode("UTF-8").strip().split("\n")


def git_get_changed_files(path: str, commithash: str) -> typing.List[str]:
    """ Returns the list of files changed in the specified commit. """
    cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commithash]
    _log.debug(f"git_get_changed_files {' '.join(cmd)}")
    return run_command(cmd, cwd=path).decode("UTF-8").strip().split("\n")


def git_get_tags(path: str) -> typing.Mapping[str, str]:
    """ Returns a dict containing for each commit tagged the corresponding tag. """
    cmd = ["git", "show-ref", "--tags", "--head"]
    _log.debug(f"git_get_tags {' '.join(cmd)}")
    tags_list = run_command(cmd, cwd=path).decode("UTF-8").strip().split("\n")

    output = {}
    for row in tags_list:
        commit, name = row.split(" ", 1)
        # we're only interested in the build/* tags
        if name.startswith("refs/tags/build/"):
            name = name.replace("refs/tags/build/", "")
            output[commit] = unescape_tag(name)

    return output


def nevrd_to_evr(nevrd: str) -> str:
    """ Converts a name:epoch-version-release.dist_tag to epoch_version_release
    so it can be inserted in the changelog.

    If the nevrd provided does not have at least 2 "-" in it, otherwise
    it will be just be cleaned for any potential dist_tag.
    """
    if nevrd.count("-") >= 2:
        version, release = nevrd.rsplit("-", 2)[1:]
        # Append a "-" to the version to make it easier to concatenate later
        version += "-"
    else:
        version = ""
        release = nevrd
    release = re.sub(r"\.fc\d+", "", release)
    release = re.sub(r"\.el\d+", "", release)
    return f"{version}{release}"


def get_rpm_current_version(path: str, name: str) -> str:
    """ Retrieve the current version set in the spec file named ``name``.spec
    at the given path.
    """
    output = None
    try:
        output = (
            run_command(["rpm", "--qf", "%{version}\n", "--specfile", f"{name}.spec"], cwd=path,)
            .decode("UTF-8")
            .strip()
        )
    except Exception:
        pass
    return output


def produce_changelog(repopath, latest_rel=None):
    name = os.path.basename(repopath)
    with tempfile.TemporaryDirectory(prefix="rpmautospec-") as workdir:
        repocopy = f"{workdir}/{name}"
        shutil.copytree(repopath, repocopy)
        _log.debug(f"Working directory: {repocopy}")
        lines = []

        # Get all the tags in the repo
        tags = git_get_tags(repocopy)

        # Get the lastest commit in the repo
        head = git_get_log(repocopy, log_options=["-1"])[0]
        head_hash = head.split(" ", 1)[0]
        head_info = git_get_commit_info(repocopy, head_hash)[0]
        head_commit_dt = datetime.datetime.utcfromtimestamp(int(head_info.split("|", 3)[2]))

        # Get the current version and build the version-release to be used
        # for the latest entry in the changelog, if we can build it
        current_evr = None
        current_version = get_rpm_current_version(repocopy, name)
        if current_version and latest_rel:
            latest_rel = nevrd_to_evr(latest_rel)
            current_evr = f"{current_version}-{latest_rel}"

        stop_commit_hash = None
        changelog = []
        changelog_file = os.path.join(repocopy, "changelog")
        if os.path.exists(changelog_file):
            stop_commit = git_get_log(repocopy, log_options=["-1"], target="changelog")
            if stop_commit:
                stop_commit_hash = stop_commit[0].split(" ", 1)[0]
            with open(changelog_file) as stream:
                changelog = [r.rstrip() for r in stream.readlines()]

        output = []
        entry = []
        nevr = current_evr or "LATEST"
        last_author = None
        for log_line in git_get_log(repocopy, toref=f"{stop_commit_hash}^"):
            if not log_line.strip():
                continue
            commit = log_line.split(" ", 1)[0]

            info = git_get_commit_info(repocopy, commit)
            if len(info) > 1:
                # Ignore merge commits
                _log.debug(f"commit {commit} is a merge commit, skipping")
                continue

            _, commithash, commit_ts, author_info, commit_summary = info[0].split("|", 4)

            if commithash in tags:
                output.append(entry)
                entry = []
                nevr = nevrd_to_evr(tags[commithash])

            commit_dt = datetime.datetime.utcfromtimestamp(int(commit_ts))
            if commit_dt < (head_commit_dt - datetime.timedelta(days=730)):
                # Ignore all commits older than 2 years
                # if there is a `changelog` file in addition to these commits
                # they will be cut down anyway when the RPM gets built, so
                # the gap between the commits we are gathering here and the
                # ones in the `changelog` file can be ignored.
                # print(f"commit {commit} is too old, breaking iteration")
                break

            files_changed = git_get_changed_files(repocopy, commit)
            ignore = True
            for filename in files_changed:
                if filename.endswith((".spec", ".patch")):
                    ignore = False

            if not ignore:
                if last_author == author_info:
                    entry[-1]["commits"].append(commit_summary)
                else:
                    entry.append(
                        {
                            "commit": commit,
                            "commit_ts": commit_ts,
                            "commit_author": author_info,
                            "commits": [commit_summary],
                            "nevr": nevr,
                        }
                    )
                last_author = author_info
            else:
                _log.debug(f"commit {commit} is not changing a file of interest, ignoring")

        # Last entries
        output.append(entry)

    wrapper = textwrap.TextWrapper(width=75, subsequent_indent="  ")
    for entries in output:
        for commit in entries:
            commit_dt = datetime.datetime.utcfromtimestamp(int(commit["commit_ts"]))
            author_info = commit["commit_author"]
            nevr = commit["nevr"]
            lines += [
                f"* {commit_dt.strftime('%a %b %d %Y')} {author_info} - {nevr}",
            ]
            for message in reversed(commit["commits"]):
                if message.strip():
                    lines += ["- %s" % wrapper.fill(message.strip())]
            lines += [""]

    # Add the existing changelog if there is one
    lines.extend(changelog)
    return lines


def main(args):
    """ Main method. """

    repopath = args.worktree_path
    changelog = produce_changelog(repopath)
    print("\n".join(changelog))
