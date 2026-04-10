import re
import typing

magic_comment_re = re.compile(r"^\s*\[(?P<magic>.*)\]\s*$")
intvalue_re = re.compile(r"\s*(?P<keyname>[a-z]+([\s_]+[a-z]+)*)\s*(?::\s*)?(?P<value>\d+)\s*")


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

    types = typing.get_type_hints(MagicCommentResult)
    values = dict()

    for line in message.split("\n"):
        if l_match := magic_comment_re.match(line):
            for part in l_match.group("magic").split(","):
                part = part.strip().replace(" ", "_")
                if part in types and types[part] is bool:
                    values[part] = True
                elif br_match := intvalue_re.match(part):
                    keyname = br_match.group("keyname")
                    if keyname in types and types[keyname] is int:
                        values[keyname] = int(br_match.group("value"))
                    else:
                        raise ValueError(
                            f"Parameter \"{keyname}\" is not recognized int type magic"
                        )

    return MagicCommentResult(**values)
