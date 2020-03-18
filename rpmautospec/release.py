#!/usr/bin/python3
from collections import defaultdict
from itertools import chain
import logging
import re
import sys
import typing

from .misc import (
    disttag_re,
    get_package_builds,
    koji_init,
    parse_evr,
    parse_release_tag,
    rpmvercmp_key,
)

_log = logging.getLogger(__name__)


def register_subcommand(subparsers):
    subcmd_name = "calculate-release"

    calc_release_parser = subparsers.add_parser(
        subcmd_name, help="Calculate the next release tag for a package build",
    )

    calc_release_parser.add_argument(
        "--algorithm",
        "--algo",
        help="The algorithm with which to calculate the next release",
        choices=["sequential_builds", "holistic_heuristic"],
        default="sequential_builds",
    )
    calc_release_parser.add_argument("package", help="The name of the package of interest")
    calc_release_parser.add_argument("dist", help="The dist-tag of interest")
    calc_release_parser.add_argument(
        "evr", help="The [epoch:]version[-release] of the package", nargs="?", type=parse_evr,
    )

    return subcmd_name


def main_sequential_builds_algo(args):
    n_builds = 1
    last_build = last_version = None
    for build in get_package_builds(args.package):
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
    print(f"Next build: {last_build['name']}-{last_build['version']}-{n_builds}.{args.dist}")


def holistic_heuristic_calculate_release(
    dist: str, evr: typing.Tuple[int, str, str],
    lower_bound: dict, higher_bound: typing.Optional[dict],
):

    # So what package EVR are we going for again? Default to "same as lower bound".
    try:
        epoch, version, release = evr
    except TypeError:
        epoch, version, release = (
            lower_bound["epoch"],
            lower_bound["version"],
            lower_bound["release"],
        )

    new_evr = {"epoch": epoch, "version": version, "release": release}
    if rpmvercmp_key(new_evr) > rpmvercmp_key(lower_bound):
        lower_bound = new_evr
        if not release:
            lower_bound["release"] = f"1.{dist}"

    lpkgrel, _, lminorbump = parse_release_tag(lower_bound["release"])

    # If the higher bound has the same version, bump its release to give it enough wiggle-room for
    # parallel builds of the (almost) same EVRs against several Fedora versions.
    if higher_bound and higher_bound["version"] == version:
        higher_bound = higher_bound.copy()
        hbpkgrel, hbmiddle, _ = parse_release_tag(higher_bound["release"])
        higher_bound["release"] = f"{hbpkgrel + 1}{hbmiddle}"

    # Bump the left-most release number and check that it doesn't violate the higher bound, if it
    # exists.
    new_evr["release"] = f"{lpkgrel + 1}.{dist}"

    if not higher_bound or rpmvercmp_key(new_evr) < rpmvercmp_key(higher_bound):
        # No (satisfiable) higher bound exists or it has a higher epoch-version-release.
        return new_evr

    if lminorbump:
        nminorbump = lminorbump + 1
    else:
        nminorbump = 1

    new_evr["release"] = rel_bak = f"{lpkgrel}.{dist}.{nminorbump}"

    if rpmvercmp_key(new_evr) < rpmvercmp_key(higher_bound):
        return new_evr

    # Oops. Attempt appending '.1' to the minor bump, ...
    new_evr["release"] += ".1"

    if rpmvercmp_key(new_evr) < rpmvercmp_key(higher_bound):
        return new_evr

    # ... otherwise don't bother.
    new_evr["release"] = rel_bak
    return new_evr


def holistic_heuristic_algo(package: str, dist: str, evr: typing.Tuple[int, str, str]):
    match = disttag_re.match(dist)
    if not match:
        print(
            f"Dist tag {dist!r} has wrong format (should be e.g. 'fc31', 'epel7')", file=sys.stderr,
        )
        sys.exit(1)

    distcode = match.group("distcode")
    pkgdistver = int(match.group("distver"))

    dtag_re = re.compile(fr"\.{distcode}(?P<distver>\d+)")

    builds = [build for build in get_package_builds(package) if dtag_re.search(build["release"])]

    # builds by distro release
    builds_per_distver = defaultdict(list)

    for build in builds:
        match = dtag_re.search(build["release"])

        if not match:
            # ignore builds for other distro types (e.g. Fedora vs. EPEL), or modular builds
            continue

        distver = int(match.group("distver"))
        builds_per_distver[distver].append(build)

    if not builds_per_distver:
        _log.warning(f"No matching builds found for dist tag pattern '{distcode}<number>'.")
        return

    for builds in builds_per_distver.values():
        builds.sort(key=rpmvercmp_key, reverse=True)

    # All builds that should be 'lower' than what we are targetting, sorted by 'highest first'.
    # We get by throwing all lower/current distro versions into one list because the new release
    # absolutely has to be higher than the highest in this list.
    lower_bound_builds = sorted(
        chain(*(builds for dver, builds in builds_per_distver.items() if dver <= pkgdistver)),
        key=rpmvercmp_key,
        reverse=True,
    )

    # TODO: Cope with epoch-version being higher in a previous Fedora release.

    # Lower bound: the RPM-wise "highest" build which this release has to exceed.
    lower_bound = lower_bound_builds[0]
    lower_bound_nvr = lower_bound["nvr"]

    # All builds that should be 'higher' than what we are targetting, i.e. the highest build of each
    # newer release. We aim at a new release which is lower than every one of them, but if this
    # can't be done, accommodate at least some.
    higher_bound_builds = sorted(
        (builds[0] for dver, builds in builds_per_distver.items() if dver > pkgdistver),
        key=rpmvercmp_key,
    )
    higher_bound_builds_nvr = [b["nvr"] for b in higher_bound_builds]

    print(f"Highest build of lower or current distro versions: {lower_bound_nvr}")
    print(f"Highest builds of higher distro versions: {', '.join(higher_bound_builds_nvr)}")

    lower_bound_rpmvercmp_key = rpmvercmp_key(lower_bound)

    # Disregard builds of higher distro versions that we can't go below. Sort so the first element
    # is the lowest build we can (and should) go "under".
    satisfiable_higher_bound_builds = sorted(
        (b for b in higher_bound_builds if lower_bound_rpmvercmp_key < rpmvercmp_key(b)),
        key=rpmvercmp_key,
    )

    if satisfiable_higher_bound_builds:
        # Find the higher bound which we can stay below.
        higher_bound = satisfiable_higher_bound_builds[0]
        higher_bound_nvr = higher_bound["nvr"]
    else:
        higher_bound = higher_bound_nvr = None

    print(f"Lowest satisfiable higher build in higher distro version: {higher_bound_nvr}")

    new_evr = holistic_heuristic_calculate_release(dist, evr, lower_bound, higher_bound)
    if new_evr["epoch"]:
        new_evr_str = f"{new_evr['epoch']}:{new_evr['version']}-{new_evr['release']}"
    else:
        new_evr_str = f"{new_evr['version']}-{new_evr['release']}"

    print(f"Calculated new release, EVR: {new_evr['release']}, {new_evr_str}")

    return new_evr["release"]


def main(args):
    """ Main method. """
    koji_init(args.koji_url)

    if args.algorithm == "sequential_builds":
        main_sequential_builds_algo(args)
    elif args.algorithm == "holistic_heuristic":
        holistic_heuristic_algo(args.package, args.dist, args.evr)
