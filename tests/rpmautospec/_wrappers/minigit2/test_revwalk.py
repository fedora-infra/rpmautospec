from typing import TYPE_CHECKING

import pytest

from rpmautospec._wrappers.minigit2.commit import Commit
from rpmautospec._wrappers.minigit2.revwalk import RevWalk

if TYPE_CHECKING:
    from rpmautospec._wrappers.minigit2.repository import Repository


@pytest.fixture
def revwalk(repo: "Repository") -> RevWalk:
    return repo.walk(repo.head.target)


class TestRevWalk:
    def test___init__(self, revwalk: RevWalk) -> None:
        new_revwalk = RevWalk(repo=revwalk._repo, native=revwalk._native)
        assert revwalk._repo is new_revwalk._repo
        assert revwalk._native is new_revwalk._native

    def test___iter__(self, revwalk: RevWalk) -> None:
        assert iter(revwalk) is revwalk

    def test___next__(self, revwalk: RevWalk) -> None:
        commits = list(revwalk)
        assert len(commits) == 1
        assert all(isinstance(c, Commit) for c in commits)
