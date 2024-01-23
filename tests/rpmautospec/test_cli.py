import logging
import subprocess
import sys
from unittest import mock

import pytest

from rpmautospec import cli

from . import temporary_cd


@pytest.mark.parametrize("log_level_name", ("CRITICAL", "WARNING", "INFO", "DEBUG"))
def test_setup_logging(log_level_name):
    """Test the setup_logging() function."""
    log_level = getattr(logging, log_level_name)

    with mock.patch.object(cli.logging, "StreamHandler") as StreamHandler, mock.patch.object(
        cli.logging, "lastResort"
    ) as lastResort, mock.patch.object(cli.logging, "basicConfig") as basicConfig:
        info_handler = StreamHandler.return_value
        cli.setup_logging(log_level)

    StreamHandler.assert_called_once_with(stream=sys.stdout)

    info_handler.setLevel.assert_called_with(log_level)
    info_handler.addFilter.assert_called_once()

    lastResort.addFilter.assert_called_once()

    if log_level_name == "INFO":
        info_handler.setFormatter.assert_called_once()
        lastResort.setFormatter.assert_called_once()
    else:
        info_handler.setFormatter.assert_not_called()
        lastResort.setFormatter.assert_not_called()

    basicConfig.assert_called_once_with(level=log_level, handlers=[info_handler, lastResort])


@pytest.mark.parametrize("exception_cls", (None, BrokenPipeError, OSError))
def test_handle_expected_exceptions(exception_cls):
    """Test the handle_expected_exceptions context manager."""
    with mock.patch.object(cli.sys, "exit") as sys_exit:
        with cli.handle_expected_exceptions():
            if exception_cls:
                raise exception_cls("BOO")

    if exception_cls != OSError:
        sys_exit.assert_not_called()
    else:
        sys_exit.assert_called_once_with("error: BOO")


def test_main_nothing():
    """Test running the CLI without arguments."""
    completed = subprocess.run(
        [sys.executable, "-c", "from rpmautospec import cli; cli.main()"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )

    assert completed.returncode != 0
    assert "error: the following arguments are required: subcommand" in completed.stderr


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
