from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest import Config


def pytest_configure(config: "Config") -> None:
    config.addinivalue_line(
        "markers", "specfile_parser(type): Set the spec file parser for this test"
    )
