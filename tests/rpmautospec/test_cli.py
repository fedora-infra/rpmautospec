import subprocess
import sys

import pytest

from . import temporary_cd


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
    "release, changelog",
    (
        ("Release: 1%{dist}", "%changelog\n- log line"),
        ("Release: %{autorelease}", "%changelog\n- log line"),
        ("Release: 1%{dist}", "%changelog\n%autochangelog"),
        ("", "%changelog\n- log line"),
        ("Release: 1%{dist}\nRelease: 1%{dist}", "%changelog\n- log line"),
        ("Release: 1%{dist}", ""),
        ("Release: 1%{dist}", "%changelog\n%changelog\n- log line"),
    ),
    ids=(
        "release-changelog",
        "autorelease-changelog",
        "release-autochangelog",
        "norelease-changelog-failure",
        "doublerelease-changelog-failure",
        "release-nochangelog-failure",
        "release-doublechangelog-failure",
    ),
)
def test_main_convert(release, changelog, repo, request):
    # we do the conversion iff it wasn't done before
    needs_autorelease = "autorelease" not in release
    needs_autochangelog = "autochangelog" not in changelog

    with temporary_cd(repo.workdir):
        completed = subprocess.run(
            [sys.executable, "-c", "from rpmautospec import cli; cli.main()", "convert"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )

    if "failure" in request.node.name:
        assert completed.returncode != 0

        assert completed.stdout == ""

        if "norelease" in request.node.name:
            assert "unable to locate release tag" in completed.stderr.lower()
        elif "doublerelease" in request.node.name:
            assert "found multiple release tags" in completed.stderr.lower()
        elif "nochangelog" in request.node.name:
            assert "unable to locate %changelog line" in completed.stderr.lower()
        elif "doublechangelog" in request.node.name:
            assert "found multiple %changelog" in completed.stderr.lower()
        else:
            assert False, "Not all failure cases covered in test."
    else:
        assert completed.returncode == 0

        assert "Converted to " in completed.stdout
        assert ("%autorelease" in completed.stdout) == needs_autorelease
        assert ("%autochangelog" in completed.stdout) == needs_autochangelog
        # Warnings end up in stderr
        assert ("already uses %autorelease" in completed.stderr) != needs_autorelease
        assert ("already uses %autochangelog" in completed.stderr) != needs_autochangelog
