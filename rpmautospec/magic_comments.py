import logging
import re
import typing

log = logging.getLogger(__name__)

magic_comment_re = re.compile(r"^\s*\[(?P<magic>.*)\]\s*$")
intvalue_re = re.compile(r"(?P<keyname>[a-z]+(?:[\s_]+[a-z]+)*)\s*(?::\s*)?(?P<value>\d+)")


class MagicCommentResult(typing.NamedTuple):
    """Stores special commit parameters extracted from a commit message."""

    skip_changelog: bool = False
    """Do not include this commit in changelog."""

    start_rightmost: bool = False
    """Start increasing number on the right of release string, not left."""

    bump_release: int = 0
    """Bump release to specified number."""

    bump_rightmost: int = 0
    """Bump rightmost (minorbump) of the release to specified number."""


types = typing.get_type_hints(MagicCommentResult)


def _get_keyname(keyname: str) -> str:
    return keyname.strip().replace(" ", "_")


def parse_magic_comments(message: str) -> MagicCommentResult:
    """Parses commit message for special lines providing extra features.

    Reworked to extract keywords from MagicCommentResult directly.
    Should reduce code repetition and simplify documentation of supported keywords.

    It does so by replacing spaces with _ underscore, then searching in defined
    class properties. Do not define extra regex for everything.

    Supports parsing of bool presences of:

       [skip changelog]
       [start rightmost]

    Supports parsing of int values of:

       [bump release: 3]
       [bump rightmost: 4]
    """

    values = dict()

    for line in message.split("\n"):
        if l_match := magic_comment_re.match(line):
            for part in l_match.group("magic").split(","):
                if br_match := intvalue_re.match(part):
                    keyname = _get_keyname(br_match.group("keyname"))
                    t = types.get(keyname, None)
                    value = br_match.group("value")
                    if types.get(keyname, None) is int:
                        values[keyname] = int(value)
                    elif t is not None:
                        log.warning(f'Parameter "{keyname}" is known, but {t} is not int')
                    else:
                        log.warning(f'Parameter "{keyname}" is not int type magic comment')
                else:
                    keyname = _get_keyname(part)
                    t = types.get(keyname, None)
                    if t is bool:
                        values[keyname] = True
                    elif t is not None:
                        log.warning(f'Parameter "{keyname}" is known, but {t} is not bool')
                    else:
                        log.warning(f'Parameter "{keyname}" is not known magic comment')

    return MagicCommentResult(**values)
