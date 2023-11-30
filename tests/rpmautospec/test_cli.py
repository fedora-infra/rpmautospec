import os
import subprocess
import sys

import pytest

from . import temporary_cd

__here__ = os.path.dirname(__file__)
# We want to have our srcdir in the Python module load path so that
# we actually import our version of the code and not the installed module.
# Using run-rpmautospec.py takes care of this for us.
run_rpmautospec_py = __here__ + "/../../run-rpmautospec.py"


def test_main_help():
    """Test that getting top-level help works

    This serves a smoke test around argument parsing. It must execute
    another process because argparse relies on sys.exit() actually stopping
    execution, i.e. mocking it out won't work, because argparse will then
    merrily chug along after displaying help.
    """
    completed = subprocess.run(
        [sys.executable, "-c", "from rpmautospec import cli; cli.main()", "--help"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )

    assert "usage:" in completed.stdout
    assert completed.stderr == ""


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
def test_main_convert(release, changelog, repo):
    # we do the conversion iff it wasn't done before
    autorelease = "autorelease" not in release
    autochangelog = "autochangelog" not in changelog
    if not (autorelease or autochangelog):
        pytest.skip("Not testing with a fully converted spec file.")

    with temporary_cd(repo.workdir):
        completed = subprocess.run(
            [sys.executable, run_rpmautospec_py, "convert"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            print("stderr:", completed.stderr)
            completed.check_returncode()

    assert "Converted to " in completed.stdout
    assert ("%autorelease" in completed.stdout) == autorelease
    assert ("%autochangelog" in completed.stdout) == autochangelog
    # Warnings end up in stderr
    assert ("is already using %autorelease" in completed.stderr) != autorelease
    assert ("is already using %autochangelog" in completed.stderr) != autochangelog
