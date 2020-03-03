#!/usr/bin/python3

import logging
import os
import subprocess

from .misc import get_package_builds, koji_init


_log = logging.getLogger(__name__)
escape_chars = {
    "^": "%5E",
    "%": "%25",
    "~": "%7E",
}


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

    repopath = args.worktree_path

    name = os.path.basename(repopath)
    for build in get_package_builds(name):
        if build.get("epoch"):
            nevr = f"{build['name']}-{build['epoch']}:{build['version']}-{build['release']}"
        else:
            nevr = f"{build['name']}-{build['version']}-{build['release']}"
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
            task = [t for t in tasks if t["method"] == "buildSRPMFromSCM"][0]
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
            # Escape un-allowed characters
            for char in escape_chars:
                nevr = nevr.replace(char, escape_chars[char])
            command = ["git", "tag", nevr, commit]
            try:
                run_command(command, cwd=repopath)
            except RuntimeError as err:
                print(err)
            else:
                print(f"tagged commit {commit} as {nevr}")
