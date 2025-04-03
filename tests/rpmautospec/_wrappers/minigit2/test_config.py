from configparser import ConfigParser
from ctypes import byref
from typing import TYPE_CHECKING

import pytest

from rpmautospec._wrappers.minigit2.config import Config
from rpmautospec._wrappers.minigit2.native_adaptation import git_config_p, lib

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def config_file(tmp_path: "Path") -> "Path":
    return tmp_path / "git_config"


@pytest.fixture
def config(config_file: "Path") -> Config:
    native = git_config_p()
    error_code = lib.git_config_open_ondisk(byref(native), str(config_file).encode("utf-8"))
    assert error_code == 0
    return Config(native=native)


class TestConfig:
    cls = Config

    @staticmethod
    def check_ini_file(config_file: "Path", key: str, value: str) -> None:
        parser = ConfigParser()
        parser.read_file(config_file.open())
        node = parser
        for name in key.split("."):
            node = node[name]
        assert node == value

    def test_mapping_interface(self, config: Config, config_file: "Path") -> None:
        for key, setvalue, strvalue in (
            ("user.name", b"Santa Claus", "Santa Claus"),
            ("user.email", "santa@northpole.org", "santa@northpole.org"),
            ("pull.rebase", True, "true"),
            ("submodule.fetchJobs", 1, "1"),
        ):
            assert key not in config

            with pytest.raises(KeyError):
                config[key]

            config[key] = setvalue

            assert key in config
            assert config[key] == strvalue

            self.check_ini_file(config_file, key, strvalue)

            del config[key]

            assert key not in config

            with pytest.raises(KeyError):
                config[key]

            with pytest.raises(KeyError):
                self.check_ini_file(config_file, key, strvalue)
