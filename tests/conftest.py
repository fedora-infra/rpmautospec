import pygit2
import pytest

SPEC_FILE_TEXT = """Summary: Boo
Name: boo
Version: 1.0
{release}
License: CC0

%description
Boo

{changelog}
"""


@pytest.fixture
def changelog(request):
    """
    This fixture exists to be substituted into the *specfile* fixture
    indirectly, or else provide a default of %autochangelog.
    """
    return getattr(request, "param", "%changelog\n%autochangelog")


@pytest.fixture
def release(request):
    """
    This fixture exists to be substituted into the *specfile* fixture
    indirectly, or else provide a default of %autorelease.
    """
    return getattr(request, "param", "Release: %autorelease")


@pytest.fixture
def repopath(tmp_path):
    repopath = tmp_path / "test"
    repopath.mkdir()

    yield repopath


@pytest.fixture
def specfile(repopath, release, changelog):
    """
    Generate a spec file within *repopath*.

    The Release tag will be replaced by the *release* fixture, if defined, or
    else will be filled by %autorelease. The changelog will be replaced by the
    *changelog* fixture, if defined, or else will be filled by %autochangelog.
    """

    specfile = repopath / "test.spec"
    specfile.write_text(SPEC_FILE_TEXT.format(release=release, changelog=changelog))

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
