#!/usr/bin/python3

import logging
import os
import re
import subprocess
from urllib import parse

from .misc import get_package_builds, koji_init


_log = logging.getLogger(__name__)

# See https://git-scm.com/docs/git-check-ref-format
git_tag_seqs_to_escape = [
    "~",
    "/",
    re.compile(r"^\."),
    re.compile(r"(\.)lock$"),
    re.compile(r"\.\.+"),
    re.compile(r"\.$"),
    # This is a no-op, original "{" get quoted anyway.
    # re.compile(r"(@)\{"),
    re.compile(r"^@$"),
]

tag_prefix = "build/"


def escape_sequence(str_seq: str) -> str:
    """Compute a byte-escaped sequence for a string"""
    return "".join(f"%{byte:02X}" for byte in str_seq.encode("utf-8"))


def escape_regex_match(match: re.Match) -> str:
    """Escape whole or partial re.Match objects

    match: The match object covering the sequence that should be
        escaped (as a whole or partially). The regular expression may
        not contain nested groups.
    """
    # The whole match
    escaped = match.group()

    # Spans count from the start of the string, not the match.
    offset = match.start()

    if match.lastindex:
        # Work from the end in case string length changes.
        idx_range = range(match.lastindex, 0, -1)
    else:
        # If match.lastindex is None, then operate on the whole match.
        idx_range = (0,)

    for idx in idx_range:
        start, end = (x - offset for x in match.span(idx))
        escaped = escaped[:start] + escape_sequence(match.group(idx)) + escaped[end:]

    return escaped


def escape_tag(tagname: str) -> str:
    """Escape prohibited character sequences in git tag names

    tagname: An unescaped tag name.

    Returns: An escaped tag name which can be converted back using
        unescape_tag().
    """
    # Leave '+' as is, some version schemes may contain it.
    escaped = parse.quote(tagname, safe="+")

    # This will quote the string in a way that urllib.parse.unquote() can undo it, i.e. only replace
    # characters by the URL escape sequence of their UTF-8 encoded value.
    for seq in git_tag_seqs_to_escape:
        if isinstance(seq, str):
            escaped = escaped.replace(seq, escape_sequence(seq))
        elif isinstance(seq, re.Pattern):
            escaped = seq.sub(escape_regex_match, escaped)
        else:
            raise TypeError("Don't know how to deal with escape sequence: {seq!r}")

    return escaped


def unescape_tag(escaped_tagname: str) -> str:
    """Unescape prohibited characters sequences in git tag names

    This essentially just exists for symmetry with escape_tag() and just
    wraps urllib.parse.unquote().

    escaped_tagname: A tag name that was escaped with escape_tag().

    Returns: An unescaped tag name.
    """
    return parse.unquote(escaped_tagname)


def register_subcommand(subparsers):
    subcmd_name = "tag-package"

    tag_project_parser = subparsers.add_parser(
        subcmd_name, help="Tag the git commits corresponding to a build in koji",
    )

    tag_project_parser.add_argument("worktree_path", help="Path to the dist-git worktree")

    return subcmd_name


def run_command(command, cwd=None):
    """ Run the specified command in a specific working directory if one
    is specified.
    """
    output = None
    try:
        output = subprocess.check_output(command, cwd=cwd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        command_str = " ".join(command)
        _log.error("Command `{}` return code: `{}`".format(command_str, e.returncode))
        _log.error("stdout:\n-------\n{}".format(e.stdout))
        _log.error("stderr:\n-------\n{}".format(e.stderr))
        raise RuntimeError(
            "Command `{}` failed to run, returned {}".format(command_str, e.returncode)
        )

    return output


def main(args):
    """ Main method. """
    kojiclient = koji_init(args.koji_url)

    repopath = args.worktree_path.rstrip(os.path.sep)

    name = os.path.basename(repopath)
    for build in get_package_builds(name):
        nevr = f"{build['name']}-{build.get('epoch') or 0}-{build['version']}-{build['release']}"
        commit = None
        if "source" in build and build["source"]:
            com = build["source"].partition("#")[-1]
            try:
                int(com, 16)
                commit = com
            except ValueError:
                # The hash isn't an hexadecimal number so, skipping it
                pass

        if commit is None:
            tasks = kojiclient.getTaskChildren(build["task_id"])
            try:
                task = [t for t in tasks if t["method"] == "buildSRPMFromSCM"][0]
            except IndexError:
                _log.info(
                    "Ignoring build without buildSRPMFromSCM task, or any task at all, "
                    f"probably an old dist-cvs build: {nevr} (build id: {build['build_id']})"
                )
                continue

            task_req = kojiclient.getTaskRequest(task["id"])
            if "fedoraproject.org" in task_req[0]:
                com = task_req[0].partition("#")[-1]
                # git commit hashes are 40 characters long, so we will
                # assume if the part after the '#' in 40 characters long it
                # is a commit hash and not a 40 characters long branch or
                # tag name
                if len(com) == 40:
                    try:
                        int(com, 16)
                        commit = com
                    except ValueError:
                        # The hash isn't an hexadecimal number so, skipping it
                        pass

        if commit:
            tag = tag_prefix + escape_tag(nevr)
            command = ["git", "tag", tag, commit]
            try:
                run_command(command, cwd=repopath)
            except RuntimeError as err:
                print(err)
            else:
                print(f"tagged commit {commit} as {tag}")
