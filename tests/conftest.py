import pygit2
import pytest


SPEC_FILE_TEXT = """Summary: Boo
Name: boo
Version: 1.0
Release: %autorelease
License: CC0

%description
Boo

%changelog
%autochangelog
"""


@pytest.fixture
def repopath(tmp_path):
    repopath = tmp_path / "test"
    repopath.mkdir()

    yield repopath


@pytest.fixture
def specfile(repopath):
    specfile = repopath / "test.spec"
    specfile.write_text(SPEC_FILE_TEXT)

    yield specfile


@pytest.fixture
def repo(repopath, specfile):
    pygit2.init_repository(repopath, initial_head="rawhide")
    if hasattr(pygit2, "GIT_REPOSITORY_OPEN_NO_SEARCH"):
        repo = pygit2.Repository(repopath, pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH)
    else:
        # pygit2 < 1.4.0
        repo = pygit2.Repository(repopath)

    repo.config["user.name"] = "Jane Doe"
    repo.config["user.email"] = "jane.doe@example.com"

    # create root commit in "rawhide" branch
    index = repo.index
    index.add(specfile.name)
    index.write()

    tree = index.write_tree()

    oid = repo.create_commit(
        None, repo.default_signature, repo.default_signature, "Initial commit", tree, []
    )
    repo.branches.local.create("rawhide", repo[oid])

    # add another commit (empty)
    parent, ref = repo.resolve_refish(repo.head.name)
    repo.create_commit(
        ref.name,
        repo.default_signature,
        repo.default_signature,
        "Did nothing!",
        tree,
        [parent.oid],
    )

    yield repo
