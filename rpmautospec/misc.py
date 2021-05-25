import re
import subprocess
from pathlib import Path
from typing import Optional
from typing import Union

import koji


# The %autorelease macro including parameters. This is imported into the main package to be used
# from 3rd party code like fedpkg etc.
AUTORELEASE_MACRO = "autorelease(e:s:po:)"
AUTORELEASE_SENTINEL = "__AUTORELEASE_SENTINEL__"

autochangelog_re = re.compile(r"\s*%(?:autochangelog|\{\??autochangelog\})\s*")

_kojiclient = None


def get_rpm_current_version(
    path: str, name: Optional[str] = None, with_epoch: bool = False
) -> Optional[str]:
    """Retrieve the current version set in the spec file named ``name``.spec
    at the given path.

    Returns None if an error is encountered.
    """
    path = Path(path)

    if not name:
        name = path.name

    specfile = path / f"{name}.spec"

    if not specfile.exists():
        return None

    query = "%{version}"
    if with_epoch:
        query = "%|epoch?{%{epoch}:}:{}|" + query
    query += r"\n"

    rpm_cmd = [
        "rpm",
        "--define",
        "_invalid_encoding_terminates_build 0",
        "--define",
        f"{AUTORELEASE_MACRO} 1%{{?dist}}",
        "--define",
        "autochangelog %nil",
        "--qf",
        query,
        "--specfile",
        f"{name}.spec",
    ]

    try:
        output = (
            subprocess.check_output(rpm_cmd, cwd=path, stderr=subprocess.PIPE)
            .decode("UTF-8")
            .split("\n")[0]
            .strip()
        )
    except Exception:
        return None

    return output


def koji_init(koji_url_or_session: Union[str, koji.ClientSession]) -> koji.ClientSession:
    global _kojiclient
    if isinstance(koji_url_or_session, str):
        _kojiclient = koji.ClientSession(koji_url_or_session)
    else:
        _kojiclient = koji_url_or_session
    return _kojiclient


def specfile_uses_rpmautospec(
    specfile: str, check_autorelease: bool = True, check_autochangelog: bool = True
) -> bool:
    """Check whether or not an RPM spec file uses rpmautospec features."""

    autorelease = check_autorelease_presence(specfile)
    autochangelog = check_autochangelog_presence(specfile)

    if check_autorelease and check_autochangelog:
        return autorelease or autochangelog
    elif check_autorelease:
        return autorelease
    elif check_autochangelog:
        return autochangelog
    else:
        raise ValueError("One of check_autorelease and check_autochangelog must be set")


def check_autorelease_presence(filename: str) -> bool:
    """
    Use the rpm package to detect the presence of an
    autorelease macro and return true if found.
    """
    cmd = (
        "rpm",
        "--define",
        "{} {}".format(AUTORELEASE_MACRO, AUTORELEASE_SENTINEL),
        "-q",
        "--queryformat",
        "%{release}\n",
        "--specfile",
        filename,
    )
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    release = popen.communicate()[0].decode(errors="replace").split("\n")[0]
    return release == AUTORELEASE_SENTINEL


def check_autochangelog_presence(filename: str) -> bool:
    """
    Search for the autochangelog macro and return true if found.
    """
    with open(filename, "r") as specfile:
        for _, line in enumerate(iter(specfile), start=1):
            line = line.rstrip("\n")
            if autochangelog_re.match(line):
                return True
        return False
