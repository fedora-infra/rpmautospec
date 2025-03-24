from unittest import mock

import pytest

from rpmautospec.cli import dispatch


@pytest.mark.parametrize("with_click", (True, False), ids=("with-click", "without-click"))
def test_cli(with_click: bool, capsys):
    dispatched_module = mock.Mock()
    dispatched_module.cli.return_value = sentinel = object()

    with mock.patch.object(dispatch, "import_module") as import_module:
        if with_click:
            import_module.side_effect = [dispatched_module]
        else:
            exc = ImportError("No module named 'click'")
            import_module.side_effect = [exc, dispatched_module]

        retval = dispatch.cli()

        assert retval is sentinel

        if with_click:
            import_module.assert_called_once_with(".click", package="rpmautospec.cli")
        else:
            stdout, stderr = capsys.readouterr()
            assert f"Can’t load rich CLI, falling back to minimal: {exc}" in stderr
            assert import_module.call_count == 2
            import_module.assert_called_with(".minimal", package="rpmautospec.cli")

        dispatched_module.cli.assert_called_once_with()
