import difflib
import os
import re
import tempfile
from contextlib import nullcontext
from pathlib import Path
from subprocess import check_output, run
from unittest import mock

import pytest

from rpmautospec.exc import SpecParseFailure
from rpmautospec.subcommands import process_distgit
from rpmautospec.version import __version__

from ...common import gen_testrepo

__HERE__ = Path(__file__).parent


def _generate_branch_testcase_combinations():
    """Pre-generate valid combinations to avoid cluttering pytest output.

    Only run fuzzing tests on the Rawhide branch because merge
    commits (which it doesn't have) make them fail."""
    valid_combinations = [
        (branch, autorelease_case, autochangelog_case, remove_changelog_file, is_processed)
        for branch in ("rawhide", "epel8")
        for autorelease_case in ("unchanged", "with braces", "optional", "manual", "broken")
        for autochangelog_case in (
            "unchanged",
            "changelog case insensitive",
            "changelog trailing garbage",
            "line in between",
            "trailing line",
            "with braces",
            "missing",
            "optional",
            "manual",
            "nochangelog",
        )
        for remove_changelog_file in (False, True)
        for is_processed in (False, True)
        if branch == "rawhide"
        or autorelease_case == "unchanged"
        and autochangelog_case == "unchanged"
        and not remove_changelog_file
    ]
    return valid_combinations


autorelease_autochangelog_cases = [
    (autorelease_case, autochangelog_case)
    for autorelease_case in ("unchanged", "with braces", "optional", "manual", "broken")
    for autochangelog_case in (
        "unchanged",
        "changelog case insensitive",
        "changelog trailing garbage",
        "line in between",
        "trailing line",
        "with braces",
        "missing",
        "optional",
        "manual",
        "nochangelog",
    )
]

relnum_re = re.compile("^(?P<relnum>[0-9]+)(?P<rest>.*)$")


def relnum_split(release):
    match = relnum_re.match(release)
    # let this fail if the regex doesn't match
    return int(match.group("relnum")), match.group("rest")


def fuzz_spec_file(
    spec_file_path: Path,
    autorelease_case: str,
    autochangelog_case: str,
    remove_changelog_file: bool,
    is_processed: bool,
):
    """Fuzz a spec file in ways which (often) shouldn't change the outcome"""
    new_spec_file_path = spec_file_path.with_name(spec_file_path.name + ".new")
    with (
        spec_file_path.open("r", encoding="utf-8") as orig,
        new_spec_file_path.open("w", encoding="utf-8") as new,
    ):
        if is_processed:
            autorelease_blurb = process_distgit.AUTORELEASE_TEMPLATE.format(autorelease_number=15)
            print(
                process_distgit.RPMAUTOSPEC_TEMPLATE.format(
                    version=__version__,
                    used_features="autorelease, autochangelog",
                    autorelease_blurb_if_needed=autorelease_blurb,
                ),
                file=new,
            )

        encountered_first_after_conversion = False
        for line in orig:
            if remove_changelog_file and encountered_first_after_conversion:
                break
            if line.startswith("Release:") and autorelease_case != "unchanged":
                if autorelease_case == "with braces":
                    print("Release:        %{autorelease}", file=new)
                elif autorelease_case == "optional":
                    print("Release:        %{?autorelease}", file=new)
                elif autorelease_case == "manual":
                    print("Release:        1", file=new)
                elif autorelease_case == "broken":
                    # So you expected a release line? Hahahaha!
                    print("Version:        %autorelease", file=new)
                else:
                    raise ValueError(f"Unknown autorelease_case: {autorelease_case}")
            elif line.strip() == "%changelog" and autochangelog_case != "unchanged":
                if autochangelog_case == "changelog case insensitive":
                    print("%ChAnGeLoG", file=new)
                elif autochangelog_case == "changelog trailing garbage":
                    print("%changelog with trailing garbage yes this works", file=new)
                elif autochangelog_case == "line in between":
                    print("%changelog\n\n%autochangelog", file=new)
                    break
                elif autochangelog_case == "trailing line":
                    print("%changelog\n%autochangelog\n", file=new)
                    break
                elif autochangelog_case == "with braces":
                    print("%changelog\n%{autochangelog}", file=new)
                    break
                elif autochangelog_case == "missing":
                    # do nothing, i.e. don't print a %changelog to file
                    break
                elif autochangelog_case == "optional":
                    print("%changelog\n%{?autochangelog}", file=new)
                    break
                elif autochangelog_case == "manual":
                    print(
                        "%changelog\n"
                        + "* Wed Jan 24 2024 Jabberwocky <jabber@wocky.not.wookie> 0-1\n"
                        + "- Burble.\n",
                        file=new,
                    )
                    break
                elif autochangelog_case == "nochangelog":
                    print("%autochangelog", file=new)
                    break
                else:
                    raise ValueError(f"Unknown autochangelog_case: {autochangelog_case}")
            else:
                if line == "- Honour the tradition of antiquated encodings!\n":
                    encountered_first_after_conversion = True
                print(line, file=new, end="")

    new_spec_file_path.replace(spec_file_path)


