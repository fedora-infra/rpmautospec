#!/usr/bin/python3
from collections import defaultdict
from itertools import chain
import logging
import re
import typing

from .misc import (
    disttag_re,
    get_rpm_current_version,
    koji_init,
    parse_epoch_version,
    parse_evr,
    parse_release_tag,
    rpmvercmp_key,
)


_log = logging.getLogger(__name__)


def register_subcommand(subparsers):
    subcmd_name = "calculate-release"

    calc_release_parser = subparsers.add_parser(
        subcmd_name,
        help="Calculate the next release tag for a package build",
    )

    calc_release_parser.add_argument(
        "--latest-evr",
        help="The [epoch:]version[-release] of the latest build",
        nargs="?",
        type=parse_evr,
    )

    calc_release_parser.add_argument(
        "--next-epoch-version",
        help="The [epoch:]version of the next build",
        nargs="?",
        type=parse_epoch_version,
    )

    calc_release_parser.add_argument(
        "srcdir", help="Clone of the dist-git repository to use for input"
    )
    calc_release_parser.add_argument("dist", help="The dist-tag of interest")

    return subcmd_name


def holistic_heuristic_calculate_release(
    dist: str,
    next_epoch_version: typing.Tuple[int, str],
    latest_evr: typing.Optional[typing.Tuple[int, str, typing.Optional[str]]],
    lower_bound: typing.Optional[dict],
    higher_bound: typing.Optional[dict],
):
    # epoch, version, release for the next build...
    epoch, version = next_epoch_version
    release = None  # == unknown

    if latest_evr and latest_evr[:2] == next_epoch_version:
        release = latest_evr["release"]
    else:
        # So later bumping produces "1"
        release = "0"

    next_evr = {"epoch": epoch, "version": version, "release": release}

    if not lower_bound or rpmvercmp_key(next_evr) > rpmvercmp_key(lower_bound):
        lower_bound = next_evr
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
    next_evr["release"] = f"{lpkgrel + 1}.{dist}"

    if not higher_bound or rpmvercmp_key(next_evr) < rpmvercmp_key(higher_bound):
        # No (satisfiable) higher bound exists or it has a higher epoch-version-release.
        return next_evr

    if lminorbump:
        nminorbump = lminorbump + 1
    else:
        nminorbump = 1

    next_evr["release"] = rel_bak = f"{lpkgrel}.{dist}.{nminorbump}"

    if rpmvercmp_key(next_evr) < rpmvercmp_key(higher_bound):
        return next_evr

    # Oops. Attempt appending '.1' to the minor bump, ...
    next_evr["release"] += ".1"

    if rpmvercmp_key(next_evr) < rpmvercmp_key(higher_bound):
        return next_evr

    # ... otherwise don't bother.
    next_evr["release"] = rel_bak
    return next_evr


def holistic_heuristic_algo(
    srcdir: str,
    dist: str,
    next_epoch_version: typing.Optional[typing.Tuple[int, str]] = None,
    latest_evr: typing.Optional[typing.Tuple[int, str, str]] = None,
    strip_dist: bool = False,
):
    match = disttag_re.fullmatch(dist)
    if not match:
        raise RuntimeError("Dist tag %r has wrong format (should be e.g. 'fc31', 'epel7')", dist)

    if not next_epoch_version:
        next_epoch_version = parse_epoch_version(get_rpm_current_version(srcdir, with_epoch=True))

    distcode = match.group("distcode")
    pkgdistver = int(match.group("distver"))

    dtag_re = re.compile(fr"\.{distcode}(?P<distver>\d+)")

    if not next_epoch_version:
        if latest_evr:
            next_epoch_version = latest_evr[:2]
        else:
            next_epoch_version = parse_epoch_version(
                get_rpm_current_version(srcdir, with_epoch=True)
            )

    # FIXME: the whole algo will be replaced
    tags = []
    builds = []
    if tags:
        for tmp_builds in tags.values():
            for build in tmp_builds:
                _log.debug("Found tagged build: %s", build)
                b_evr = "-".join(build.rsplit("-", 2)[1:])
                epoch, version, release = parse_evr(b_evr)
                builds.append(
                    {"nvr": build, "epoch": epoch, "version": version, "release": release}
                )

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
        _log.warning("No matching builds found for dist tag pattern '%s<number>'.", distcode)
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

    _log.debug("Lower bound builds: %s", [b["nvr"] for b in lower_bound_builds])

    # TODO: Cope with epoch-version being higher in a previous Fedora release.

    # Lower bound: the RPM-wise "highest" build which this release has to exceed.
    if lower_bound_builds:
        lower_bound = lower_bound_builds[0]
        lower_bound_nvr = lower_bound["nvr"]
        lower_bound_rpmvercmp_key = rpmvercmp_key(lower_bound)
        _log.info("Highest build of lower or current distro versions: %s", lower_bound_nvr)

    # All builds that should be 'higher' than what we are targetting, i.e. the highest build of each
    # newer release. We aim at a new release which is lower than every one of them, but if this
    # can't be done, accommodate at least some.
    higher_bound_builds = sorted(
        (builds[0] for dver, builds in builds_per_distver.items() if dver > pkgdistver),
        key=rpmvercmp_key,
    )
    higher_bound_builds_nvr = [b["nvr"] for b in higher_bound_builds]
    _log.info("Highest builds of higher distro versions: %s", ", ".join(higher_bound_builds_nvr))

    if lower_bound_builds:
        # Disregard builds of higher distro versions that we can't go below. Sort so the first
        # element is the lowest build we can (and should) go "under".
        satisfiable_higher_bound_builds = sorted(
            (b for b in higher_bound_builds if lower_bound_rpmvercmp_key < rpmvercmp_key(b)),
            key=rpmvercmp_key,
        )
    else:
        satisfiable_higher_bound_builds = None

    if satisfiable_higher_bound_builds:
        # Find the higher bound which we can stay below.
        higher_bound = satisfiable_higher_bound_builds[0]
        higher_bound_nvr = higher_bound["nvr"]
    else:
        higher_bound = higher_bound_nvr = None

    _log.info("Lowest satisfiable higher build in higher distro version: %s", higher_bound_nvr)

    next_evr = holistic_heuristic_calculate_release(
        dist,
        next_epoch_version,
        latest_evr=latest_evr,
        lower_bound=lower_bound,
        higher_bound=higher_bound,
    )
    if next_evr["epoch"]:
        next_evr_str = f"{next_evr['epoch']}:{next_evr['version']}-{next_evr['release']}"
    else:
        next_evr_str = f"{next_evr['version']}-{next_evr['release']}"

    _log.info("Calculated next release, EVR: %s, %s", next_evr["release"], next_evr_str)

    release = next_evr["release"]

    if strip_dist:
        release = release.replace(f".{dist}", "")

    return release


def main(args):
    """ Main method. """
    koji_init(args.koji_url)

    holistic_heuristic_algo(
        srcdir=args.srcdir,
        dist=args.dist,
        next_epoch_version=args.next_epoch_version,
        latest_evr=args.latest_evr,
    )
