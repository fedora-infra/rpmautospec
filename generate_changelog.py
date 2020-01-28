#!/usr/bin/python3

import collections
import datetime
import logging
import os
import subprocess
import sys
import textwrap

import pygit2

_log = logging.getLogger(__name__)


def run_command(command, cwd=None):
    """ Run the specified command in a specific working directory if one
    is specified.
    """
    output = None
    try:
        output = subprocess.check_output(
            command, cwd=cwd, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        _log.error(
            "Command `{}` return code: `{}`".format(
                " ".join(command), e.returncode
            )
        )
        _log.error("stdout:\n-------\n{}".format(e.stdout))
        _log.error("stderr:\n-------\n{}".format(e.stderr))
        raise Exception("Command failed to run")

    return output


def main(args):
    """ Main method. """
    repo_obj = pygit2.Repository(args[0])
    name = os.path.basename(args[0])

    branch = repo_obj.lookup_branch(repo_obj.head.shorthand)
    commit = branch.peel(pygit2.Commit)
    nvr = None
    new_nvr = None
    changed = False
    data = collections.defaultdict(list)
    for commit in repo_obj.walk(commit.hex, pygit2.GIT_SORT_TIME):
        if len(commit.parents) > 1:
            # Ignore merge commits
            continue

        commit_dt = datetime.datetime.utcfromtimestamp(commit.commit_time)
        if commit_dt < (datetime.datetime.utcnow() - datetime.timedelta(days=730)):
            # Ignore all commits older than 2 years
            break

        repo_obj.checkout_tree(
            commit,
            strategy=pygit2.GIT_CHECKOUT_FORCE | pygit2.GIT_CHECKOUT_RECREATE_MISSING)
        if os.path.exists(os.path.join(args[0], f"{name}.spec")):
            try:
                output = run_command([
                    "rpm", "--qf", '%{name}  %{version}  %{release}\n',
                    "--specfile", f"{name}.spec",
                ], cwd=args[0])
            except Exception:
                continue
            output = tuple(
                output.decode('utf-8').strip().split('\n')[0].rsplit('.', 1)[0].split('  ')
            )
            nvr = '-'.join(output)

            if commit.parents:
                diff = repo_obj.diff(commit.parents[0], commit)
            else:
                # First commit in the repo
                diff = commit.tree.diff_to_tree(swap=True)

            if diff.stats.files_changed:
                files_changed = [d.new_file.path for d in diff.deltas]
                ignore = True
                for filename in files_changed:
                    if filename.endswith(('.spec', '.patch')):
                        ignore = False
                if not ignore:
                    data[output].append(commit)
        else:
            print("No more spec file, bailing")
            break

    for nvr in data:
        commits = data[nvr].reverse()
        for idx, commit in enumerate(data[nvr]):
            last_commit = idx + 1 == len(data[nvr])
            commit_dt = datetime.datetime.utcfromtimestamp(commit.commit_time)
            wrapper = textwrap.TextWrapper(width=75, subsequent_indent="  ")
            message = wrapper.fill(commit.message.split('\n')[0].strip('- '))

            if last_commit:
                print(f"* {commit_dt.strftime('%a %b %d %Y')} {commit.author.name} <{commit.author.email}> - {nvr[1]}-{nvr[2]}")
            else:
                print(f"* {commit_dt.strftime('%a %b %d %Y')} {commit.author.name} <{commit.author.email}>")
            print("- %s" % message)
            print()



if __name__ == '__main__':
    main(sys.argv[1:])
