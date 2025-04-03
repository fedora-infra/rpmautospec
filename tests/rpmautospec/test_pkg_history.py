import datetime as dt
import os
import re
import stat
from calendar import LocaleTextCalendar
from contextlib import nullcontext
from pathlib import Path
from shutil import SpecialFileError, rmtree
from unittest import mock

import pytest

from rpmautospec import pkg_history
from rpmautospec.compat import pygit2, rpm

from ..common import SPEC_FILE_TEMPLATE, create_commit


def test__checkout_tree_files(repopath, specfile, repo, tmp_path):
    # Add a symlink in a new commit
    symlink = repopath / "symlink"
    symlink.symlink_to(specfile.name)

    index = repo.index
    index.add(symlink.name)
    index.write()

    tree = index.write_tree()

    parent, ref = repo.resolve_refish(repo.head.name)

    oid = repo.create_commit(
        ref.name,
        repo.default_signature,
        repo.default_signature,
        "Added a symlink!",
        tree,
        [parent.id],
    )

    head_commit = repo[oid]

    # Now check out the files elsewhere
    elsewhere = tmp_path / "elsewhere"

    pkg_history._checkout_tree_files(head_commit, head_commit.tree, elsewhere)

    specfile_dst = elsewhere / specfile.name
    with specfile.open("r") as src, specfile_dst.open("r") as dst:
        assert src.read() == dst.read()

    symlink_dst = elsewhere / symlink.name
    assert symlink_dst.is_symlink()
    assert symlink_dst.resolve() == specfile_dst


@pytest.fixture
def processor(repo):
    processor = pkg_history.PkgHistoryProcessor(repo.workdir)
    processor.repo = repo
    return processor


