"""
Test the rpmautospec.subcommands.converter module
"""

import logging
import re
from types import SimpleNamespace
from unittest import mock

import pygit2
import pytest
from rpmautospec_core.main import autochangelog_re, autorelease_re

from rpmautospec.subcommands import convert

release_autorelease_re = re.compile(
    convert.release_re.pattern + autorelease_re.pattern, re.MULTILINE
)


def test_init_invalid_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="doesn't exist"):
        convert.PkgConverter(tmp_path / "nonexistent.spec")

    dir_no_spec = tmp_path / "dir_no_spec"
    dir_no_spec.mkdir()
    with pytest.raises(FileNotFoundError, match="doesn't exist in "):
        convert.PkgConverter(dir_no_spec)

    no_spec_extension = tmp_path / "noext"
    no_spec_extension.touch()
    with pytest.raises(ValueError, match="must have '.spec' as an extension"):
        convert.PkgConverter(no_spec_extension)


def test_init_dirty_tree(specfile, repo):
    # The changelog file has already been added:
    changelog = specfile.parent / "changelog"
    changelog.touch()
    with pytest.raises(FileExistsError, match="'changelog' is already in the repository"):
        convert.PkgConverter(specfile)
    changelog.unlink()

    # The spec file has been modified without committing it:
    specfile.write_text("Modified")
    with pytest.raises(convert.FileIsModifiedError, match="is modified"):
        convert.PkgConverter(specfile)
    repo.reset(repo.head.target, pygit2.GIT_RESET_HARD)

    # Other files have been changed, which may corrupt our commit:
    dirty = specfile.parent / "dirty"
    dirty.write_text("")
    repo.index.add("dirty")
    repo.index.write()
    with pytest.raises(convert.FileIsModifiedError, match="is dirty"):
        convert.PkgConverter(specfile)


@mock.patch("rpmautospec.subcommands.convert.PkgConverter")
def test_main_invalid_args(specfile):
    args = SimpleNamespace(
        spec_or_path=specfile, message="", no_commit=False, no_changelog=False, no_release=False
    )
    with pytest.raises(ValueError, match="Commit message cannot be empty"):
        convert.main(args)

    args = SimpleNamespace(
        spec_or_path=specfile,
        message="message",
        no_commit=False,
        no_changelog=True,
        no_release=True,
    )
    with pytest.raises(ValueError, match="All changes are disabled"):
        convert.main(args)


@mock.patch("rpmautospec.subcommands.convert.PkgConverter")
def test_main_valid_args(PkgConverter, specfile):
    PkgConverter.return_value = pkg_converter = mock.MagicMock()

    # No Release change.
    args = SimpleNamespace(
        spec_or_path=specfile,
        message="message",
        no_commit=False,
        no_changelog=False,
        no_release=True,
    )
    convert.main(args)
    pkg_converter.load.assert_called_once()
    pkg_converter.convert_to_autochangelog.assert_called_once()
    pkg_converter.convert_to_autorelease.assert_not_called()
    pkg_converter.save.assert_called()
    pkg_converter.commit.assert_called_once_with("message")

    # No %changelog change.
    pkg_converter.reset_mock()
    args = SimpleNamespace(
        spec_or_path=specfile,
        message="message",
        no_commit=False,
        no_changelog=True,
        no_release=False,
    )
    convert.main(args)
    pkg_converter.load.assert_called_once()
    pkg_converter.convert_to_autochangelog.assert_not_called()
    pkg_converter.convert_to_autorelease.assert_called_once()
    pkg_converter.save.assert_called_once()
    pkg_converter.commit.assert_called_once_with("message")

    # No git commit.
    pkg_converter.reset_mock()
    args = SimpleNamespace(
        spec_or_path=specfile,
        message="message",
        no_commit=True,
        no_changelog=False,
        no_release=False,
    )
    convert.main(args)
    pkg_converter.load.assert_called_once()
    pkg_converter.convert_to_autochangelog.assert_called_once()
    pkg_converter.convert_to_autorelease.assert_called_once()
    pkg_converter.save.assert_called_once()
    pkg_converter.commit.assert_not_called()


@pytest.mark.parametrize(
    "release, expected",
    [
        ("Release: 1%{dist}", "Release: %autorelease\n"),
        ("Release \t: \t1%{dist}", "Release \t: \t%autorelease\n"),
        ("ReLeAsE: 1%{dist}", "ReLeAsE: %autorelease\n"),
    ],
    ids=[
        "regular",
        "whitespace",
        "case",
    ],
    indirect=["release"],
)
def test_autorelease(specfile, expected):
    assert autorelease_re.search(specfile.read_text()) is None

    converter = convert.PkgConverter(specfile)
    converter.load()
    converter.convert_to_autorelease()
    converter.save()

    assert release_autorelease_re.search(specfile.read_text()).group() == expected


