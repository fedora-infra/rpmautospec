from contextlib import nullcontext
from unittest import mock
from unittest.mock import call

import pytest

from rpmautospec._wrappers.minirpm._rpm import exc, toplevel


@pytest.mark.parametrize("testcase", ("with-file", "with-file-error", "without-file"))
def test_setLogFile(testcase: str):
    with_file = "with-file" in testcase
    error = "error" in testcase

    if with_file:
        file = mock.Mock()
    else:
        file = None

    with (
        mock.patch.object(toplevel, "libc") as libc,
        mock.patch.object(toplevel, "librpmio") as librpmio,
        mock.patch.object(toplevel, "FILE_p") as FILE_p,
    ):
        if error:
            libc.fdopen.return_value = None
            expectation = pytest.raises(IOError)
        else:
            expectation = nullcontext()

        with expectation:
            toplevel.setLogFile(file)

    if with_file:
        file.fileno.assert_called_once_with()
        libc.fdopen.assert_called_once_with(file.fileno.return_value, b"a")
        if not error:
            librpmio.rpmlogSetFile.assert_called_once_with(libc.fdopen.return_value)
    else:
        librpmio.rpmlogSetFile.assert_called_once_with(FILE_p.return_value)


@pytest.mark.parametrize("success", (True, False), ids=("success", "failure"))
def test_reloadConfig(success: bool):
    globalmock = mock.Mock()
    with (
        mock.patch.object(toplevel, "librpm") as librpm,
        mock.patch.object(toplevel, "librpmio") as librpmio,
    ):
        globalmock.attach_mock(librpm, "librpm")
        globalmock.attach_mock(librpmio, "librpmio")
        librpm.rpmReadConfigFiles.return_value = 0 if success else -1
        retval = toplevel.reloadConfig()

    assert retval == success

    globalmock.assert_has_calls(
        (
            call.librpmio.rpmFreeMacros(None),
            call.librpm.rpmFreeRpmrc(),
            call.librpm.rpmReadConfigFiles(None, None),
        ),
    )


def test_addMacro():
    with mock.patch.object(toplevel, "librpmio") as librpmio:
        toplevel.addMacro("foo", "bar")

    librpmio.rpmPushMacro.assert_called_once_with(None, b"foo", None, b"bar", -1)


@pytest.mark.parametrize("success", (True, False), ids=("success", "failure"))
def test_expandMacro(success: bool):
    with (
        mock.patch.object(toplevel, "librpmio") as librpmio,
        mock.patch.object(toplevel, "c_char_p") as c_char_p,
        mock.patch.object(toplevel, "byref") as byref,
        mock.patch.object(toplevel, "libc") as libc,
        mock.patch.object(toplevel, "cast") as cast,
    ):
        expanded = c_char_p.return_value
        if success:
            librpmio.rpmExpandMacros.return_value = 0
            expanded.value.decode.return_value = "bar"
            expectation = nullcontext()
        else:
            librpmio.rpmExpandMacros.return_value = -1
            expectation = pytest.raises(exc.RpmError, match="error expanding macro")

        with expectation:
            retval = toplevel.expandMacro("%foo")

        if success:
            assert retval == "bar"
            librpmio.rpmExpandMacros.assert_called_once_with(None, b"%foo", byref(expanded), 0)
            expanded.value.decode.assert_called_once_with("utf-8", errors="surrogateescape")
            libc.free.assert_called_once_with(cast(expanded, toplevel.c_void_p))
