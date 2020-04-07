#!/usr/bin/python3

import logging
import os

from .misc import get_package_builds, koji_init, run_command
from .py2compat.tagging import escape_tag, PagureTaggingProxy, tag_prefix


_log = logging.getLogger(__name__)


def register_subcommand(subparsers):
    subcmd_name = "tag-package"

    tag_project_parser = subparsers.add_parser(
        subcmd_name, help="Tag the git commits corresponding to a build in koji",
    )

    tag_project_parser.add_argument("worktree_path", help="Path to the dist-git worktree")
    tag_project_parser.add_argument(
        "--pagure-url",
        help="Pagure url for tagging the package in the repo. Requires pagure_token to work.",
        default="https://src.fedoraproject.org",
    )

    tag_project_parser.add_argument(
        "--pagure-token",
        help="Pagure token for tagging the package in the repo. Requires pagure_url to work.",
    )
    return subcmd_name


def tag_package(srcdir, session, pagure_proxy=None):
    koji_init(session)
    repopath = srcdir.rstrip(os.path.sep)

    name = os.path.basename(repopath)
    for build in get_package_builds(name):
        nevr = f"{build['name']}-{build.get('epoch') or 0}-{build['version']}-{build['release']}"

        owner_name = build["owner_name"]
        # Ignore modular builds, account for staging
        if owner_name.startswith("mbs/") and owner_name.endswith(".fedoraproject.org"):
            _log.debug("Ignoring modular build: %s", nevr)
            continue

        commit = None
        # FIXME: We probably shouldn't hardcode "fedoraproject.org" here and below, rather use a
        # configurable full host name.
        if "source" in build and build["source"] and "fedoraproject.org" in build["source"]:
            com = build["source"].partition("#")[-1]
            # git commit hashes are 40 characters long, so we will
            # assume if the part after the '#' is 40 characters long it
            # is a commit hash and not a 40 characters long branch or
            # tag name
            if len(com) == 40:
                try:
                    int(com, 16)
                    commit = com
                except ValueError:
                    # The hash isn't a hexadecimal number, skip it
                    pass

        if commit is None:
            tasks = session.getTaskChildren(build["task_id"])
            try:
                task = [t for t in tasks if t["method"] == "buildSRPMFromSCM"][0]
            except IndexError:
                _log.debug(
                    "Ignoring build without buildSRPMFromSCM task, or any task at all, "
                    "probably an old dist-cvs build: %s (build id: %s)",
                    nevr,
                    build["build_id"],
                )
                continue

            task_req = session.getTaskRequest(task["id"])
            if "fedoraproject.org" in task_req[0]:
                com = task_req[0].partition("#")[-1]
                # git commit hashes are 40 characters long, so we will
                # assume if the part after the '#' is 40 characters long it
                # is a commit hash and not a 40 characters long branch or
                # tag name
                if len(com) == 40:
                    try:
                        int(com, 16)
                        commit = com
                    except ValueError:
                        # The hash isn't a hexadecimal number, skip it
                        pass

        if commit:
            tag = tag_prefix + escape_tag(nevr)
            command = ["git", "tag", "--force", tag, commit]
            try:
                run_command(command, cwd=repopath)
            except Exception:
                _log.exception("Error while tagging %s with %s:", commit, tag)
            else:
                _log.info("Tagged commit %s as %s", commit, tag)
                if pagure_proxy:
                    _log.info("Uploading tag to pagure")
                    pagure_proxy.create_tag(
                        repository="rpms/" + name, tagname=tag, commit_hash=commit
                    )


def main(args):
    """ Main method. """
    session = koji_init(args.koji_url)

    pagure_proxy = None
    if args.pagure_url and args.pagure_token:
        pagure_proxy = PagureTaggingProxy(base_url=args.pagure_url, auth_token=args.pagure_token)

    tag_package(args.worktree_path, session, pagure_proxy)
