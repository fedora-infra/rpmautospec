import re
from typing import NamedTuple

magic_comment_re = re.compile(r"^\s*\[(?P<magic>.*)\]\s*$")
skip_changelog_re = re.compile(r"\s*skip\s+changelog\s*")


class MagicCommentResult(NamedTuple):
    skip_changelog: bool


def parse_magic_comments(message: str) -> MagicCommentResult:
    skip_changelog = False

    for line in message.split("\n"):
        if l_match := magic_comment_re.match(line):
            for part in l_match.group("magic").split(","):
                if skip_changelog_re.match(part):
                    skip_changelog = True

    return MagicCommentResult(skip_changelog=skip_changelog)
