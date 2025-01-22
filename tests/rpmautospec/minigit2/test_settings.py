from rpmautospec.minigit2.native_adaptation import git_config_level_t
from rpmautospec.minigit2.settings import SearchPathList


class TestSearchPathList:
    def test_get_set(self):
        spl = SearchPathList()

        # from auto-used git_empty_config() fixture
        assert spl[git_config_level_t.SYSTEM] == "/dev/null"

        spl[git_config_level_t.SYSTEM] = "/DEV/NULL"
        assert spl[git_config_level_t.SYSTEM] == "/DEV/NULL"

        spl[git_config_level_t.SYSTEM] = b"/DEV/DOESNTEXIST"
        assert spl[git_config_level_t.SYSTEM] == "/DEV/DOESNTEXIST"