class TestPkgHistoryProcessor:
    version_re = re.compile(r"^Version: .*$", flags=re.MULTILINE)

    @pytest.mark.parametrize(
        "testcase",
        (
            "str, is file",
            "str, is dir",
            "path, is file",
            "path, is file, wrong extension",
            "path, is dir",
            "doesn't exist",
            "spec doesn't exist, is dir",
            "no git repo",
            "not a regular file",
        ),
    )
    @mock.patch("rpmautospec.pkg_history.pygit2")
    def test___init__(self, pygit2, testcase, specfile):
        if "wrong extension" in testcase:
            # Path.rename() only returns the new path from Python 3.8 on.
            specfile.rename(specfile.with_suffix(".foo"))
            specfile = specfile.with_suffix(".foo")

        spec_or_path = specfile

        if "is dir" in testcase:
            spec_or_path = spec_or_path.parent

        if "spec doesn't exist" in testcase:
            specfile.unlink()
        elif "doesn't exist" in testcase:
            rmtree(specfile.parent)

        if "str" in testcase:
            spec_or_path = str(spec_or_path)

        if "doesn't exist" in testcase:
            with pytest.raises(FileNotFoundError) as excinfo:
                pkg_history.PkgHistoryProcessor(spec_or_path)
            if "spec doesn't exist" in testcase:
                expected_message = f"Spec file '{specfile}' doesn't exist in '{specfile.parent}'."
            else:
                expected_message = f"Spec file or path '{spec_or_path}' doesn't exist."
            assert str(excinfo.value) == expected_message
            return

        if "not a regular file" in testcase:
            specfile.unlink()
            os.mknod(specfile, stat.S_IFIFO | stat.S_IRUSR | stat.S_IWUSR)
            with pytest.raises(SpecialFileError) as excinfo:
                pkg_history.PkgHistoryProcessor(spec_or_path)
            assert str(excinfo.value) == "File specified as `spec_or_path` is not a regular file."
            return

        if "wrong extension" in testcase:
            with pytest.raises(ValueError) as excinfo:
                pkg_history.PkgHistoryProcessor(spec_or_path)
            assert str(excinfo.value) == (
                "File specified as `spec_or_path` must have '.spec' as an extension."
            )
            return

        if "no git repo" in testcase:

            class GitError(Exception):
                pass

            pygit2.GitError = GitError
            pygit2.Repository.side_effect = GitError

        processor = pkg_history.PkgHistoryProcessor(spec_or_path)

        assert processor.specfile == specfile
        assert processor.path == specfile.parent

        pygit2.Repository.assert_called_once()

        if "no git repo" in testcase:
            assert processor.repo is None
        else:
            assert processor.repo

    @pytest.mark.parametrize(
        "with_exception", (False, True), ids=("without-exception", "with-exception")
    )
    def test__get_rpm_packager(self, with_exception, processor):
        with mock.patch.object(pkg_history, "rpm") as rpm:
            if with_exception:
                rpm.expandMacro.side_effect = Exception("CARRIER LOST")
            else:
                rpm.expandMacro.return_value = "BOOP"

            result = processor._get_rpm_packager()

            if with_exception:
                assert result == "John Doe <packager@example.com>"
            else:
                assert result == "BOOP"

    @pytest.mark.parametrize(
        "testcase",
        (
            "normal",
            "with-name",
            "specfile-missing",
            "specfile-broken",
            "specfile-broken-without-log-error",
        ),
    )
    @pytest.mark.parametrize(
        "release",
        (
            "Release: %autorelease",
            "Release: %autorelease -b 5",
            "Release: 1",
        ),
        ids=(
            "autorelease",
            "autorelease-base",
            "manual",
        ),
    )
    @pytest.mark.parametrize(
        "prep, abridged_fails",
        (
            ("%prep", False),
            ("", False),
            ("%package boo\nSummary: Boo boo\n%prep\n%description boo", True),
        ),
        ids=("with-prep", "without-prep", "with-prep-inadequate"),
        indirect=["prep"],
    )
    def test__get_rpmverflags(
        self, testcase, release, prep, abridged_fails, specfile, processor, caplog
    ):
        with_name = "with-name" in testcase
        specfile_missing = "specfile-missing" in testcase
        specfile_broken = "specfile-broken" in testcase
        log_error = "without-log-error" not in testcase
        manual = "%autorelease" not in release
        if not manual:
            base = 5 if "-b" in release else 1
        else:
            base = None

        if with_name:
            name = specfile.stem
        else:
            name = None

        if specfile_missing:
            specfile.unlink()

        if specfile_broken:
            specfile.unlink()
            specfile.touch()

        with (
            caplog.at_level("DEBUG"),
            mock.patch.object(rpm, "spec", wraps=rpm.spec) as mock_rpm_spec,
        ):
            if abridged_fails:
                mock_rpm_spec.side_effect = [
                    ValueError("can't parse specfile\n"),
                    mock.DEFAULT,
                ]

            result = processor._get_rpmverflags(specfile.parent, name=name, log_error=log_error)

        if specfile_missing or specfile_broken:
            assert "error" in result
        else:
            assert result == {
                "epoch-version": "1.0",
                "extraver": None,
                "snapinfo": None,
                "prerelease": None,
                "base": base,
            }

        if specfile_missing:
            assert result["error"] == "specfile-missing"
        elif specfile_broken:
            assert result["error"] == "specfile-parse-error"

        if log_error:
            if specfile_missing:
                assert "spec file missing" in caplog.text
            elif specfile_broken:
                assert re.search(r"rpm query for .* failed", caplog.text)
        else:
            assert caplog.text == ""

    @pytest.mark.parametrize(
        "testcase",
        ("normal", "no-spec-file", "needs-full-repo"),
    )
    def test__get_rpmverflags_for_commit(self, testcase, specfile, repo, processor):
        head_commit = repo[repo.head.target]

        no_spec_file = "no-spec-file" in testcase
        needs_full_repo = "needs-full-repo" in testcase

        if no_spec_file:
            index = repo.index
            index.remove(specfile.name)
            index.write()

            tree = index.write_tree()

            parent, ref = repo.resolve_refish(repo.head.name)

            head_commit = repo[
                repo.create_commit(
                    ref.name,
                    repo.default_signature,
                    repo.default_signature,
                    "Be gone, spec file!",
                    tree,
                    [parent.id],
                )
            ]

        with (
            mock.patch.object(
                processor, "_get_rpmverflags", wraps=processor._get_rpmverflags
            ) as _get_rpmverflags,
            mock.patch.object(
                pkg_history, "_checkout_tree_files", side_effect=pkg_history._checkout_tree_files
            ) as _checkout_tree_files,
        ):
            side_effect = [mock.DEFAULT]
            if needs_full_repo:
                side_effect.insert(0, {"error": "specfile-parse-error"})
            _get_rpmverflags.side_effect = side_effect

            calls_in_order = mock.Mock()
            calls_in_order.attach_mock(_get_rpmverflags, "_get_rpmverflags")
            calls_in_order.attach_mock(_checkout_tree_files, "_checkout_tree_files")

            result = processor._get_rpmverflags_for_commit(head_commit)

        if no_spec_file:
            assert result["error"] == "specfile-missing"
            _get_rpmverflags.assert_not_called()
            _checkout_tree_files.assert_not_called()
        else:
            assert result["epoch-version"] == "1.0"

            if not needs_full_repo:
                _get_rpmverflags.assert_called_once_with(mock.ANY, processor.name, log_error=False)
                _checkout_tree_files.assert_not_called()
            else:
                calls_in_order.assert_has_calls(
                    (
                        mock.call._get_rpmverflags(mock.ANY, processor.name, log_error=False),
                        mock.call._checkout_tree_files(head_commit, head_commit.tree, mock.ANY),
                        mock.call._get_rpmverflags(mock.ANY, processor.name),
                    )
                )

    @pytest.mark.parametrize("testcase", ("normal", "needs-full-repo"))
    def test__get_rpmverflags_for_commit_cache(self, testcase, repo, processor):
        head_commit = repo[repo.head.target]

        with mock.patch.object(processor, "_get_rpmverflags") as _get_rpmverflags:
            _get_rpmverflags.return_value = retval = {}

            if testcase == "needs-full-repo":
                retval["error"] = "specfile-parse-error"

            assert processor._get_rpmverflags_for_commit(head_commit) is retval

            if testcase == "needs-full-repo":
                assert _get_rpmverflags.call_args_list == [
                    mock.call(mock.ANY, processor.name, log_error=False),
                    mock.call(mock.ANY, processor.name),
                ]
            else:
                _get_rpmverflags.assert_called_once_with(mock.ANY, processor.name, log_error=False)

            # Check that value is cached

            _get_rpmverflags.reset_mock()

            assert processor._get_rpmverflags_for_commit(head_commit) is retval

            _get_rpmverflags.assert_not_called()

    @pytest.mark.parametrize("testcase", ("normal", "key-error"))
    def test__merge_info(self, testcase, processor):
        f1 = {"child_must_continue": False, "changelog_removed": False}
        f2 = {"child_must_continue": True, "changelog_removed": True}

        if "key-error" in testcase:
            f1["boo"] = f2["boo"] = "BOOM"
            catch_exc = pytest.raises(KeyError, match="boo")
        else:
            catch_exc = nullcontext()

        with catch_exc:
            assert processor._merge_info(f1, f2) == {
                "child_must_continue": True,
                "changelog_removed": False,
            }

    @pytest.mark.parametrize(
        "testcase",
        (
            "without-commit",
            "with-commit",
            "all-results",
            "locale-set",
            "without-repo",
            "with-merge",
            "missing-specfile",
            "missing-specfile-missing-default-signature",
            "dirty",
            "dirty-missing-default-signature",
        ),
    )
    @pytest.mark.repo_config(converted=True)
    def test_run(self, testcase, specfile, specfile_content, repo, processor, locale):
        if testcase == "locale-set":
            locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

        all_results = "all-results" in testcase

        expected_release = 1

        if "without-repo" in testcase:
            rmtree(repo.path)
            processor = pkg_history.PkgHistoryProcessor(repo.workdir)
            head_commit = None
        else:
            head_commit = repo[repo.head.target]

        signature = pygit2.Signature("The Great Pretender", "ohyes@i.am")

        if "with-merge" in testcase:
            # Mess a bit with the spec file …
            specfile.write_text(specfile_content + "\n\n")

            result = create_commit(
                repo,
                author=signature,
                committer=signature,
                message="Bow before my white space!",
            )
            head_commit = result["commit"]

            # … and then revert by a merge using the previous tree. Seriously.
            parent_commit = head_commit.parents[0]
            result = create_commit(
                repo,
                author=signature,
                committer=signature,
                message="Rebuild for fun and giggles",
                tree_id=parent_commit.tree.id,
                parents=[head_commit.id, parent_commit.id],
            )

            head_commit = result["commit"]
            expected_release += 2

        if "missing-specfile" in testcase:
            specfile.unlink()

        if "dirty" in testcase:
            expected_release += 1
            with specfile.open("a") as fp:
                fp.write("\n\n")

        if "missing-default-signature" in testcase:
            del repo.config["user.name"]
            del repo.config["user.email"]

        if "with-commit" in testcase:
            # Pass as string
            args = [str(head_commit.id)]
        elif "with-merge" in testcase:
            # Pass the commit object
            args = [head_commit]
        else:
            args = []

        res = processor.run(
            *args,
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            all_results=all_results,
        )

        assert isinstance(res, dict)
        if all_results:
            assert all(isinstance(key, pygit2.Commit) for key in res)
            # only verify outcome for head commit below
            res = res[head_commit]
        else:
            assert all(isinstance(key, str) for key in res)

        if "missing-specfile" in testcase:
            assert res["epoch-version"] is None
            assert not res["changelog"]
            return

        changelog = res["changelog"]
        top_entry = changelog[0]

        assert res["release-number"] == expected_release

        if "without-repo" in testcase:
            for snippet in (
                processor._get_rpm_packager(),
                "- Uncommitted changes",
            ):
                assert snippet in top_entry.format()
        elif "dirty" not in testcase:
            assert res["commit-id"] == head_commit.id
            if "with-merge" in testcase:
                assert top_entry["commit-id"] == parent_commit.id
            else:
                assert top_entry["commit-id"] == head_commit.id

                for snippet in (
                    "Jane Doe <jane.doe@example.com>",
                    "- Did something!",
                ):
                    assert snippet in top_entry.format()

                cal = LocaleTextCalendar(firstweekday=0, locale="C.UTF-8")
                commit_time = dt.datetime.fromtimestamp(head_commit.commit_time, dt.timezone.utc)
                weekdayname = cal.formatweekday(day=commit_time.weekday(), width=3)
                monthname = cal.formatmonthname(
                    theyear=commit_time.year,
                    themonth=commit_time.month,
                    width=1,
                    withyear=False,
                )[:3]
                expected_date_blurb = (
                    f"* {weekdayname} {monthname} {commit_time.day:02} {commit_time.year}"
                )
                assert top_entry.format().startswith(expected_date_blurb)
        else:
            assert top_entry["commit-id"] is None
            assert top_entry["commitlog"] == "Uncommitted changes"
            if "missing-default-signature" not in testcase:
                assert top_entry["authorblurb"] == "Jane Doe <jane.doe@example.com>"
            else:
                assert top_entry["authorblurb"] == (
                    "Unknown User <please-configure-git-user@example.com>"
                )

        assert all("error" not in entry for entry in changelog)

        verflags = res["verflags"]
        assert verflags["base"] == 1
        assert verflags["epoch-version"] == "1.0"
        assert verflags["extraver"] is None
        assert verflags["prerelease"] is None
        assert verflags["snapinfo"] is None

    @pytest.mark.repo_config(uses_rpmautospec=False, converted=False, add_commit=False)
    def test_run__with_wonky_history(self, repo, processor):
        workdir = Path(repo.workdir)
        specfile = workdir / "test.spec"

        # This takes some setting up, starting with two non-rpmautospec commits

        rawhide_tmpl_args = {
            "version": "Version: 0.8",
            "release": "Release: 2%{?dist}",
            "prep": "%prep",
            "changelog": "%changelog\n"
            + "* Jane Doe <jane.doe@example.com> - 0.8-2\n- Do the thing\n\n"
            + "* Jane Doe <jane.doe@example.com> - 0.8-1\n- Import the package\n",
        }
        specfile.write_text(SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
        epel_tip = create_commit(repo, message="Do the thing", create_branch="epel")["oid"]

        # Simulate activity
        rawhide_tmpl_args["prep"] = "%prep\necho Hello\n\n"
        rawhide_tmpl_args["release"] = "Release: 3%{?dist}"
        rawhide_tmpl_args["changelog"] = rawhide_tmpl_args["changelog"].replace(
            "%changelog\n",
            "%changelog\n" + "* Jane Doe <jane.doe@example.com> - 0.8-3\n" + "- Hello\n\n",
        )
        specfile.write_text(SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
        create_commit(repo, message="Hello")

        # Bump version and convert to rpmautospec
        changelogfile = workdir / "changelog"
        changelogfile.write_text(
            rawhide_tmpl_args["changelog"].replace(
                "%changelog\n",
                "* Jane Doe <jane.doe@example.com> - 0.9-1\n- Update to version 0.9\n\n",
            )
        )
        rawhide_tmpl_args |= {
            "version": "Version: 0.9",
            "release": "Release: %autorelease",
            "changelog": "%changelog\n%autochangelog\n",
        }
        specfile.write_text(SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
        result = create_commit(
            repo,
            reference_name="refs/heads/rawhide",
            message="Update to version 0.9\n\nConvert to rpmautospec.\n",
        )
        rawhide_tip = result["oid"]
        rawhide_tree = result["commit"].tree

        ### epel
        repo.checkout("refs/heads/epel")

        # Merge rawhide into epel
        epel_tip = create_commit(
            repo,
            message="Merge branch rawhide into epel",
            tree_id=rawhide_tree.id,
            parents=[epel_tip, rawhide_tip],
        )["oid"]

        ### rawhide
        repo.checkout("refs/heads/rawhide")

        # Bump the version and screw up rpmautospec
        rawhide_tmpl_args["version"] = "Version: 1.0"
        rawhide_tmpl_args["release"] = "Release: 1%{?dist}"
        rawhide_tmpl_args["changelog"] = (
            "%changelog\n"
            + "* Jane Doe <jane.doe@example.com> - 1.0-1\n"
            + "- Update to version 1.0\n\n"
            + "%autochangelog\n"
        )
        specfile.write_text(SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
        create_commit(repo, message="Update to version 1.0")

        # Bump again
        rawhide_tmpl_args["version"] = "Version: 1.1"
        rawhide_tmpl_args["changelog"] = rawhide_tmpl_args["changelog"].replace(
            "%changelog\n",
            "%changelog\n"
            + "* Jane Doe <jane.doe@example.com> - 1.1-1\n"
            + "- Update to version 1.1\n\n",
        )
        specfile.write_text(SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
        result = create_commit(repo, message="Update to version 1.1")
        rawhide_tip = result["oid"]
        rawhide_tree = result["commit"].tree

        ### epel
        repo.checkout("refs/heads/epel")

        # Merge rawhide into epel
        epel_tip = create_commit(
            repo,
            message="Merge branch rawhide into epel",
            tree_id=rawhide_tree.id,
            parents=[epel_tip, rawhide_tip],
        )["oid"]

        ### rawhide
        repo.checkout("refs/heads/rawhide")

        # Fix rpmautospec
        rawhide_tmpl_args["release"] = "Release: %autorelease"
        changelogfile.write_text(
            rawhide_tmpl_args["changelog"]
            .replace("%changelog\n", "")
            .replace("%autochangelog\n", "")
            + changelogfile.read_text()
        )
        rawhide_tmpl_args["changelog"] = "%changelog\n%autochangelog\n"
        specfile.write_text(SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
        result = create_commit(repo, message="Fix using rpmautospec")
        rawhide_tip = result["oid"]
        rawhide_tree = result["commit"].tree

        ### epel
        repo.checkout("refs/heads/epel")

        # Merge rawhide into epel
        create_commit(
            repo,
            message="Merge branch rawhide into epel",
            tree_id=rawhide_tree.id,
            parents=[epel_tip, rawhide_tip],
        )

        res = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
        )

        assert res["epoch-version"] == "1.1"
        assert res["release-complete"] == "3"
        assert (
            res["changelog"][0]["data"]
            == """* Jane Doe <jane.doe@example.com> - 1.1-1
- Update to version 1.1

* Jane Doe <jane.doe@example.com> - 1.0-1
- Update to version 1.0

* Jane Doe <jane.doe@example.com> - 0.9-1
- Update to version 0.9

* Jane Doe <jane.doe@example.com> - 0.8-3
- Hello

* Jane Doe <jane.doe@example.com> - 0.8-2
- Do the thing

* Jane Doe <jane.doe@example.com> - 0.8-1
- Import the package
"""
        )
