import re
from typing import NamedTuple

magic_comment_re = re.compile(r"^\s*\[(?P<magic>.*)\]\s*$")
skip_changelog_re = re.compile(r"\s*skip\s+changelog\s*")
bump_release_re = re.compile(r"\s*bump\s+release\s*(?::\s*)?(?P<bump_value>\d+)\s*")


class MagicCommentResult(NamedTuple):
    skip_changelog: bool
    bump_release: int


def parse_magic_comments(message: str) -> MagicCommentResult:
    skip_changelog = False
    bump_release = 0

    for line in message.split("\n"):
        if l_match := magic_comment_re.match(line):
            for part in l_match.group("magic").split(","):
                if skip_changelog_re.match(part):
                    skip_changelog = True
                if br_match := bump_release_re.match(part):
                    bump_release = max(bump_release, int(br_match.group("bump_value")))

    return MagicCommentResult(skip_changelog=skip_changelog, bump_release=bump_release)
