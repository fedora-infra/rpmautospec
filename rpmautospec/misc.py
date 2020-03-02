from functools import cmp_to_key
import re
from typing import List, Optional, Tuple

import koji
import rpm


release_re = re.compile(r"^(?P<pkgrel>\d+)(?:(?P<middle>.*?)(?:\.(?P<minorbump>\d+))?)?$")
disttag_re = re.compile(r"^\.?(?P<distcode>[^\d\.]+)(?P<distver>\d+)")
evr_re = re.compile(r"^(?:(?P<epoch>\d+):)?(?P<version>[^-:]+)(?:-(?P<release>[^-:]+))?$")

rpmvercmp_key = cmp_to_key(
    lambda b1, b2: rpm.labelCompare(
        (str(b1["epoch"]), b1["version"], b1["release"]),
        (str(b2["epoch"]), b2["version"], b2["release"]),
    )
)

_kojiclient = None


def parse_evr(evr_str: str) -> Tuple[int, str, str]:
    match = evr_re.match(evr_str)

    if not match:
        raise ValueError(str)

    epoch = match.group("epoch") or 0
    epoch = int(epoch)

    return epoch, match.group("version"), match.group("release")


def parse_release_tag(tag: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    pkgrel = middle = minorbump = None
    match = release_re.match(tag)
    if match:
        pkgrel = int(match.group("pkgrel"))
        middle = match.group("middle")
        try:
            minorbump = int(match.group("minorbump"))
        except TypeError:
            pass
    return pkgrel, middle, minorbump


def koji_init(koji_url: str):
    global _kojiclient
    _kojiclient = koji.ClientSession(koji_url)
    return _kojiclient


def get_package_builds(pkgname: str, extras: bool = False) -> List[dict]:
    assert _kojiclient

    pkgid = _kojiclient.getPackageID(pkgname)
    if not pkgid:
        raise ValueError(f"Package {pkgname!r} not found!")

    return _kojiclient.listBuilds(pkgid, type="rpm", queryOpts={"order": "-nvr"})
