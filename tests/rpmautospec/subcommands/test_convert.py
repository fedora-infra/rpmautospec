"""
Test the rpmautospec.subcommands.converter module
"""

import logging
import re
from pathlib import Path
from shutil import SpecialFileError
from unittest import mock

import pytest
from rpmautospec_core.main import autochangelog_re, autorelease_re

from rpmautospec.compat import pygit2
from rpmautospec.exc import SpecParseFailure
from rpmautospec.subcommands import convert

release_autorelease_re = re.compile(
    convert.release_re.pattern + autorelease_re.pattern, re.MULTILINE
)


class TestPkgConverter:
    def test_init_invalid_path(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="doesn’t exist"):
            convert.PkgConverter(tmp_path / "nonexistent.spec")

        dir_no_spec = tmp_path / "dir_no_spec"
        dir_no_spec.mkdir()
        with pytest.raises(FileNotFoundError, match="doesn’t exist in "):
            convert.PkgConverter(dir_no_spec)

        no_spec_extension = tmp_path / "noext"
        no_spec_extension.touch()
        with pytest.raises(ValueError, match="must have '.spec' as an extension"):
            convert.PkgConverter(no_spec_extension)

    def test_init_not_regular_file(self):
        spec_or_path = mock.Mock()
        spec_or_path.absolute.return_value = spec_or_path
        spec_or_path.is_dir.return_value = False
        spec_or_path.is_file.return_value = False

        with pytest.raises(SpecialFileError, match=r"Spec file or path .* is not a regular file"):
            convert.PkgConverter(spec_or_path)

    def test_init_changelog_exists(self, specfile, repo):
        # The changelog file has already been added:
        changelog = specfile.parent / "changelog"
        changelog.touch()
        with pytest.raises(FileExistsError, match="'changelog' is already in the repository"):
            convert.PkgConverter(specfile)

    def test_init_modified_spec_file(self, specfile, repo):
        # The spec file has been modified without committing it:
        specfile.write_text("Modified")
        with pytest.raises(convert.FileModifiedError, match="is modified"):
            convert.PkgConverter(specfile)

    def test_init_dirty_tree(self, specfile, repo):
        # Other files have been changed, which may corrupt our commit:
        dirty = specfile.parent / "dirty"
        dirty.write_text("")
        repo.index.add("dirty")
        repo.index.write()
        with pytest.raises(convert.FileModifiedError, match="is dirty"):
            convert.PkgConverter(specfile)

    @pytest.mark.parametrize("param_type", (Path, str))
    def test_init_new_file(self, param_type, specfile, repo):
        newfile = specfile.parent / "newfile"
        newfile.touch()
        convert.PkgConverter(param_type(specfile))

    def test_init_spec_file_untracked(self, specfile, repo):
        untracked_spec = specfile.parent / "untracked.spec"
        untracked_spec.touch()

        with pytest.raises(
            convert.FileUntrackedError,
            match=r"Spec file '.*' exists in the repository, but is untracked",
        ):
            convert.PkgConverter(untracked_spec)

    @pytest.mark.parametrize("for_git", (False, True), ids=("not-for-git", "for-git"))
    @pytest.mark.parametrize(
        "converted_release, converted_changelog",
        ((True, False), (False, True), (True, True)),
        ids=("converted-release", "converted-changelog", "converted-release-converted-changelog"),
    )
    @pytest.mark.parametrize("made_commit", (True, False), ids=("made-commit", "not-made-commit"))
    def test_describe_changes(
        self, for_git, converted_release, converted_changelog, made_commit, specfile, repo
    ):
        converter = convert.PkgConverter(specfile)
        converter.converted_release = converted_release
        converter.converted_changelog = converted_changelog
        converter.made_commit = made_commit

        description = converter.describe_changes(for_git)

        if for_git:
            assert description.startswith("Convert to")
        else:
            assert description.startswith("Converted to")

        if converted_release:
            assert "%autorelease" in description
        else:
            assert "%autorelease" not in description

        if converted_changelog:
            assert "%autochangelog" in description
        else:
            assert "%autochangelog" not in description

        if not for_git and made_commit:
            assert "committed to git" in description
        else:
            assert "committed to git" not in description

    @pytest.mark.parametrize(
        "release, changelog",
        (
            (
                "Release: 1",
                "%changelog\n"
                + "* Wed Jan 24 2024 Road Runner <roadrunner@desert.place> 1-1\n"
                + "- Meep meep!\n",
            ),
        ),
        indirect=True,
    )
    @pytest.mark.parametrize("signoff", (False, True), ids=("signoff", "no-signoff"))
    @pytest.mark.parametrize("with_message", (False, True), ids=("without-message", "with-message"))
    def test_commit(self, with_message, signoff, release, changelog, specfile, repo, caplog):
        converter = convert.PkgConverter(specfile)
        converter.load()
        converter.convert_to_autorelease()
        converter.convert_to_autochangelog()
        converter.save()

        if with_message:
            expected_message = message = "The message"
        else:
            message = None
            expected_message = "Convert to %autorelease and %autochangelog\n\n[skip changelog]"

        if signoff:
            expected_message += "\n\nSigned-off-by: Jane Doe <jane.doe@example.com>"

        converter.commit(message=message, signoff=signoff)

        head_commit = repo[repo.head.target]

        assert head_commit.message == expected_message


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
    assert "already uses %autorelease" in caplog.records[0].message


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
    with pytest.raises(SpecParseFailure, match=expected):
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
    assert "already uses %autochangelog" in caplog.records[0].message


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
    with pytest.raises(SpecParseFailure, match=expected):
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
        *(delta.new_file.path for delta in diff.deltas),
        *(delta.old_file.path for delta in diff.deltas),
    }

    if changelog_should_change or release_should_change:
        expected_message = "Convert to rpmautospec."
    else:
        expected_message = "Did something!"
    assert head.message == expected_message
    assert specfile.name in fileschanged
    assert ("changelog" in fileschanged) == changelog_should_change
