import difflib
import os
import re
import shutil
import tarfile
import tempfile
from subprocess import check_output, run

import pytest

from rpmautospec.subcommands import process_distgit

from .. import temporary_cd

__here__ = os.path.dirname(__file__)


def _generate_branch_testcase_combinations():
    """Pre-generate valid combinations to avoid cluttering pytest output.

    Only run fuzzing tests on the Rawhide branch because merge
    commits (which it doesn't have) make them fail."""
    valid_combinations = [
        (branch, autorelease_case, autochangelog_case, remove_changelog_file)
        for branch in ("rawhide", "epel8")
        for autorelease_case in ("unchanged", "with braces", "optional")
        for autochangelog_case in (
            "unchanged",
            "changelog case insensitive",
            "changelog trailing garbage",
            "line in between",
            "trailing line",
            "with braces",
            "missing",
            "optional",
        )
        for remove_changelog_file in (False, True)
        if branch == "rawhide"
        or autorelease_case == "unchanged"
        and autochangelog_case == "unchanged"
        and not remove_changelog_file
    ]
    return valid_combinations


autorelease_autochangelog_cases = [
    (autorelease_case, autochangelog_case)
    for autorelease_case in ("unchanged", "with braces", "optional")
    for autochangelog_case in (
        "unchanged",
        "changelog case insensitive",
        "changelog trailing garbage",
        "line in between",
        "trailing line",
        "with braces",
        "missing",
        "optional",
    )
]

relnum_re = re.compile("^(?P<relnum>[0-9]+)(?P<rest>.*)$")


def relnum_split(release):
    match = relnum_re.match(release)
    # let this fail if the regex doesn't match
    return int(match.group("relnum")), match.group("rest")


def fuzz_spec_file(spec_file_path, autorelease_case, autochangelog_case, remove_changelog_file):
    """Fuzz a spec file in ways which (often) shouldn't change the outcome"""

    with open(spec_file_path, "r") as orig, open(spec_file_path + ".new", "w") as new:
        encountered_first_after_conversion = False
        for line in orig:
            if remove_changelog_file and encountered_first_after_conversion:
                break
            if line.startswith("Release:") and autorelease_case != "unchanged":
                if autorelease_case == "with braces":
                    print("Release:        %{autorelease}", file=new)
                elif autorelease_case == "optional":
                    print("Release:        %{?autorelease}", file=new)
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
                else:
                    raise ValueError(f"Unknown autochangelog_case: {autochangelog_case}")
            else:
                if line == "- Honour the tradition of antiquated encodings!\n":
                    encountered_first_after_conversion = True
                print(line, file=new, end="")

    os.rename(spec_file_path + ".new", spec_file_path)


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


