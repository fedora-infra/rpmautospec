from argparse import ArgumentParser, _SubParsersAction
from contextlib import nullcontext
from unittest import mock

import pytest

from rpmautospec.cli import minimal
from rpmautospec.exc import SpecParseFailure


class TestCliDisplayedError:
    def test_show(self, capsys):
        exc = minimal.CliDisplayedError(msg="msg")
        exc.show()

        stdout, stderr = capsys.readouterr()
        assert not stdout
        assert "Error: msg" in stderr


def test_build_parser():
    parser = minimal.build_parser()
    assert isinstance(parser, ArgumentParser)
    assert any(
        isinstance(action, _SubParsersAction) and "process-distgit" in action.choices
        for action in parser._subparsers._actions
    )


@pytest.mark.parametrize("success", (True, False), ids=("success", "failure"))
def test_process_distgit(success):
    if success:
        expectation = nullcontext()
    else:
        expectation = pytest.raises(minimal.CliDisplayedError)

    with mock.patch.object(minimal, "do_process_distgit") as do_process_distgit:
        if not success:
            do_process_distgit.side_effect = SpecParseFailure("boop")

        with expectation:
            minimal.process_distgit("spec_or_path", "target")

    do_process_distgit.assert_called_once_with(spec_or_path="spec_or_path", target="target")


@pytest.mark.parametrize("success", (True, False), ids=("success", "failure"))
def test_cli(success, capsys):
    with (
        mock.patch.object(minimal, "build_parser") as build_parser,
        mock.patch.object(minimal, "globals") as mock_globals,
        mock.patch.object(minimal, "getfullargspec") as getfullargspec,
    ):
        args = build_parser.return_value.parse_args.return_value
        args.command = "process-distgit"
        args.spec_or_path = "spec_or_path"
        args.target = "target"

        process_distgit = mock.Mock()
        if not success:
            process_distgit.side_effect = exc = minimal.CliDisplayedError("hi")
            exc_show = mock.Mock(wraps=exc.show)
            exc.show = exc_show

        mock_globals.return_value = {"process_distgit": process_distgit}

        getfullargspec.return_value.args = ("spec_or_path", "target")

        retval = minimal.cli()

        process_distgit.assert_called_once_with(spec_or_path="spec_or_path", target="target")

        if success:
            assert retval == 0
        else:
            assert retval != 0
            exc_show.assert_called_once_with()
            stdout, stderr = capsys.readouterr()
            assert "Error: hi" in stderr
