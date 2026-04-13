import re
from pathlib import Path
from typing import get_type_hints

import pytest
import yaml

from rpmautospec.magic_comments import MagicCommentResult, parse_magic_comments

HERE = Path(__file__).parent
COMMITLOG_CHANGELOG_DIR = HERE.parent / "test-data" / "commitlogs"
COMMITLOGFILE_RE = re.compile(r"^commit-(?P<variant>.*)\.txt$")


def _read_commitlog_magic_comments_testdata():
    parametrized = []
    magic_types = get_type_hints(MagicCommentResult)

    for commitlog_path in sorted(COMMITLOG_CHANGELOG_DIR.glob("commit*.txt")):
        match = COMMITLOGFILE_RE.match(commitlog_path.name)
        variant = match.group("variant")
        chlog_items_path = commitlog_path.with_name(f"expected-{variant}.yaml")
        with open(chlog_items_path, "r") as chlog_items_fp:
            d = yaml.safe_load(chlog_items_fp)

        for k in d:
            if k not in magic_types:
                d.pop(k, None)

        parametrized.append(
            pytest.param(
                commitlog_path.read_text(),
                MagicCommentResult(**d),
                id=f"commit-{variant}",
            )
        )
    return parametrized


@pytest.mark.parametrize("commitlog, result", _read_commitlog_magic_comments_testdata())
def test_parse_magic_comments(commitlog, result):
    assert parse_magic_comments(commitlog) == result
