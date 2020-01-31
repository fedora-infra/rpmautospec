#!/usr/bin/python3

import argparse
import logging
import re
import sys

import koji


_log = logging.getLogger(__name__)


def get_cli_arguments(args):
    """ Set the CLI argument parser and return the argument parsed.
    """
    parser = argparse.ArgumentParser(
        description="Script to determine the next NVR of a build"
    )
    parser.add_argument(
        "--koji-url",
        help="The base URL of the Koji hub",
        default="https://koji.fedoraproject.org/kojihub",
    )
    parser.add_argument("package", help="The name of the package of interest")
    parser.add_argument("dist", help="The dist-tag of interest")

    return parser.parse_args(args)


_release_re = re.compile(r"(?P<pkgrel>\d+)(?:(?P<middle>.*\.)(?P<minorbump>\d+))?")


def parse_release_tag(tag):
    pkgrel = middle = minorbump = None
    match = _release_re.match(tag)
    if match:
        pkgrel = int(match.group("pkgrel"))
        middle = match.group("middle")
        try:
            minorbump = int(match.group("minorbump"))
        except TypeError:
            pass
    return pkgrel, middle, minorbump


def main(args):
    """ Main method. """
    args = get_cli_arguments(args)
    client = koji.ClientSession(args.koji_url)

    pkgid = client.getPackageID(args.package)
    if not pkgid:
        print(f"Package {args.package!r} not found!", file=sys.stderr)
        return 1

    n_builds = 1
    last_build = last_version = None
    for build in client.listBuilds(pkgid, type="rpm", queryOpts={"order": "-nvr"}):
        if args.dist in build["release"]:
            if n_builds == 1:
                last_build = build
                last_version = build["version"]
            if build["version"] == last_version:
                n_builds += 1

    if not last_build:
        print("No build found")
        return

    print(f"Last build: {last_build['nvr']}")
    pkgrel, middle, minorbump = parse_release_tag(last_build["release"])
    try:
        n_builds = max([pkgrel + 1, n_builds])
    except TypeError:
        pass
    print(
        f"Next build: {last_build['name']}-{last_build['version']}-{n_builds}.{args.dist}"
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
