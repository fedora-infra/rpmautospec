import sys

import pytest

from rpmautospec._wrappers.minigit2.native_adaptation import git_config_level_t
from rpmautospec._wrappers.minigit2.settings import SearchPathList

_UNSET = object()


class TestSearchPathList:
    @pytest.mark.parametrize(
        "set_value, get_value",
        (
            # From auto-used git_empty_config() fixture, fails if pygit2 is loaded and used
            # in the fixture.
            pytest.param(
                _UNSET,
                "/dev/null",
                marks=pytest.mark.skipif("pygit2" in sys.modules, reason="pygit2 is loaded"),
            ),
            ("/DEV/NULL", "/DEV/NULL"),
            (b"/DEV/DOESNTEXIST", "/DEV/DOESNTEXIST"),
        ),
    )
    def test_get_set(self, set_value, get_value):
        spl = SearchPathList()

        if set_value is not _UNSET:
            spl[git_config_level_t.SYSTEM] = set_value
        assert spl[git_config_level_t.SYSTEM] == get_value
