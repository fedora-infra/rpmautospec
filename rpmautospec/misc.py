import re
from collections import namedtuple
from functools import lru_cache
from pathlib import Path
from typing import Union


# the %autorelease macro including parameters
AUTORELEASE_MACRO = "autorelease(e:s:pb:)"

autorelease_re = re.compile(r"\s*(?i:Release)\s*:.*%(?:autorelease(?:\s|$)|\{\??autorelease\})")
changelog_re = re.compile(r"^%changelog(?:\s.*)?$", re.IGNORECASE)
autochangelog_re = re.compile(r"\s*%(?:autochangelog|\{\??autochangelog\})\s*")


SpecfileFeatures = namedtuple(
    "SpecfileFeatures",
    ("has_autorelease", "has_autochangelog", "changelog_lineno", "autochangelog_lineno"),
)


@lru_cache(maxsize=None)
def check_specfile_features(specpath: Union[Path, str]) -> SpecfileFeatures:
    if not isinstance(specpath, Path):
        specpath = Path(specpath)

    has_autorelease = False
    changelog_lineno = None
    autochangelog_lineno = None

    with specpath.open("r", encoding="utf-8", errors="replace") as specfile:
        for lineno, line in enumerate(iter(specfile), start=1):
            line = line.rstrip("\n")

            if not has_autorelease and autorelease_re.match(line):
                has_autorelease = True

            if changelog_lineno is None and changelog_re.match(line):
                changelog_lineno = lineno

            if autochangelog_lineno is None and autochangelog_re.match(line):
                autochangelog_lineno = lineno

    return SpecfileFeatures(
        has_autorelease=has_autorelease,
        has_autochangelog=bool(autochangelog_lineno),
        changelog_lineno=changelog_lineno,
        autochangelog_lineno=autochangelog_lineno,
    )


def specfile_uses_rpmautospec(
    specpath: Union[Path, str], check_autorelease: bool = True, check_autochangelog: bool = True
) -> bool:
    """Check whether or not an RPM spec file uses rpmautospec features."""
    if not check_autorelease and not check_autochangelog:
        raise ValueError("One of check_autorelease and check_autochangelog must be set")

    features = check_specfile_features(specpath)

    retval = False

    if check_autorelease:
        retval = retval or features.has_autorelease

    if check_autochangelog:
        retval = retval or features.has_autochangelog

    return retval
