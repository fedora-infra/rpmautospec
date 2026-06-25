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
from rpmautospec.specparser import SpecParserError

from ..common import SPEC_FILE_TEMPLATE, create_commit, create_tagged_repo


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
def processor(request: pytest.FixtureRequest, repo):
    specfile_parser = None
    exc = None
    expectation = nullcontext()

    for node in request.node.listchain():
        for marker in node.own_markers:
            if marker.name == "specfile_parser":
                if not marker.args:
                    specfile_parser = None
                elif len(marker.args) > 2:
                    raise ValueError("specfile_parser takes no more than two arguments")
                else:
                    specfile_parser = marker.args[0]
                    if len(marker.args) > 1:
                        exc = marker.args[1]
                    else:
                        exc = None

                    if exc:
                        expectation = pytest.raises(exc)
                        pytest.xfail("Invalid value of RPMAUTOSPEC_SPEC_PARSER")
                    else:
                        expectation = nullcontext()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.delenv("RPMAUTOSPEC_SPEC_PARSER", raising=False)
        if specfile_parser is not None:
            if specfile_parser == "norpm":
                pytest.importorskip("norpm")
            monkeypatch.setenv("RPMAUTOSPEC_SPEC_PARSER", specfile_parser)

        with expectation:
            processor = pkg_history.PkgHistoryProcessor(repo.workdir)

        if exc:
            yield None
        else:
            processor.repo = repo

            yield processor


def _parametrize_test__get_rpmverflags() -> tuple[pytest.param, ...]:
    testcases = (
        "normal",
        "with-name",
        "specfile-missing",
        "specfile-broken",
        "specfile-broken-without-log-error",
    )

    releases_by_id = {
        "autorelease": "Release: %autorelease",
        "autorelease-base": "Release: %autorelease -b 5",
        "manual": "Release: 1",
    }

    prep_abridged_fails_by_id = {
        "with-prep": ("%prep", False),
        "without-prep": ("", False),
        "with-prep-inadequate": (
            "%package boo\nSummary: Boo boo\n%prep\n%description boo",
            True,
        ),
    }

    specfile_parser_by_id = {
        "with-rpm-default": None,
        "with-rpm": "rpm",
        "with-norpm": "norpm",
        "with-illegal-specfile-parser": "illegal",
    }

    param_sets = [
        pytest.param(
            testcase,
            release,
            prep,
            abridged_fails,
            specfile_parser,
            marks=(
                pytest.mark.specfile_parser(specfile_parser)
                if specfile_parser != "illegal"
                else pytest.mark.specfile_parser(specfile_parser, SpecParserError)
            ),
            id=f"{testcase}-{release_id}-{prep_af_id}-{specfile_parser_id}",
        )
        for testcase in testcases
        for release_id, release in releases_by_id.items()
        for prep_af_id, (prep, abridged_fails) in prep_abridged_fails_by_id.items()
        for specfile_parser_id, specfile_parser in specfile_parser_by_id.items()
        if (
            specfile_parser != "illegal"
            or (testcase, release_id, prep_af_id) == ("normal", "autorelease", "with-prep")
        )  # Test illegal specfile parser only once
    ]

    return param_sets


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
        "testcase, release, prep, abridged_fails, specfile_parser",
        _parametrize_test__get_rpmverflags(),
    )
    def test__get_rpmverflags(
        self,
        testcase,
        release,
        prep,
        abridged_fails,
        specfile_parser,
        specfile,
        processor,
        caplog,
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
                assert re.search(r"spec file query failed: ", caplog.text)
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

    @pytest.mark.parametrize(
        "specfile_parser",
        (
            pytest.param("rpm", marks=pytest.mark.specfile_parser("rpm"), id="with-rpm"),
            pytest.param("norpm", marks=pytest.mark.specfile_parser("norpm"), id="with-norpm"),
        ),
    )
    @pytest.mark.parametrize("epoch", (None, "2"), ids=("without-epoch", "with-epoch"))
    @pytest.mark.repo_config(uses_rpmautospec=False, converted=False, add_commit=False)
    def test_run_epoch(self, specfile_parser, epoch, repo, processor):
        workdir = Path(repo.workdir)
        specfile = workdir / "test.spec"

        rawhide_tmpl_args = {
            "version": "Version: 1",
            "release": "Release: 2%{?dist}",
            "prep": "%prep",
            "changelog": "%changelog\n"
            + "* Jane Doe <jane.doe@example.com> - 0.8-2\n- Do the thing\n\n"
            + "* Jane Doe <jane.doe@example.com> - 0.8-1\n- Import the package\n",
        }

        def _write_it(message):
            epoch_text = f"Epoch: {epoch}\n" if epoch else ""
            specfile.write_text(epoch_text + SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
            create_commit(repo, message=message)

        # One non-rpmautospec commit
        _write_it("Initial commit")

        # Convert to autorelease
        rawhide_tmpl_args["release"] = "Release: %autorelease"
        _write_it("Use %autorelease")

        # Simulate activity
        rawhide_tmpl_args["prep"] = "%prep\necho Hello\n\n"
        _write_it("Do something")

        res = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
        )

        assert res["epoch-version"] == "2:1" if epoch else "1"
        assert res["release-number"] == 3

    @pytest.mark.repo_config(uses_rpmautospec=False, converted=False, add_commit=False)
    @pytest.mark.specfile_parser("norpm")
    def test_norpm_and_lua_in_epoch(self, repo, processor):
        workdir = Path(repo.workdir)
        specfile = workdir / "test.spec"

        rawhide_tmpl_args = {
            "version": "Version: 1",
            "release": "Release: %autorelease",
            "prep": "%prep",
            "changelog": "%changelog\n",
        }
        epoch_text = "Epoch: %{lua: something}\n"
        specfile.write_text(epoch_text + SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
        create_commit(repo, message="initial commit")
        res = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
        )
        assert res["release-number"] == 2
        assert "unexpanded macro in epoch_version" in res["verflags"]["error-detail"]

    @pytest.mark.repo_config(uses_rpmautospec=False, converted=False, add_commit=False)
    @pytest.mark.parametrize(
        "specfile_parser",
        (
            pytest.param("rpm", marks=pytest.mark.specfile_parser("rpm"), id="with-rpm"),
            pytest.param("norpm", marks=pytest.mark.specfile_parser("norpm"), id="with-norpm"),
        ),
    )
    def test_spec_syntax_error(self, specfile_parser, repo, processor):
        workdir = Path(repo.workdir)
        specfile = workdir / "test.spec"
        rawhide_tmpl_args = {
            "version": "Version: 1",
            "release": "Release: %autorelease",
            "prep": "%prep",
            "changelog": "%changelog\n",
        }
        breaking_part = (
            "%if\n"  # if without expression - both {no,}rpm fail to parse this
            "do something\n"
            "%endif\n"
        )
        specfile.write_text(breaking_part + SPEC_FILE_TEMPLATE.format(**rawhide_tmpl_args))
        create_commit(repo, message="initial commit")
        res = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
        )
        assert res["release-number"] == 2
        assert res["verflags"]["error"] == "specfile-parse-error"