def run_git_amend(worktree_dir):
    # Ensure worktree doesn't differ
    commit_timestamp = check_output(
        ["git", "log", "-1", "--pretty=format:%cI"],
        cwd=worktree_dir,
        encoding="ascii",
    ).strip()
    # Set name and email explicitly so CI doesn't trip over them being unset.
    env = os.environ | {
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "<test@example.com>",
        "GIT_COMMITTER_DATE": commit_timestamp,
    }
    run(
        ["git", "commit", "--all", "--allow-empty", "--amend", "--no-edit"],
        cwd=worktree_dir,
        env=env,
    )


@pytest.mark.parametrize(
    "override_locale", (False, "C", "de_DE.UTF-8"), ids=("locale-unset", "locale-C", "locale-de")
)
@pytest.mark.parametrize(
    "overwrite_specfile",
    (False, True),
    ids=("without-overwrite-specfile", "with-overwrite-specfile"),
)
@pytest.mark.parametrize("dirty_worktree", (False, True), ids=("clean-worktree", "dirty-worktree"))
@pytest.mark.parametrize("bump_release", (0, 15), ids=("without-bump-release", "with-bump-release"))
@pytest.mark.parametrize(
    "branch, autorelease_case, autochangelog_case, remove_changelog_file, is_processed",
    _generate_branch_testcase_combinations(),
)
def test_do_process_distgit(
    override_locale,
    overwrite_specfile,
    branch,
    dirty_worktree,
    autorelease_case,
    autochangelog_case,
    remove_changelog_file,
    is_processed,
    bump_release,
    locale,
    tmp_path,
):
    """Test the do_process_distgit() function"""
    if override_locale:
        locale.setlocale(locale.LC_ALL, override_locale)

    unpacked_repo_dir, test_spec_file_path = gen_testrepo(tmp_path, branch)

    if bump_release:
        commit_timestamp = check_output(
            ["git", "log", "-1", "--pretty=format:%cI"],
            cwd=unpacked_repo_dir,
            encoding="ascii",
        ).strip()
        # Set name and email explicitly so CI doesn't trip over them being unset.
        env = os.environ | {
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "<test@example.com>",
            "GIT_COMMITTER_DATE": commit_timestamp,
        }
        latest_commit_log = check_output(
            ["git", "log", "-1", "--pretty=format:%B"],
            cwd=unpacked_repo_dir,
            encoding="utf-8",
        )
        amended_commit_log = latest_commit_log + f"\n\n[bump release: {bump_release}]\n"
        run(
            ["git", "commit", "--amend", "--no-edit", "-m", amended_commit_log],
            cwd=unpacked_repo_dir,
            env=env,
        )

    if autorelease_case != "unchanged" or autochangelog_case != "unchanged" or is_processed:
        fuzz_spec_file(
            test_spec_file_path,
            autorelease_case,
            autochangelog_case,
            remove_changelog_file,
            is_processed,
        )

    if remove_changelog_file:
        (unpacked_repo_dir / "changelog").unlink()

    if (
        autorelease_case != "unchanged"
        or autochangelog_case != "unchanged"
        or remove_changelog_file
    ) and not dirty_worktree:
        run_git_amend(unpacked_repo_dir)

    if overwrite_specfile:
        target_spec_file_path = None
    else:
        target_spec_file_path = tmp_path / "test-this-specfile-please.spec"

    orig_test_spec_file_stat = test_spec_file_path.stat()

    if autorelease_case == "broken" and not is_processed:
        catch_exception = pytest.raises(
            SpecParseFailure, match=rf"Couldn’t parse spec file {test_spec_file_path.name}"
        )
    else:
        catch_exception = nullcontext()

    # Set restrictive umask to check that file mode is preserved.
    old_umask = os.umask(0o077)
    real_cls = process_distgit.PkgHistoryProcessor
    processor_run = None
    with mock.patch(
        "rpmautospec.subcommands.process_distgit.PkgHistoryProcessor",
    ) as processor_cls:

        def wrap_cls(*args, **kwargs):
            nonlocal processor_run
            obj = real_cls(*args, **kwargs)
            processor_run = obj.run = mock.Mock(wraps=obj.run)
            return obj

        processor_cls.side_effect = wrap_cls
        with catch_exception as excinfo:
            retval = process_distgit.do_process_distgit(
                unpacked_repo_dir, target_spec_file_path, enable_caching=False
            )

        if excinfo:
            return
    # And restore previous umask.
    os.umask(old_umask)

    if is_processed or autorelease_case == "manual" and autochangelog_case == "manual":
        # No processing should be done if the spec file was processed before already, or doesn’t
        # need processing.
        assert not retval
        processor_run.assert_not_called()
        return

    # Input spec file was not processed before, should have been processed now.
    assert retval is not False
    processor_run.assert_called()

    test_spec_file_stat = os.stat(test_spec_file_path)
    attrs = ["mode", "ino", "dev", "uid", "gid"]
    if not overwrite_specfile:
        attrs.extend(["size", "mtime", "ctime"])

    for attr in attrs:
        assert getattr(test_spec_file_stat, "st_" + attr) == getattr(
            orig_test_spec_file_stat, "st_" + attr
        )

    expected_spec_file_path = (
        __HERE__.parent.parent
        / "test-data"
        / "repodata"
        / "dummy-test-package-gloster.spec.expected"
    )

    with (
        tempfile.NamedTemporaryFile(mode="w+", encoding="utf8") as tmpspec,
        open(expected_spec_file_path, "r", encoding="utf-8") as expspec,
    ):
        # Copy expected spec file and potentially bump release number
        relnum_seen = None
        relnumdef_re = re.compile(
            r"(?P<prefix>^\s*release_number\s*=\s*)(?P<relnum>\d+)(?P<suffix>.*)$"
        )
        for line in expspec:
            if match := relnumdef_re.match(line):
                relnum_seen = int(match.group("relnum"))
                if bump_release > relnum_seen:
                    print(
                        match.group("prefix") + str(bump_release) + match.group("suffix"),
                        file=tmpspec,
                    )
                    expected_spec_file_path = Path(tmpspec.name)
                    continue
            tmpspec.write(line)
        tmpspec.flush()

        if (
            autorelease_case != "unchanged"
            or autochangelog_case != "unchanged"
            or remove_changelog_file
        ):
            if autochangelog_case not in (
                "changelog case insensitive",
                "changelog trailing garbage",
                "manual",
            ):
                # "%changelog", "%ChAnGeLoG", ... stay verbatim, trick fuzz_spec_file() to
                # leave the rest of the cases as is, the %autorelease macro is expanded.
                fuzz_autochangelog_case = "unchanged"
            else:
                fuzz_autochangelog_case = autochangelog_case
            expected_spec_file_path = Path(tmpspec.name)
            fuzz_spec_file(
                expected_spec_file_path,
                autorelease_case,
                fuzz_autochangelog_case,
                remove_changelog_file,
                is_processed,
            )

        rpm_cmd = [
            "rpm",
            "--define",
            "dist .fc32",
            "--define",
            "_changelog_trimage 0",
            "--define",
            "_changelog_trimtime 0",
            "--specfile",
        ]

        if target_spec_file_path:
            test_cmd = rpm_cmd + [target_spec_file_path]
        else:
            test_cmd = rpm_cmd + [test_spec_file_path]
        expected_cmd = rpm_cmd + [expected_spec_file_path]
        if branch == "epel8":
            expected_cmd += ["--define", "latest_changelog_is_historical 1"]

        q_release = ["--qf", "%{release}\n"]
        test_output = check_output(test_cmd + q_release, encoding="utf-8").strip()
        test_relnum, test_rest = relnum_split(test_output)
        expected_output = check_output(expected_cmd + q_release, encoding="utf-8").strip()
        expected_relnum, expected_rest = relnum_split(expected_output)

        if autorelease_case == "manual":
            expected_relnum = 1

        if (
            dirty_worktree
            and autorelease_case != "manual"
            and (
                autorelease_case != "unchanged"
                or autochangelog_case != "unchanged"
                or remove_changelog_file
            )
        ):
            expected_relnum += 1

        if branch == "epel8" and not bump_release:
            expected_relnum += 1

        if autorelease_case != "manual":
            expected_relnum = max(expected_relnum, bump_release)

        assert test_relnum == expected_relnum

        assert test_rest == expected_rest

        q_changelog = ["--changelog"]
        test_output = check_output(test_cmd + q_changelog, encoding="utf-8")
        expected_output = check_output(expected_cmd + q_changelog, encoding="utf-8")

        if (
            dirty_worktree
            and autochangelog_case != "manual"
            and (
                autorelease_case != "unchanged"
                or autochangelog_case != "unchanged"
                or remove_changelog_file
            )
        ):
            diff = list(difflib.ndiff(expected_output.splitlines(), test_output.splitlines()))
            if autorelease_case != "manual":
                # verify entry for uncommitted changes
                assert all(line.startswith("+ ") for line in diff[:3])
                assert diff[0].endswith(f"-{expected_relnum}")

            diffoffset = 0 if autochangelog_case != "manual" else 2

            assert diff[diffoffset + 1] == "+ - Uncommitted changes"
            assert diff[diffoffset + 2] == "+ "

            # verify the rest is the expected changelog
            assert all(line.startswith("  ") for line in diff[diffoffset + 3 :])

            expected_output_offset = 0 if autochangelog_case != "manual" else 3
            assert expected_output.splitlines()[expected_output_offset:] == [
                line[2:] for line in diff[diffoffset + 3 :]
            ]
        else:
            assert test_output == expected_output