@pytest.mark.parametrize("overwrite_specfile", (False, True))
@pytest.mark.parametrize("dirty_worktree", (False, True))
@pytest.mark.parametrize(
    "branch, autorelease_case, autochangelog_case, remove_changelog_file",
    _generate_branch_testcase_combinations(),
)
def test_process_distgit(
    tmp_path,
    overwrite_specfile,
    branch,
    dirty_worktree,
    autorelease_case,
    autochangelog_case,
    remove_changelog_file,
):
    """Test the process_distgit() function"""
    workdir = str(tmp_path)
    with tarfile.open(
        os.path.join(
            __here__,
            os.path.pardir,
            os.path.pardir,
            "test-data",
            "repodata",
            "dummy-test-package-gloster-git.tar.gz",
        )
    ) as tar:
        # Ensure unpackaged files are owned by user
        for member in tar:
            member.uid = os.getuid()
            member.gid = os.getgid()
        tar.extractall(path=workdir, numeric_owner=True)

    unpacked_repo_dir = os.path.join(workdir, "dummy-test-package-gloster")
    test_spec_file_path = os.path.join(
        unpacked_repo_dir,
        "dummy-test-package-gloster.spec",
    )

    with temporary_cd(unpacked_repo_dir):
        run(["git", "checkout", branch])

    if autorelease_case != "unchanged" or autochangelog_case != "unchanged":
        fuzz_spec_file(
            test_spec_file_path,
            autorelease_case,
            autochangelog_case,
            remove_changelog_file,
        )

    if remove_changelog_file:
        os.unlink(os.path.join(unpacked_repo_dir, "changelog"))

    if (
        autorelease_case != "unchanged"
        or autochangelog_case != "unchanged"
        or remove_changelog_file
    ) and not dirty_worktree:
        run_git_amend(unpacked_repo_dir)

    if overwrite_specfile:
        target_spec_file_path = None
    else:
        target_spec_file_path = os.path.join(workdir, "test-this-specfile-please.spec")

    orig_test_spec_file_stat = os.stat(test_spec_file_path)

    # Set restrictive umask to check that file mode is preserved.
    old_umask = os.umask(0o077)
    process_distgit.process_distgit(unpacked_repo_dir, target_spec_file_path)
    # And restore previous umask.
    os.umask(old_umask)

    test_spec_file_stat = os.stat(test_spec_file_path)
    attrs = ["mode", "ino", "dev", "uid", "gid"]
    if not overwrite_specfile:
        attrs.extend(["size", "mtime", "ctime"])

    for attr in attrs:
        assert getattr(test_spec_file_stat, "st_" + attr) == getattr(
            orig_test_spec_file_stat, "st_" + attr
        )

    expected_spec_file_path = os.path.join(
        __here__,
        os.path.pardir,
        os.path.pardir,
        "test-data",
        "repodata",
        "dummy-test-package-gloster.spec.expected",
    )

    with tempfile.NamedTemporaryFile() as tmpspec:
        shutil.copy2(expected_spec_file_path, tmpspec.name)
        if (
            autorelease_case != "unchanged"
            or autochangelog_case != "unchanged"
            or remove_changelog_file
        ):
            if autochangelog_case not in (
                "changelog case insensitive",
                "changelog trailing garbage",
            ):
                # "%changelog", "%ChAnGeLoG", ... stay verbatim, trick fuzz_spec_file() to
                # leave the rest of the cases as is, the %autorelease macro is expanded.
                fuzz_autochangelog_case = "unchanged"
            else:
                fuzz_autochangelog_case = autochangelog_case
            expected_spec_file_path = tmpspec.name
            fuzz_spec_file(
                expected_spec_file_path,
                autorelease_case,
                fuzz_autochangelog_case,
                remove_changelog_file,
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

        q_release = ["--qf", "%{release}\n"]
        test_output = check_output(test_cmd + q_release, encoding="utf-8").strip()
        test_relnum, test_rest = relnum_split(test_output)
        expected_output = check_output(expected_cmd + q_release, encoding="utf-8").strip()
        expected_relnum, expected_rest = relnum_split(expected_output)

        if dirty_worktree and (
            autorelease_case != "unchanged"
            or autochangelog_case != "unchanged"
            or remove_changelog_file
        ):
            expected_relnum += 1

        if branch == "epel8":
            expected_relnum += 1

        assert test_relnum == expected_relnum

        assert test_rest == expected_rest

        q_changelog = ["--changelog"]
        test_output = check_output(test_cmd + q_changelog, encoding="utf-8")
        expected_output = check_output(expected_cmd + q_changelog, encoding="utf-8")

        if dirty_worktree and (
            autorelease_case != "unchanged"
            or autochangelog_case != "unchanged"
            or remove_changelog_file
        ):
            diff = list(difflib.ndiff(expected_output.splitlines(), test_output.splitlines()))
            # verify entry for uncommitted changes
            assert all(line.startswith("+ ") for line in diff[:3])
            assert diff[0].endswith(f"-{expected_relnum}")
            assert diff[1] == "+ - Uncommitted changes"
            assert diff[2] == "+ "

            # verify the rest is the expected changelog
            assert all(line.startswith("  ") for line in diff[3:])
            assert expected_output.splitlines() == [line[2:] for line in diff[3:]]
        else:
            assert test_output == expected_output