def _make_spec(name="pkg", version="1.0", summary="t", desc="T"):
    """Create a minimal spec file content string."""
    return (
        f"Name: {name}\nVersion: {version}\nRelease: %autorelease\n"
        f"Summary: {summary}\n\nLicense: MIT\n\n%description\n{desc}\n"
    )


class TestTagBasedProcessing:
    """Tests for tag-based release and changelog methods."""

    def _processor(self, tmp_path, **kwargs):
        repo_path, _ = create_tagged_repo(tmp_path, **kwargs)
        return pkg_history.PkgHistoryProcessor(repo_path)

    @pytest.mark.parametrize(
        "tags, namespace, expected_count",
        [
            # No tags: empty result
            (None, "fedora/f44", 0),
            # Two tags on same commit: one commit key, two NVRs
            ([("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-2.0-3", 0)], "fedora/f44", 1),
            # Tags on different commits
            ([("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-2.0-1", 1)], "fedora/f44", 2),
            # Non-NVR tags filtered out (too few segments, non-numeric release)
            (
                [
                    ("fedora/f44/not-enough", 0),
                    ("fedora/f44/also-bad", 0),
                    ("fedora/f44/pkg-1.0-rc1", 0),
                    ("fedora/f44/pkg-1.0-1", 0),
                ],
                "fedora/f44",
                1,
            ),
            # Wrong package name filtered out
            ([("fedora/f44/other-1.0-1", 0), ("fedora/f44/pkg-1.0-1", 0)], "fedora/f44", 1),
        ],
        ids=[
            "no-tags",
            "same-commit",
            "different-commits",
            "non-nvr-filtered",
            "wrong-name-filtered",
        ],
    )
    def test_get_tags_for_namespace(self, tmp_path, tags, namespace, expected_count):
        commits = ["first", "second"] if any(t[1] == 1 for t in (tags or [])) else None
        processor = self._processor(tmp_path, commits=commits, tags=tags)
        result = processor.get_tags_for_namespace(namespace)
        assert len(result) == expected_count

    def test_get_tags_for_namespace_different_namespaces(self, tmp_path):
        """Each namespace returns only its own tags."""
        processor = self._processor(
            tmp_path,
            tags=[
                ("fedora/f44/pkg-1.0-1", 0),
                ("fedora/f43/pkg-2.0-1", 0),
                ("fedora/f42/pkg-3.0-1", 0),
            ],
        )
        assert (
            list(processor.get_tags_for_namespace("fedora/f44").values())[0][0]["version"] == "1.0"
        )
        assert (
            list(processor.get_tags_for_namespace("fedora/f43").values())[0][0]["version"] == "2.0"
        )
        assert (
            list(processor.get_tags_for_namespace("fedora/f42").values())[0][0]["version"] == "3.0"
        )

    def test_get_tags_for_namespace_no_repo(self, tmp_path):
        """Without a git repo, returns empty."""
        pkg_dir = tmp_path / "norepo"
        pkg_dir.mkdir()
        spec = pkg_dir / "norepo.spec"
        spec.write_text("Name: norepo\nVersion: 1.0\nRelease: 1\nSummary: test\n")
        processor = pkg_history.PkgHistoryProcessor(pkg_dir)
        assert processor.get_tags_for_namespace("fedora/f44") == {}

    def test_make_changelog_entry_fields(self, tmp_path):
        repo_path, oids = create_tagged_repo(tmp_path, commits=["test msg"])
        processor = pkg_history.PkgHistoryProcessor(repo_path)
        commit = processor.repo.get(oids[0])

        entry = processor._make_changelog_entry(commit, "2.0", "5")

        assert entry["commit-id"] == commit.id
        assert entry["authorblurb"] == "Test User <test@example.com>"
        assert entry["epoch-version"] == "2.0"
        assert entry["release-complete"] == "5"
        assert entry["commitlog"] == "test msg"
        assert isinstance(entry["timestamp"], dt.datetime)
        assert entry["timestamp"].tzinfo == dt.timezone.utc

    def test_changelog_from_tags_empty_when_no_tags(self, tmp_path):
        processor = self._processor(tmp_path, commits=["c1"])
        assert processor._changelog_from_tags("fedora/f44") == ()

    def test_changelog_from_tags_one_entry_per_commit(self, tmp_path):
        processor = self._processor(
            tmp_path,
            commits=["first", "second"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-2", 1)],
        )
        result = processor._changelog_from_tags("fedora/f44")
        assert len(result) == 2
        assert "second" in result[0]["commitlog"]
        assert "first" in result[1]["commitlog"]

    def test_changelog_from_tags_sorted_by_timestamp(self, tmp_path):
        processor = self._processor(
            tmp_path,
            commits=[("older", 1700000100), ("newer", 1700000500)],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-2", 1)],
        )
        result = processor._changelog_from_tags("fedora/f44")
        assert result[0]["timestamp"] > result[1]["timestamp"]

    def test_changelog_from_tags_dedup_uses_lowest_by_default(self, tmp_path):
        processor = self._processor(
            tmp_path,
            commits=["rebuilt"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-3", 0)],
        )
        result = processor._changelog_from_tags("fedora/f44")
        assert len(result) == 1
        assert result[0]["release-complete"] == "1"

    def test_changelog_from_tags_dedup_uses_highest_when_requested(self, tmp_path):
        processor = self._processor(
            tmp_path,
            commits=["rebuilt"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-3", 0)],
        )
        result = processor._changelog_from_tags("fedora/f44", use_highest_release_tag=True)
        assert len(result) == 1
        assert result[0]["release-complete"] == "3"

    def test_changelog_from_tags_ignores_other_namespaces(self, tmp_path):
        processor = self._processor(
            tmp_path,
            commits=["c1", "c2", "c3"],
            tags=[
                ("fedora/f44/pkg-1.0-1", 0),
                ("fedora/f43/pkg-1.0-1", 1),
                ("rhel/el9/pkg-1.0-1", 2),
            ],
        )
        result = processor._changelog_from_tags("fedora/f44")
        assert len(result) == 1
        assert "c1" in result[0]["commitlog"]

    @pytest.mark.parametrize(
        "version, tags, expected",
        [
            # No tags at all: returns base (first build)
            ("1.0", [], 1),
            # Tags exist but none match namespace: returns base
            ("1.0", [("fedora/f43/pkg-1.0-1", 0)], 1),
            # Tags match namespace but different version: returns base (1)
            ("2.0", [("fedora/f44/pkg-1.0-3", 0)], 1),
            # Tags match namespace+version: returns max(release) + 1
            ("1.0", [("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-5", 0)], 6),
        ],
        ids=["no-tags", "wrong-namespace", "version-mismatch", "matching-increments"],
    )
    def test_release_from_tags(self, tmp_path, version, tags, expected):
        processor = self._processor(tmp_path, version=version, tags=tags or None)
        assert processor._release_from_tags("fedora/f44") == expected

    def test_release_from_tags_base_as_floor(self, tmp_path):
        """-b N is honoured as a floor even when tags exist."""
        processor = self._processor(
            tmp_path,
            version="1.0",
            tags=[("fedora/f44/pkg-1.0-2", 0)],
            base=100,
        )
        assert processor._release_from_tags("fedora/f44") == 100

    def test_release_from_tags_base_below_tag(self, tmp_path):
        """-b N below the tag release doesn't reduce the result."""
        processor = self._processor(
            tmp_path,
            version="1.0",
            tags=[("fedora/f44/pkg-1.0-50", 0)],
            base=10,
        )
        assert processor._release_from_tags("fedora/f44") == 51

    def test_release_from_tags_new_version_uses_base(self, tmp_path):
        """New version with no matching tags returns base."""
        processor = self._processor(
            tmp_path,
            version="2.0",
            tags=[("fedora/f44/pkg-1.0-5", 0)],
            base=100,
        )
        assert processor._release_from_tags("fedora/f44") == 100

    def test_release_from_tags_spec_parse_error(self, tmp_path):
        """If spec can't be parsed, returns None even with matching tags."""
        repo_path, _ = create_tagged_repo(tmp_path, tags=[("fedora/f44/pkg-1.0-1", 0)])
        spec = repo_path / "pkg.spec"
        spec.write_text("garbage content\n")
        processor = pkg_history.PkgHistoryProcessor(repo_path)
        assert processor._release_from_tags("fedora/f44") is None

    def test_run_no_namespace_uses_normal_walk(self, tmp_path):
        """Without git_tag_namespace, run() uses normal history walk."""
        processor = self._processor(tmp_path, commits=["c0", "c1", "c2"])
        result = processor.run(visitors=[processor.release_number_visitor])
        assert result["release-number"] == 3

    def test_run_namespace_with_matching_tags_uses_tags(self, tmp_path):
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=["c0", "c1", "c2", "c3", "c4", "c5"],
            tags=[
                ("fedora/f44/pkg-1.0-1", 0),
                ("fedora/f44/pkg-1.0-2", 1),
                ("fedora/f44/pkg-1.0-3", 2),
                ("fedora/f44/pkg-1.0-4", 3),
                ("fedora/f44/pkg-1.0-5", 4),
            ],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor], git_tag_namespace="fedora/f44"
        )
        assert result["release-number"] == 6

    def test_run_namespace_no_tags_first_build(self, tmp_path):
        """Tag mode but no tags exist or match: release is base (1)."""
        processor = self._processor(tmp_path, commits=["c0", "c1", "c2"])
        result = processor.run(
            visitors=[processor.release_number_visitor], git_tag_namespace="fedora/f44"
        )
        assert result["release-number"] == 1

    def test_run_namespace_with_all_results(self, tmp_path):
        processor = self._processor(
            tmp_path, version="1.0", commits=["c0", "c1", "c2"], tags=[("fedora/f44/pkg-1.0-5", 0)]
        )
        result = processor.run(
            visitors=[processor.release_number_visitor],
            git_tag_namespace="fedora/f44",
            all_results=True,
        )
        assert isinstance(result, dict)
        assert len(result) == 1
        assert list(result.values())[0]["release-number"] == 6

    def test_run_changelog_tagged_only_no_tags_first_build(self, tmp_path):
        """No tags, tagged-only mode: single entry with HEAD's message, release = base."""
        processor = self._processor(tmp_path, commits=["c0", "c1", "c2"])
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="tagged-only",
        )
        assert result["release-number"] == 1
        changelog = result["changelog"]
        # tagged-only with no tags: just HEAD's entry
        assert len(changelog) == 1
        assert changelog[0]["release-complete"] == "1"
        assert "c2" in changelog[0]["commitlog"]

    def test_run_changelog_tagged_only_current_commit_prepended(self, tmp_path):
        """HEAD is tagged: in lowest mode, no duplicate entry — tag history includes HEAD."""
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=["first", "second"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-2", 1)],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="tagged-only",
        )
        assert result["release-number"] == 3
        changelog = result["changelog"]
        # HEAD is already in tag history — no duplicate, just 2 entries
        assert len(changelog) == 2
        assert changelog[0]["release-complete"] == "2"
        assert changelog[1]["release-complete"] == "1"

    def test_run_changelog_tagged_only_head_tagged_highest(self, tmp_path):
        """HEAD is tagged, highest mode: HEAD entry shows computed release, no duplicate."""
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=["first", "second"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-2", 1)],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="tagged-only",
            changelog_use_highest_release_tag=True,
        )
        assert result["release-number"] == 3
        changelog = result["changelog"]
        assert len(changelog) == 2
        assert changelog[0]["release-complete"] == "3"
        assert changelog[1]["release-complete"] == "1"

    def test_run_changelog_tagged_only_untagged_head(self, tmp_path):
        """HEAD is untagged but still gets the top changelog entry."""
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=["tagged", "untagged head"],
            tags=[("fedora/f44/pkg-1.0-1", 0)],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="tagged-only",
        )
        changelog = result["changelog"]
        assert len(changelog) == 2
        assert "untagged head" in changelog[0]["commitlog"]
        assert changelog[0]["release-complete"] == "2"

    def test_run_accumulated_linear_all_tagged(self, tmp_path):
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=["first", "second", "third"],
            tags=[
                ("fedora/f44/pkg-1.0-1", 0),
                ("fedora/f44/pkg-1.0-2", 1),
                ("fedora/f44/pkg-1.0-3", 2),
            ],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        assert result["release-number"] == 4
        changelog = result["changelog"]
        # HEAD is the last tagged commit, so no separate "current" entry
        # End result: 3 entries, one per tag
        assert len(changelog) == 3
        assert changelog[0]["release-complete"] == "3"
        assert "third" in changelog[0]["commitlog"]
        assert changelog[2]["release-complete"] == "1"
        assert "first" in changelog[2]["commitlog"]

    def test_run_accumulated_untagged_commits_grouped(self, tmp_path):
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=["tagged v1", "fix a", "fix b", "tagged v2", "wip"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-2", 3)],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]
        a = "Test User"

        # Entry 0: HEAD (untagged) - single item
        assert changelog[0]["release-complete"] == "3"
        assert changelog[0]["commitlog"] == f"- wip ({a})"

        # Entry 1: tagged v2 + accumulated untagged commits
        assert changelog[1]["release-complete"] == "2"
        assert changelog[1]["commitlog"] == f"tagged v2 ({a})\n\n- fix b ({a})\n- fix a ({a})"

        # Entry 2: tagged v1 - single item
        assert changelog[2]["release-complete"] == "1"
        assert changelog[2]["commitlog"] == f"tagged v1 ({a})"

    def test_run_accumulated_format_head_tagged_with_untagged(self, tmp_path):
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=["base", "fix1", "fix2", "big release"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-2", 3)],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]
        a = "Test User"

        # HEAD is tagged: anchor + accumulated untagged commits
        assert changelog[0]["release-complete"] == "2"
        assert changelog[0]["commitlog"] == f"big release ({a})\n\n- fix2 ({a})\n- fix1 ({a})"

        # Base entry
        assert changelog[1]["release-complete"] == "1"
        assert changelog[1]["commitlog"] == f"base ({a})"

    def test_run_accumulated_multiline_commits_attributed(self, tmp_path):
        """Multiple untagged commits with multi-line messages attribute every line."""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        spec.write_text(
            "Name: pkg\nVersion: 1.0\nRelease: %autorelease\n"
            "Summary: t\n\nLicense: MIT\n\n%description\nT\n"
        )
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree = index.write_tree()

        # Tagged base commit
        sig_a = pygit2.Signature("Alice", "alice@example.com", time=1700000000)
        c0 = repo.create_commit(
            "HEAD", sig_a, sig_a, "Initial release\n\n- First package build", tree, []
        )
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c0)

        # Untagged multi-line commit by Bob
        sig_b = pygit2.Signature("Bob", "bob@example.com", time=1700000100)
        c1 = repo.create_commit(
            "HEAD",
            sig_b,
            sig_b,
            "Version 1.0.1\n\n- Fix CVE-2024-1234\n- Fix memory leak",
            tree,
            [c0],
        )

        # Untagged single-line commit by Alice
        sig_a2 = pygit2.Signature("Alice", "alice@example.com", time=1700000200)
        repo.create_commit(
            "HEAD",
            sig_a2,
            sig_a2,
            "Rebuild for new dep",
            tree,
            [c1],
        )

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]

        # Entry 0: HEAD (untagged) accumulates c2 + c1 into one entry
        assert changelog[0]["release-complete"] == "2"
        commitlog = changelog[0]["commitlog"]
        # Alice's single-line commit
        assert "- Rebuild for new dep (Alice)" in commitlog
        # Bob's multi-line commit: each body item attributed to Bob
        assert "- Version 1.0.1 (Bob)" in commitlog
        assert "- Fix CVE-2024-1234 (Bob)" in commitlog
        assert "- Fix memory leak (Bob)" in commitlog
        # Base entry
        assert "Initial release (Alice)" in changelog[1]["commitlog"]
        assert "- First package build (Alice)" in changelog[1]["commitlog"]

    def test_run_accumulated_head_multiline_splits_message(self, tmp_path):
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        spec.write_text(
            "Name: pkg\nVersion: 1.0\nRelease: %autorelease\n"
            "Summary: t\n\nLicense: MIT\n\n%description\nT\n"
        )
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree = index.write_tree()

        sig = pygit2.Signature("Alice", "alice@example.com", time=1700000000)
        c0 = repo.create_commit("HEAD", sig, sig, "base", tree, [])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c0)

        # HEAD with multi-line message
        sig2 = pygit2.Signature("Bob", "bob@example.com", time=1700000100)
        repo.create_commit(
            "HEAD",
            sig2,
            sig2,
            "Update to 1.1\n\n- Fix CVE-2024-9999\n- Resolves: rhbz#12345",
            tree,
            [c0],
        )

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]

        # HEAD entry: all items attributed to Bob
        commitlog = changelog[0]["commitlog"]
        assert "- Update to 1.1 (Bob)" in commitlog
        assert "- Fix CVE-2024-9999 (Bob)" in commitlog
        assert "- Resolves: rhbz#12345 (Bob)" in commitlog

    def test_run_accumulated_no_tags_first_build(self, tmp_path):
        """No tags, accumulated mode: single entry with all commit messages, release = base."""
        processor = self._processor(tmp_path, commits=["c0", "c1", "c2"])
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        assert result["release-number"] == 1
        changelog = result["changelog"]
        # accumulated with no tags: all history in one entry
        assert len(changelog) == 1
        assert changelog[0]["release-complete"] == "1"
        assert "c0" in changelog[0]["commitlog"]
        assert "c1" in changelog[0]["commitlog"]
        assert "c2" in changelog[0]["commitlog"]

    def test_run_accumulated_highest_mode_rebuild(self, tmp_path):
        """In highest mode, HEAD's entry uses the computed release (not existing tag)."""
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=["first", "second"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-2", 1)],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
            changelog_use_highest_release_tag=True,
        )
        assert result["release-number"] == 3
        changelog = result["changelog"]
        # HEAD is tagged as 2, but highest mode uses computed release 3
        assert changelog[0]["release-complete"] == "3"
        assert "second" in changelog[0]["commitlog"]
        # Previous entry uses its tag's release
        assert changelog[1]["release-complete"] == "1"

    def test_run_accumulated_unresolvable_merge_jumps_to_tag(self, tmp_path):
        # Divergent branch merge structure:
        # HEAD -> merge_commit (tree differs from both parents)
        #   parent1: commit on branch A (tagged)
        #   parent2: commit on branch B (tagged)
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        base_time = 1700000000

        # Create divergent branches
        # Common ancestor
        sig = pygit2.Signature("Test", "test@example.com", time=base_time)
        spec.write_text(_make_spec())
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree0 = index.write_tree()
        c0 = repo.create_commit("HEAD", sig, sig, "ancestor", tree0, [])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c0)

        # Branch A commit (different content)
        sig_a = pygit2.Signature("Test", "test@example.com", time=base_time + 100)
        spec.write_text(_make_spec(summary="branch A", desc="A"))
        index.add("pkg.spec")
        index.write()
        tree_a = index.write_tree()
        c_a = repo.create_commit(None, sig_a, sig_a, "branch A change", tree_a, [c0])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-2", c_a)

        # Branch B commit (different content again)
        sig_b = pygit2.Signature("Test", "test@example.com", time=base_time + 200)
        spec.write_text(_make_spec(summary="branch B", desc="B"))
        index.add("pkg.spec")
        index.write()
        tree_b = index.write_tree()
        c_b = repo.create_commit(None, sig_b, sig_b, "branch B change", tree_b, [c0])

        # Merge commit with unique tree (not matching either parent)
        sig_m = pygit2.Signature("Test", "test@example.com", time=base_time + 300)
        spec.write_text(_make_spec(summary="merged", desc="Merged"))
        index.add("pkg.spec")
        index.write()
        tree_m = index.write_tree()
        c_m = repo.create_commit(None, sig_m, sig_m, "merge commit", tree_m, [c_a, c_b])
        repo.set_head(c_m)

        # Verify trees are all different (unresolvable)
        assert tree_m != tree_a
        assert tree_m != tree_b

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]
        # Should have entries - the merge triggers a jump to the next older tag
        assert len(changelog) >= 2
        # The merge commit's message should be in the first entry
        assert "merge commit" in changelog[0]["commitlog"]
        # The ancestor's entry should exist
        messages = "\n".join(e["commitlog"] for e in changelog)
        assert "ancestor" in messages

    def test_run_accumulated_same_tree_merge_follows_parent(self, tmp_path):
        """On a merge, we want to try same-tree ('our') parent before tags"""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        base_time = 1700000000
        spec_content = _make_spec()

        # Commit A (ancestor)
        sig = pygit2.Signature("Test", "test@example.com", time=base_time)
        spec.write_text(spec_content)
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree0 = index.write_tree()
        c0 = repo.create_commit("HEAD", sig, sig, "ancestor", tree0, [])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c0)

        # Branch commit with different content
        sig_b = pygit2.Signature("Test", "test@example.com", time=base_time + 100)
        spec.write_text(spec_content + "\n# branch change\n")
        index.add("pkg.spec")
        index.write()
        tree_b = index.write_tree()
        c_b = repo.create_commit(None, sig_b, sig_b, "branch work", tree_b, [c0])

        # Merge commit with SAME tree as parent c_b (strategy "ours" equivalent)
        sig_m = pygit2.Signature("Test", "test@example.com", time=base_time + 200)
        c_m = repo.create_commit(None, sig_m, sig_m, "merge ours", tree_b, [c_b, c0])
        repo.set_head(c_m)
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-2", c_m)

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]
        # Should follow same-tree parent (c_b), accumulate its message
        assert len(changelog) >= 2
        messages = "\n".join(e["commitlog"] for e in changelog)
        assert "branch work" in messages
        assert "ancestor" in messages

    def test_run_accumulated_all_tags_visited_terminates(self, tmp_path):
        """When all tagged commits are visited and merge is unresolvable, walk ends."""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        base_time = 1700000000

        # Single tagged commit
        sig = pygit2.Signature("Test", "test@example.com", time=base_time)
        spec.write_text(_make_spec())
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree0 = index.write_tree()
        c0 = repo.create_commit("HEAD", sig, sig, "base", tree0, [])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c0)

        # Two divergent children
        sig_a = pygit2.Signature("Test", "test@example.com", time=base_time + 100)
        spec.write_text(_make_spec(summary="A", desc="A"))
        index.add("pkg.spec")
        index.write()
        tree_a = index.write_tree()
        c_a = repo.create_commit(None, sig_a, sig_a, "side A", tree_a, [c0])

        sig_b = pygit2.Signature("Test", "test@example.com", time=base_time + 200)
        spec.write_text(_make_spec(summary="B", desc="B"))
        index.add("pkg.spec")
        index.write()
        tree_b = index.write_tree()
        c_b = repo.create_commit(None, sig_b, sig_b, "side B", tree_b, [c0])

        # Unresolvable merge (tree differs from both parents)
        sig_m = pygit2.Signature("Test", "test@example.com", time=base_time + 300)
        spec.write_text(_make_spec(summary="M", desc="M"))
        index.add("pkg.spec")
        index.write()
        tree_m = index.write_tree()
        c_m = repo.create_commit(None, sig_m, sig_m, "unresolvable merge", tree_m, [c_a, c_b])
        repo.set_head(c_m)

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]
        # Walk hits merge, jumps to c0 (only tag), then c0 has no parents -> terminates
        # If merge is hit again somehow, all tags visited -> return None terminates
        assert len(changelog) >= 1
        messages = "\n".join(e["commitlog"] for e in changelog)
        assert "unresolvable merge" in messages

    def test_accumulated_tag_visited_before_merge_exhausts_jump(self, tmp_path):
        """Cycle guard: tag on mainline before merge was visited, don't revisit"""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        base_time = 1700000000

        def spec_v(v):
            return _make_spec(summary=v, desc=v)

        # Two divergent base commits (parents of the merge)
        sig0a = pygit2.Signature("Test", "test@example.com", time=base_time)
        spec.write_text(spec_v("side a"))
        index = repo.index
        index.add("pkg.spec")
        index.write()
        t_a = index.write_tree()
        c_a = repo.create_commit("HEAD", sig0a, sig0a, "side a", t_a, [])

        sig0b = pygit2.Signature("Test", "test@example.com", time=base_time + 50)
        spec.write_text(spec_v("side b"))
        index.add("pkg.spec")
        index.write()
        t_b = index.write_tree()
        c_b = repo.create_commit(None, sig0b, sig0b, "side b", t_b, [])

        # Unresolvable merge (tree differs from both parents)
        sig1 = pygit2.Signature("Test", "test@example.com", time=base_time + 100)
        spec.write_text(spec_v("merged"))
        index.add("pkg.spec")
        index.write()
        t_m = index.write_tree()
        c_m = repo.create_commit(None, sig1, sig1, "merge", t_m, [c_a, c_b])

        # Tagged commit AFTER the merge (on mainline, visited before merge is encountered)
        sig2 = pygit2.Signature("Test", "test@example.com", time=base_time + 200)
        spec.write_text(spec_v("tagged"))
        index.add("pkg.spec")
        index.write()
        t_tag = index.write_tree()
        c_tag = repo.create_commit(None, sig2, sig2, "tagged release", t_tag, [c_m])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c_tag)

        # HEAD after the tag
        sig3 = pygit2.Signature("Test", "test@example.com", time=base_time + 300)
        spec.write_text(spec_v("head"))
        index.add("pkg.spec")
        index.write()
        t_h = index.write_tree()
        c_h = repo.create_commit(None, sig3, sig3, "head commit", t_h, [c_tag])
        repo.set_head(c_h)

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        # Walk: head -> c_tag (tagged, visited) -> c_m (unresolvable merge)
        # Jump: only tag is c_tag, already visited -> return None -> walk ends
        # This hits line 882 (return None) and line 825 (break on revisit if jump returns visited)
        changelog = result["changelog"]
        assert len(changelog) >= 1
        messages = "\n".join(e["commitlog"] for e in changelog)
        assert "head commit" in messages
        assert "tagged release" in messages

    def test_accumulated_jump_skips_visited_tag(self, tmp_path):
        """Jump skips already-visited tags and lands on an older unvisited one."""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        base_time = 1700000000

        def spec_v(v):
            return _make_spec(summary=v, desc=v)

        # Common ancestor
        sig0 = pygit2.Signature("Test", "test@example.com", time=base_time)
        spec.write_text(spec_v("common"))
        index = repo.index
        index.add("pkg.spec")
        index.write()
        t0 = index.write_tree()
        c0 = repo.create_commit("HEAD", sig0, sig0, "common ancestor", t0, [])

        # Branch A: tagged commit with c0 as parent
        sig_a = pygit2.Signature("Test", "test@example.com", time=base_time + 100)
        spec.write_text(spec_v("branch a"))
        index.add("pkg.spec")
        index.write()
        t_a = index.write_tree()
        c_a = repo.create_commit(None, sig_a, sig_a, "branch a tagged", t_a, [c0])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c_a)

        # Branch B: different content, also from c0
        sig_b = pygit2.Signature("Test", "test@example.com", time=base_time + 150)
        spec.write_text(spec_v("branch b"))
        index.add("pkg.spec")
        index.write()
        t_b = index.write_tree()
        c_b = repo.create_commit(None, sig_b, sig_b, "branch b", t_b, [c0])

        # Unresolvable merge of c_a and c_b
        sig_m = pygit2.Signature("Test", "test@example.com", time=base_time + 200)
        spec.write_text(spec_v("merged"))
        index.add("pkg.spec")
        index.write()
        t_m = index.write_tree()
        c_m = repo.create_commit(None, sig_m, sig_m, "merge", t_m, [c_a, c_b])

        # Tagged commit after merge (visited before the merge during walk)
        sig2 = pygit2.Signature("Test", "test@example.com", time=base_time + 300)
        spec.write_text(spec_v("release 2"))
        index.add("pkg.spec")
        index.write()
        t2 = index.write_tree()
        c2 = repo.create_commit(None, sig2, sig2, "release 2", t2, [c_m])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-2", c2)

        # HEAD
        sig_h = pygit2.Signature("Test", "test@example.com", time=base_time + 400)
        spec.write_text(spec_v("head"))
        index.add("pkg.spec")
        index.write()
        t_h = index.write_tree()
        c_h = repo.create_commit(None, sig_h, sig_h, "head", t_h, [c2])
        repo.set_head(c_h)

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        # Walk: head -> c2 (tagged "2", visited) -> c_m (unresolvable merge)
        # Jump: c2 already visited, skip -> c_a (tagged "1", unvisited) -> walk c_a -> c0 -> done
        changelog = result["changelog"]
        assert len(changelog) >= 2
        messages = "\n".join(e["commitlog"] for e in changelog)
        assert "head" in messages
        assert "branch a tagged" in messages

    def test_run_accumulated_non_chronological_history(self, tmp_path):
        """rpmbuild requires changelog in chronological order, verify we sort"""
        # Out-of-order may happen due to cherry-pick or rebase prior to merge
        processor = self._processor(
            tmp_path,
            version="1.0",
            commits=[
                ("old commit rebased late", 1700000500),  # newer timestamp but first in history
                ("new commit rebased early", 1700000100),  # older timestamp but second
                ("middle", 1700000300),
            ],
            tags=[
                ("fedora/f44/pkg-1.0-1", 0),
                ("fedora/f44/pkg-1.0-2", 1),
                ("fedora/f44/pkg-1.0-3", 2),
            ],
        )
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]
        # Regardless of walk order, entries must be sorted by timestamp descending
        for i in range(len(changelog) - 1):
            assert changelog[i]["timestamp"] >= changelog[i + 1]["timestamp"]

    def test_run_accumulated_version_change_between_tags(self, tmp_path):
        """Tags with different versions produce entries with correct epoch-version."""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        base_time = 1700000000
        spec_t = _make_spec(version="{v}")

        sig0 = pygit2.Signature("Test", "test@example.com", time=base_time)
        spec.write_text(spec_t.format(v="1.0"))
        index = repo.index
        index.add("pkg.spec")
        index.write()
        t0 = index.write_tree()
        c0 = repo.create_commit("HEAD", sig0, sig0, "initial 1.0", t0, [])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c0)

        sig1 = pygit2.Signature("Test", "test@example.com", time=base_time + 100)
        spec.write_text(spec_t.format(v="1.0"))
        index.add("pkg.spec")
        index.write()
        t1 = index.write_tree()
        c1 = repo.create_commit("HEAD", sig1, sig1, "bugfix for 1.0", t1, [c0])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-2", c1)

        sig2 = pygit2.Signature("Test", "test@example.com", time=base_time + 200)
        spec.write_text(spec_t.format(v="2.0"))
        index.add("pkg.spec")
        index.write()
        t2 = index.write_tree()
        c2 = repo.create_commit("HEAD", sig2, sig2, "upgrade to 2.0", t2, [c1])
        repo.references.create("refs/tags/fedora/f44/pkg-2.0-1", c2)

        sig3 = pygit2.Signature("Test", "test@example.com", time=base_time + 300)
        spec.write_text(spec_t.format(v="2.0"))
        index.add("pkg.spec")
        index.write()
        t3 = index.write_tree()
        repo.create_commit("HEAD", sig3, sig3, "fix for 2.0", t3, [c2])

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        # Version changed: release resets. Current spec is 2.0, only one 2.0 tag -> release 2
        assert result["release-number"] == 2
        changelog = result["changelog"]
        # Entries should have correct versions
        versions = [e["epoch-version"] for e in changelog]
        assert "2.0" in versions
        assert "1.0" in versions
        # 2.0 entries come first (newer)
        v2_entries = [e for e in changelog if e["epoch-version"] == "2.0"]
        v1_entries = [e for e in changelog if e["epoch-version"] == "1.0"]
        assert v2_entries[0]["timestamp"] > v1_entries[0]["timestamp"]

    def test_namespaced_tag(self, tmp_path):
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        spec.write_text(
            "Name: pkg\nVersion: 1.0\nRelease: %autorelease\n"
            "Summary: t\n\nLicense: MIT\n\n%description\nT\n"
        )
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree = index.write_tree()
        sig = pygit2.Signature("Test", "test@example.com", time=1700000000)
        c0 = repo.create_commit("HEAD", sig, sig, "initial", tree, [])
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-1", c0)

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor],
            git_tag_namespace="fedora/f44",
        )
        assert result["release-number"] == 2

    def test_dirty_worktree_with_tags(self, tmp_path):
        """Dirty worktree doesn't affect tag-based release (tags count builds, not commits)."""
        repo_path, _ = create_tagged_repo(
            tmp_path, version="1.0", tags=[("fedora/f44/pkg-1.0-2", 0)]
        )
        spec = repo_path / "pkg.spec"
        spec.write_text(spec.read_text() + "\n# modified\n")
        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor], git_tag_namespace="fedora/f44"
        )
        # max tag is 2, next build is 3 — same whether worktree is clean or dirty
        assert result["release-number"] == 3

    def test_epoch_no_epoch_tag_does_not_match(self, tmp_path):
        """Spec has epoch, tag without epoch encoding should not match."""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        spec.write_text(
            "Epoch: 2\nName: pkg\nVersion: 1.0\nRelease: %autorelease\n"
            "Summary: t\n\nLicense: MIT\n\n%description\nT\n"
        )
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree = index.write_tree()
        sig = pygit2.Signature("Test", "test@example.com", time=1700000000)
        c0 = repo.create_commit("HEAD", sig, sig, "initial", tree, [])

        # Tag without epoch: "1.0" won't match "2:1.0"
        repo.references.create("refs/tags/fedora/f44/pkg-1.0-5", c0)

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor], git_tag_namespace="fedora/f44"
        )
        assert result["release-number"] == 1

    def test_epoch_encoded_tag_matches(self, tmp_path):
        """Spec has epoch, tag with epoch encoding (!) should match."""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        spec.write_text(
            "Epoch: 2\nName: pkg\nVersion: 1.0\nRelease: %autorelease\n"
            "Summary: t\n\nLicense: MIT\n\n%description\nT\n"
        )
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree = index.write_tree()
        sig = pygit2.Signature("Test", "test@example.com", time=1700000000)
        c0 = repo.create_commit("HEAD", sig, sig, "initial", tree, [])

        # Tag with epoch encoded: "2_1.0" → decoded as "2:1.0" → matches
        repo.references.create("refs/tags/fedora/f44/2!pkg-1.0-3", c0)

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor], git_tag_namespace="fedora/f44"
        )
        assert result["release-number"] == 4

    def test_epoch_change_resets_release(self, tmp_path):
        """Epoch bump with same version: old epoch tags don't match, release resets."""
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        # Current spec has Epoch: 2
        spec = repo_path / "pkg.spec"
        spec.write_text(
            "Epoch: 2\nName: pkg\nVersion: 1.0\nRelease: %autorelease\n"
            "Summary: t\n\nLicense: MIT\n\n%description\nT\n"
        )
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree = index.write_tree()
        sig = pygit2.Signature("Test", "test@example.com", time=1700000000)
        c0 = repo.create_commit("HEAD", sig, sig, "initial", tree, [])

        # Old tags from epoch 1 era: "1_1.0" → decoded as "1:1.0"
        repo.references.create("refs/tags/fedora/f44/1!pkg-1.0-7", c0)

        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor], git_tag_namespace="fedora/f44"
        )
        # "1:1.0" != "2:1.0" → no match → reset to base
        assert result["release-number"] == 1

    def test_missing_specfile_with_tags(self, tmp_path):
        """Spec deleted from worktree after init: tag path can't parse spec, falls through."""
        repo_path, _ = create_tagged_repo(
            tmp_path, version="1.0", tags=[("fedora/f44/pkg-1.0-1", 0)]
        )
        processor = pkg_history.PkgHistoryProcessor(repo_path)
        # Delete spec after init (simulates dirty worktree with deleted file)
        spec = repo_path / "pkg.spec"
        spec.unlink()
        result = processor.run(
            visitors=[processor.release_number_visitor], git_tag_namespace="fedora/f44"
        )
        # Can't parse spec → _release_from_tags returns None → falls through to walk
        assert "release-number" in result

    # What follows is deeper testing of tag-handling on "unresolvable" merge scenarios

    def _make_divergent_merges_repo(self, tmp_path):
        """Create a repo with multiple unresolvable merges from a divergent branch.

        This is based on merges from rawhide that have hit the "unresolvable" exit.
        (in particular, this is adapated from mesa circa Version 26 on f44)

        Topology:
            HEAD  "Drop included patches"     (untagged, Version: 3.0)
            c5    "Update to 3.0"             (untagged, Version: 3.0)
            c4    "Backport fix"              [tagged f44-pkg-2.5-3] (Version: 2.5)
            M1    Merge (unresolvable)
            c3    "Cherry-pick fix"           [tagged f44-pkg-2.0-4] (Version: 2.0)
            M2    Merge (unresolvable)
            c1    "Rebuild for dep"           [tagged f44-pkg-1.6-2] (Version: 1.6)
            c0    "Update to 1.6"            [tagged f44-pkg-1.6-1] (Version: 1.6)

        Merged, divergent commits (i.e. merges from rawhide):
            r2    "Update to 2.5" (different tree)
            r1    "Update to 2.0" (different tree)
        """
        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = pygit2.init_repository(str(repo_path))

        spec = repo_path / "pkg.spec"
        base_time = 1700000000
        spec_t = _make_spec(version="{v}", desc="{d}")

        def commit(msg, version, desc, parents, time_offset, tag=None):
            sig = pygit2.Signature("Test", "test@example.com", time=base_time + time_offset)
            spec.write_text(spec_t.format(v=version, d=desc))
            index = repo.index
            index.add("pkg.spec")
            index.write()
            tree = index.write_tree()
            ref = "HEAD" if not parents else None
            oid = repo.create_commit(ref, sig, sig, msg, tree, parents)
            if tag:
                repo.references.create(f"refs/tags/{tag}", oid)
            return oid

        # c0: initial tagged release
        c0 = commit("Update to 1.6", "1.6", "v1.6", [], 0, tag="fedora/f44/pkg-1.6-1")

        # c1: rebuild on f44 side
        c1 = commit("Rebuild for dep", "1.6", "v1.6 rebuild", [c0], 100, tag="fedora/f44/pkg-1.6-2")

        # r1: rawhide diverges with different content
        r1 = commit("Update to 2.0", "2.0", "rawhide 2.0", [c0], 150)

        # M2: unresolvable merge (tree differs from both parents)
        sig = pygit2.Signature("Test", "test@example.com", time=base_time + 200)
        spec.write_text(spec_t.format(v="2.0", d="merged 2.0"))
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree_m2 = index.write_tree()
        m2 = repo.create_commit(None, sig, sig, "Merge rawhide into f44", tree_m2, [c1, r1])

        # c3: cherry-pick on f44 after merge
        c3 = commit(
            "Cherry-pick fix", "2.0", "v2.0 cherry-pick", [m2], 300, tag="fedora/f44/pkg-2.0-4"
        )

        # r2: rawhide diverges again
        r2 = commit("Update to 2.5", "2.5", "rawhide 2.5", [r1], 350)

        # M1: second unresolvable merge
        sig = pygit2.Signature("Test", "test@example.com", time=base_time + 400)
        spec.write_text(spec_t.format(v="2.5", d="merged 2.5"))
        index = repo.index
        index.add("pkg.spec")
        index.write()
        tree_m1 = index.write_tree()
        m1 = repo.create_commit(None, sig, sig, "Merge rawhide into f44", tree_m1, [c3, r2])

        # c4: tagged commit after second merge
        c4 = commit("Backport fix", "2.5", "v2.5 backport", [m1], 500, tag="fedora/f44/pkg-2.5-3")

        # c5: untagged version bump
        c5 = commit("Update to 3.0", "3.0", "v3.0 update", [c4], 600)

        # HEAD: untagged, about to be built
        head = commit("Drop included patches", "3.0", "v3.0 final", [c5], 700)
        repo.set_head(head)

        return repo_path

    def test_divergent_merges_release_from_tags(self, tmp_path):
        """Version with no matching tags resets to base release."""
        repo_path = self._make_divergent_merges_repo(tmp_path)
        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor],
            git_tag_namespace="fedora/f44",
        )
        # Version 3.0 has no matching tags, so release resets to base
        assert result["release-number"] == 1

    def test_divergent_merges_accumulated_changelog(self, tmp_path):
        """Accumulated mode jumps past unresolvable merges, groups commits correctly."""
        repo_path = self._make_divergent_merges_repo(tmp_path)
        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="accumulated",
        )
        changelog = result["changelog"]
        assert len(changelog) == 5

        # Entry 0: HEAD (untagged, about to be built as 3.0-1)
        # Includes the untagged "Update to 3.0" commit accumulated with HEAD
        assert changelog[0]["epoch-version"] == "3.0"
        assert changelog[0]["release-complete"] == "1"
        assert "Drop included patches" in changelog[0]["commitlog"]
        assert "Update to 3.0" in changelog[0]["commitlog"]
        assert "(Test)" in changelog[0]["commitlog"]

        # Entry 1: tagged 2.5-3 — "Backport fix" plus the merge commit message
        # (merge is on mainline, its message is part of this build's work)
        assert changelog[1]["epoch-version"] == "2.5"
        assert changelog[1]["release-complete"] == "3"
        assert "Backport fix" in changelog[1]["commitlog"]
        assert "Merge" in changelog[1]["commitlog"]

        # Entry 2: tagged 2.0-4 — "Cherry-pick fix" plus its merge
        assert changelog[2]["epoch-version"] == "2.0"
        assert changelog[2]["release-complete"] == "4"
        assert "Cherry-pick fix" in changelog[2]["commitlog"]

        # Entry 3: tagged 1.6-2
        assert changelog[3]["epoch-version"] == "1.6"
        assert changelog[3]["release-complete"] == "2"
        assert "Rebuild for dep" in changelog[3]["commitlog"]

        # Entry 4: tagged 1.6-1
        assert changelog[4]["epoch-version"] == "1.6"
        assert changelog[4]["release-complete"] == "1"
        assert "Update to 1.6" in changelog[4]["commitlog"]

        # Rawhide-only commits never appear
        # (i.e., divergent branching does not pollute the changelog)
        all_messages = "\n".join(e["commitlog"] for e in changelog)
        assert "Update to 2.5" not in all_messages
        assert "Update to 2.0" not in all_messages

        # Chronological order
        for i in range(len(changelog) - 1):
            assert changelog[i]["timestamp"] >= changelog[i + 1]["timestamp"]

    def test_divergent_merges_tagged_only_changelog(self, tmp_path):
        """Tagged-only mode produces one entry per tagged commit plus HEAD."""
        repo_path = self._make_divergent_merges_repo(tmp_path)
        processor = pkg_history.PkgHistoryProcessor(repo_path)
        result = processor.run(
            visitors=[processor.release_number_visitor, processor.changelog_visitor],
            git_tag_namespace="fedora/f44",
            changelog_mode="tagged-only",
        )
        changelog = result["changelog"]
        assert len(changelog) == 5

        # Entry 0: HEAD (about to be built as 3.0-1) — only HEAD's own message
        assert changelog[0]["epoch-version"] == "3.0"
        assert changelog[0]["release-complete"] == "1"
        assert changelog[0]["commitlog"] == "Drop included patches"

        # Entry 1: tagged 2.5-3
        assert changelog[1]["epoch-version"] == "2.5"
        assert changelog[1]["release-complete"] == "3"
        assert changelog[1]["commitlog"] == "Backport fix"

        # Entry 2: tagged 2.0-4
        assert changelog[2]["epoch-version"] == "2.0"
        assert changelog[2]["release-complete"] == "4"
        assert changelog[2]["commitlog"] == "Cherry-pick fix"

        # Entry 3: tagged 1.6-2
        assert changelog[3]["epoch-version"] == "1.6"
        assert changelog[3]["release-complete"] == "2"
        assert changelog[3]["commitlog"] == "Rebuild for dep"

        # Entry 4: tagged 1.6-1
        assert changelog[4]["epoch-version"] == "1.6"
        assert changelog[4]["release-complete"] == "1"
        assert changelog[4]["commitlog"] == "Update to 1.6"

        # No rawhide-side commit messages
        all_messages = "\n".join(e["commitlog"] for e in changelog)
        assert "Update to 2.5" not in all_messages
        assert "Update to 2.0" not in all_messages

    def test_skip_changelog_tagged_only(self, tmp_path):
        """Tagged commits always appear in tagged-only mode regardless of [skip changelog]."""
        processor = self._processor(
            tmp_path,
            commits=["Initial build", "[skip changelog]\nMass rebuild"],
            tags=[("fedora/f44/pkg-1.0-1", 0), ("fedora/f44/pkg-1.0-2", 1)],
        )
        result = processor._changelog_from_tags("fedora/f44")
        # Both releases have entries — they were shipped
        assert len(result) == 2

    def test_skip_changelog_accumulated_untagged(self, tmp_path):
        """[skip changelog] on untagged non-HEAD commits excludes them from accumulated mode."""
        processor = self._processor(
            tmp_path,
            commits=["Initial build", "[skip changelog]\nMass rebuild", "Fix bug"],
            tags=[("fedora/f44/pkg-1.0-1", 0)],
        )
        verflags = {"epoch-version": "1.0", "base": "1"}
        result = processor._changelog_accumulated(
            "fedora/f44", processor.repo.head.peel(), verflags, tag_release=2
        )
        all_messages = "\n".join(e["commitlog"] for e in result)
        assert "Mass rebuild" not in all_messages
        assert "Fix bug" in all_messages

    def test_visited_single_parent_falls_through_to_jump(self, tmp_path):
        """Single-parent commit whose parent is visited falls through to jump."""
        # To hit line 920->933: _next_commit_for_walk is called on commit C
        # where C has 1 parent that's already in visited.
        #
        # DAG: root <- A(tag) <- B(merge of A+X, unresolvable) <- HEAD (child of B)
        #        \
        #         C(tag, single parent=root)
        #
        # X is untagged with different tree than A.
        #
        # Walk: HEAD -> B (single parent, not visited -> follow)
        #   -> B is processed. _next(B): merge, trees differ from both parents -> jump
        #   -> jump to A (highest time unvisited tag). Process A.
        #   -> _next(A): single parent=root, not visited -> follow root. Process root.
        #   -> _next(root): no parents -> return None? NO, need root to have parents.
        #
        # Revised: need _next to jump to C. For that, the commit must fall through
        # to the jump loop. The simplest trigger: a multi-parent commit where no
        # same-tree unvisited parent exists.
        #
        # Final approach: use _next_commit_for_walk directly in unit test.
        import pygit2 as _pygit2

        repo_path = tmp_path / "pkg"
        repo_path.mkdir()
        repo = _pygit2.init_repository(str(repo_path))
        spec = repo_path / "pkg.spec"
        base_time = 1700000000

        def make(msg, parents, time, content):
            spec.write_text(
                f"Name: pkg\nVersion: 1.0\nRelease: %autorelease\n"
                f"Summary: T\nLicense: MIT\n\n%description\n{content}\n"
            )
            repo.index.add("pkg.spec")
            repo.index.write()
            tree = repo.index.write_tree()
            sig = _pygit2.Signature("T", "t@e.com", time=time)
            return repo.create_commit(None, sig, sig, msg, tree, parents)

        root = make("root", [], base_time, "r")
        c = make("Side C", [root], base_time + 100, "c")

        # Create a tag for C
        repo.create_reference("refs/tags/fedora/f44/pkg-1.0-1", c)

        processor = pkg_history.PkgHistoryProcessor(repo_path)

        # Simulate: visited already contains root, tagged_by_time = [str(c)]
        visited = {str(root)}
        tagged_by_time = [str(c)]

        commit_c = repo.get(c)
        # _next_commit_for_walk(C): C has 1 parent (root), root IS in visited
        # -> should fall through to jump, find no unvisited tags (C itself is
        #    in tagged_by_time but we add it to visited first)
        visited.add(str(c))
        result = processor._next_commit_for_walk(commit_c, visited, tagged_by_time)

        # C's parent (root) is visited, no unvisited tags remain -> None
        assert result is None

    def test_release_from_tags_prerelease_extraver(self, tmp_path):
        """%autorelease -p -e rc1 composes correctly in tag mode."""
        processor = self._processor(
            tmp_path,
            version="1.0",
            tags=[("fedora/f44/pkg-1.0-2", 0)],
            autorelease_opts="-p -e rc1",
        )
        result = processor._run_tagged(
            processor.repo.head.peel(),
            git_tag_namespace="fedora/f44",
        )
        # tag_release = 3 (max 2 + 1), composed with prerelease + extraver:
        # "0." prefix (prerelease) + "3" (release 3 + base 1 - 1) + ".rc1" (extraver)
        assert result["release-complete"] == "0.3.rc1"
