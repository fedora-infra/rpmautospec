#!/usr/bin/python3

import argparse
import logging
import subprocess
import sys


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


def get_cli_arguments(self):
    """ Set the CLI argument parser and return the argument parsed.
    """
    parser = argparse.ArgumentParser(
        description="Script to determine the next NVR of a build"
    )
    parser.add_argument("package", help="The name of the package of interest")
    parser.add_argument("dist", help="The dist-tag of interest")

    return parser.parse_args()


def main(args):
    """ Main method. """
    args = get_cli_arguments(args)

    cmd = f"koji list-builds --package={args.package} --state=COMPLETE -r --quiet"
    rows = run_command(cmd.split()).decode("utf-8")
    builds = [
        row.strip().split()[0] for row in rows.split("\n") if row.strip()
    ]
    n_builds = 1
    last_build = None
    nv = None
    for build in builds:
        if args.dist in build:
            if n_builds == 1:
                last_build = build
                nv = last_build.rsplit("-", 1)[0]
            if build.startswith(nv):
                n_builds += 1

    if not last_build:
        print("No build found")
        return

    print(f"Last build: {last_build}")
    last_build = last_build.rsplit(f".{args.dist}", 1)[0]
    rel = last_build.rsplit("-", 1)[-1]
    try:
        rel = int(rel)
        n_builds = max([rel + 1, n_builds])
    except Exception:
        pass
    print(f"Next build: {nv}-{n_builds}.{args.dist}")


if __name__ == "__main__":
    main(sys.argv[1:])
