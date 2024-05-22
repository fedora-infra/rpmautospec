import locale as locale_mod
from pathlib import Path

import pygit2
import pytest

SPEC_FILE_TEXT = """Summary: Boo
Name: boo
{version}
{release}
License: CC0

%description
Boo

{prep}

{changelog}
"""


def pytest_configure(config):
    config.addinivalue_line("markers", "repo_config")


@pytest.fixture(scope="session", autouse=True)
def git_empty_config():
    """Ensure tests run with empty git configuration."""
    for level in (
        pygit2.GIT_CONFIG_LEVEL_SYSTEM,
        pygit2.GIT_CONFIG_LEVEL_XDG,
        pygit2.GIT_CONFIG_LEVEL_GLOBAL,
        pygit2.GIT_CONFIG_LEVEL_LOCAL,
    ):
        try:
            pygit2.settings.search_path[level] = "/dev/null"
        except ValueError:
            pass


@pytest.fixture(autouse=True)
def locale():
    """Ensure consistent locale and that modifications stay isolated."""
    saved_locale_settings = {
        category: locale_mod.getlocale(getattr(locale_mod, category))
        for category in dir(locale_mod)
        if category.startswith("LC_") and category != "LC_ALL"
    }

    locale_mod.setlocale(locale_mod.LC_ALL, "C.UTF-8")

    yield locale_mod

    for category, locale_settings in saved_locale_settings.items():
        locale_mod.setlocale(getattr(locale_mod, category), locale_settings)


@pytest.fixture
def version(request) -> str:
    """
    This fixture exists to be substituted into the *specfile* fixture
    indirectly, or else provide a default of 1.0.
    """
    return getattr(request, "param", "Version: 1.0")


@pytest.fixture
def release(request) -> str:
    """
    This fixture exists to be substituted into the *specfile* fixture
    indirectly, or else provide a default of %autorelease.
    """
    return getattr(request, "param", "Release: %autorelease")


@pytest.fixture
def prep(request) -> str:
    """This fixture substitutes the %prep section into the *specfile*
    fixture indirectly, or provides a default."""
    return getattr(request, "param", "%prep")


@pytest.fixture
def changelog(request) -> str:
    """
    This fixture exists to be substituted into the *specfile* fixture
    indirectly, or else provide a default of %autochangelog.
    """
    return getattr(request, "param", "%changelog\n%autochangelog")


@pytest.fixture
def repopath(tmp_path) -> Path:
    repopath = tmp_path / "test"
    repopath.mkdir()

    yield repopath


@pytest.fixture
def specfile_content(version, release, prep, changelog) -> str:
    """Generate content for a spec file.

    The Version tag will be replaced by the *version* fixture, if defined, or
    else will be filled by 1.0.

    The Release tag will be replaced by the *release* fixture, if defined, or
    else will be filled by %autorelease.

    The %prep section will be replaced by the *prep* fixture if defined, or
    else will be filled by %prep.

    The changelog will be replaced by the *changelog* fixture, if defined, or
    else will be filled by %autochangelog.
    """
    return SPEC_FILE_TEXT.format(version=version, release=release, prep=prep, changelog=changelog)


@pytest.fixture
def specfile(repopath, specfile_content) -> Path:
    """Generate a spec file within *repopath*.

    The Version tag will be replaced by the *version* fixture, if defined, or
    else will be filled by 1.0.

    The Release tag will be replaced by the *release* fixture, if defined, or
    else will be filled by %autorelease.

    The %prep section will be replaced by the *prep* fixture if defined, or
    else will be filled by %prep.

    The changelog will be replaced by the *changelog* fixture, if defined, or
    else will be filled by %autochangelog.
    """

    specfile = repopath / "test.spec"
    specfile.write_text(specfile_content)

    yield specfile


@pytest.fixture
def _repo_config(request):
    config = {"converted": False}
    for node in request.node.listchain():
        for mark in node.own_markers:
            if mark.name == "repo_config":
                config |= mark.kwargs
    return config


@pytest.fixture
def repo(repopath, specfile, specfile_content, _repo_config):
    converted = _repo_config["converted"]

    pygit2.init_repository(repopath, initial_head="rawhide")
    repo = pygit2.Repository(repopath, pygit2.GIT_REPOSITORY_OPEN_NO_SEARCH)

    repo.config["user.name"] = "Jane Doe"
    repo.config["user.email"] = "jane.doe@example.com"
    author_blurb = f"{repo.config['user.name']} <{repo.config['user.email']}>"

    # create root commit in "rawhide" branch
    if converted:
        # … with manual release and changelog
        specfile.write_text(
            SPEC_FILE_TEXT.format(
                version="Version: 0.8",
                release="Release: 1%{?dist}",
                prep="%prep",
                changelog=f"%changelog\n* {author_blurb} 0.8-1\n- Initial commit",
            )
        )

        index = repo.index
        index.add(specfile.name)
        index.write()

        tree = index.write_tree()

        oid = repo.create_commit(
            None, repo.default_signature, repo.default_signature, "Initial commit", tree, []
        )
        repo.branches.local.create("rawhide", repo[oid])

        # add another commit, converting to %autorelease/%autochangelog
        changelog = specfile.parent / "changelog"
        changelog.write_text(f"* {author_blurb} 0.8-1\n- Initial commit\n")

        specfile.write_text(
            SPEC_FILE_TEXT.format(
                version="Version: 0.9",
                release="Release: %autorelease",
                prep="%prep",
                changelog="%changelog\n%autochangelog",
            )
        )
        index = repo.index
        index.add_all()
        index.add(changelog.name)
        index.write()

        tree = index.write_tree()

        parent, ref = repo.resolve_refish(repo.head.name)
        repo.create_commit(
            ref.name,
            repo.default_signature,
            repo.default_signature,
            "Update to 0.9\n\nConvert to rpmautospec.",
            tree,
            [parent.id],
        )
    else:
        # … starting out as %autorelease/%autochangelog
        index = repo.index
        index.add(specfile.name)
        index.write()

        tree = index.write_tree()

        oid = repo.create_commit(
            None, repo.default_signature, repo.default_signature, "Initial commit", tree, []
        )
        repo.branches.local.create("rawhide", repo[oid])

    # add a last commit, tweaking the spec file
    specfile.write_text(specfile_content + "\n")

    index = repo.index
    index.add_all()
    index.write()

    tree = index.write_tree()

    parent, ref = repo.resolve_refish(repo.head.name)
    repo.create_commit(
        ref.name,
        repo.default_signature,
        repo.default_signature,
        "Did something!",
        tree,
        [parent.id],
    )

    yield repo
