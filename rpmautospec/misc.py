from functools import cmp_to_key
import logging
import os
import re
import subprocess
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import koji
import rpm


# The %autorelease macro including parameters. This is imported into the main package to be used from
# 3rd party code like fedpkg etc.
AUTORELEASE_MACRO = "autorelease(e:s:hp)"

release_re = re.compile(r"^(?P<pkgrel>\d+)(?:(?P<middle>.*?)(?:\.(?P<minorbump>\d+))?)?$")
disttag_re = re.compile(r"\.?(?P<distcode>[^\d\.]+)(?P<distver>\d+)")
evr_re = re.compile(r"^(?:(?P<epoch>\d+):)?(?P<version>[^-:]+)(?:-(?P<release>[^-:]+))?$")

rpmvercmp_key = cmp_to_key(
    lambda b1, b2: rpm.labelCompare(
        (str(b1["epoch"]), b1["version"], b1["release"]),
        (str(b2["epoch"]), b2["version"], b2["release"]),
    ),
)

_kojiclient = None

_log = logging.getLogger(__name__)


def parse_evr(evr_str: str) -> Tuple[int, str, Optional[str]]:
    match = evr_re.match(evr_str)

    if not match:
        raise ValueError(evr_str)

    epoch = match.group("epoch") or 0
    epoch = int(epoch)

    return epoch, match.group("version"), match.group("release")


def parse_epoch_version(epoch_version_str: str) -> Tuple[int, str]:
    e, v, r = parse_evr(epoch_version_str)
    if r is not None:
        raise ValueError(epoch_version_str)
    return e, v


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


def get_rpm_current_version(path: str, name: Optional[str] = None, with_epoch: bool = False) -> str:
    """Retrieve the current version set in the spec file named ``name``.spec
    at the given path.
    """
    if not name:
        path = path.rstrip(os.path.sep)
        name = os.path.basename(path)

    query = "%{version}"
    if with_epoch:
        query = "%|epoch?{%{epoch}:}:{}|" + query
    query += r"\n"

    rpm_cmd = [
        "rpm",
        "--define",
        f"{AUTORELEASE_MACRO} 1%{{?dist}}",
        "--define",
        "autochangelog %nil",
        "--qf",
        query,
        "--specfile",
        f"{name}.spec",
    ]

    output = None
    try:
        output = run_command(rpm_cmd, cwd=path).decode("UTF-8").split("\n")[0].strip()
    except Exception:
        pass
    return output


def koji_init(koji_url_or_session: Union[str, koji.ClientSession]) -> koji.ClientSession:
    global _kojiclient
    if isinstance(koji_url_or_session, str):
        _kojiclient = koji.ClientSession(koji_url_or_session)
    else:
        _kojiclient = koji_url_or_session
    return _kojiclient


def get_package_builds(pkgname: str) -> List[dict]:
    assert _kojiclient

    pkgid = _kojiclient.getPackageID(pkgname)
    if not pkgid:
        raise ValueError(f"Package {pkgname!r} not found!")

    # Don't add queryOpts={"order": "-nvr"} or similar, this sorts alphanumerically and and this is
    # not how EVRs should be sorted.
    return _kojiclient.listBuilds(pkgid, type="rpm")


def run_command(command: list, cwd: Optional[str] = None) -> bytes:
    """Run the specified command in a specific working directory if one
    is specified.
    """
    output = None
    try:
        output = subprocess.check_output(command, cwd=cwd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        _log.error("Command `%s` return code: `%s`", " ".join(command), e.returncode)
        _log.error("stdout:\n-------\n%s", e.stdout)
        _log.error("stderr:\n-------\n%s", e.stderr)
        raise

    return output