def test_autorelease_already_converted(specfile, caplog):
    assert autorelease_re.search(specfile.read_text()) is not None

    converter = convert.PkgConverter(specfile)
    converter.load()

    caplog.clear()
    converter.convert_to_autorelease()
    assert len(caplog.records) == 1
    assert "is already using %autorelease" in caplog.records[0].message


@pytest.mark.parametrize(
    "release, expected",
    [
        ("", "Unable to locate Release tag"),
        ("Release: 1%{dist}\nRelease: 2%{dist}", "Found multiple Release tags"),
    ],
    ids=[
        "missing",
        "multiple",
    ],
    indirect=["release"],
)
def test_autorelease_invalid(specfile, expected):
    converter = convert.PkgConverter(specfile)
    converter.load()
    with pytest.raises(RuntimeError, match=expected):
        converter.convert_to_autorelease()


@pytest.mark.parametrize(
    "changelog",
    [
        "%changelog\n- log line",
        "%ChAnGeLoG\n- log line      ",  # trailing whitespace here
        "%changelog\n- log line\n\n\n",  # trailing newlines here
    ],
    ids=[
        "regular",
        "case+whitespace",
        "regular+newlines",
    ],
    indirect=True,
)
def test_autochangelog(specfile):
    assert autochangelog_re.search(specfile.read_text()) is None

    converter = convert.PkgConverter(specfile)
    converter.load()
    converter.convert_to_autochangelog()
    converter.save()

    assert autochangelog_re.search(specfile.read_text()) is not None
    changelog = specfile.parent / "changelog"
    assert changelog.exists()
    assert changelog.read_text() == "- log line\n"


def test_autochangelog_already_converted(specfile, caplog):
    converter = convert.PkgConverter(specfile)
    converter.load()

    caplog.clear()
    converter.convert_to_autochangelog()
    assert len(caplog.records) == 1
    assert "is already using %autochangelog" in caplog.records[0].message


@pytest.mark.parametrize(
    "changelog, expected",
    [
        ("", "Unable to locate %changelog line"),
        ("%changelog\n%changelog", "Found multiple %changelog on lines"),
    ],
    ids=[
        "missing",
        "multiple",
    ],
    indirect=["changelog"],
)
def test_autochangelog_invalid(specfile, expected):
    assert autochangelog_re.search(specfile.read_text()) is None

    converter = convert.PkgConverter(specfile)
    converter.load()
    with pytest.raises(RuntimeError, match=expected):
        converter.convert_to_autochangelog()


def test_commit_no_repo(specfile, caplog):
    converter = convert.PkgConverter(specfile)
    with caplog.at_level(logging.DEBUG):
        converter.commit("Convert to rpmautospec.")
    assert len(caplog.records) == 1
    assert "Unable to open repository" in caplog.records[0].message


@pytest.mark.parametrize(
    "release",
    ["Release: 1%{dist}", "Release: %{autorelease}"],
    ids=["release1", "autorelease"],
    indirect=True,
)
@pytest.mark.parametrize(
    "changelog",
    ["%changelog\n- log line", "%changelog\n%autochangelog"],
    ids=["changelog", "autochangelog"],
    indirect=True,
)
def test_commit(specfile, release, changelog, repo):
    converter = convert.PkgConverter(specfile)
    converter.load()
    converter.convert_to_autochangelog()
    converter.convert_to_autorelease()
    converter.save()
    converter.commit("Convert to rpmautospec.")

    for filepath, flags in repo.status().items():
        assert flags == pygit2.GIT_STATUS_CURRENT

    changelog_should_change = autochangelog_re.search(changelog) is None
    release_should_change = autorelease_re.search(release) is None
    head = repo.revparse_single("HEAD")
    diff = repo.diff("HEAD^", head)
    fileschanged = {
        *(patch.delta.new_file.path for patch in diff),
        *(patch.delta.old_file.path for patch in diff),
    }

    if changelog_should_change or release_should_change:
        expected_message = "Convert to rpmautospec."
    else:
        expected_message = "Did nothing!"
    assert head.message == expected_message
    assert (specfile.name in fileschanged) == (changelog_should_change or release_should_change)
    assert ("changelog" in fileschanged) == changelog_should_change
