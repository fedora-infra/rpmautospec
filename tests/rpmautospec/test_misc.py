import logging
import os
from tempfile import NamedTemporaryFile
from typing import TextIO

import pytest

from rpmautospec import misc

__here__ = os.path.dirname(__file__)


class TestMisc:
    """Test the rpmautospec.misc module"""

    @staticmethod
    def _generate_spec_with_features(
        specfile: TextIO,
        *,
        with_autorelease=True,
        autorelease_flags="",
        with_changelog=True,
        with_autochangelog=True,
    ):
        contents = [
            "Line 1",
            "Line 2",
            f"Release: %autorelease {autorelease_flags}" if with_autorelease else "Release: 1",
            "Line 4",
            "Line 5",
        ]
        if with_changelog:
            contents.append("%changelog")
        if with_autochangelog:
            contents.append("%autochangelog")
        else:
            contents.extend(["* Thu Jan 01 1970 Some Name <email@example.com>", "- some entry"])

        print("\n".join(contents), file=specfile)
        specfile.flush()

    @pytest.mark.parametrize(
        "with_autorelease,autorelease_flags,with_changelog,with_autochangelog",
        (
            pytest.param(True, "", True, True, id="all features"),
            pytest.param(True, "-b 200", True, True, id="with non standard base release number"),
            pytest.param(False, "", False, False, id="nothing"),
        ),
    )
    def test_check_specfile_features(
        self,
        with_autorelease,
        autorelease_flags,
        with_changelog,
        with_autochangelog,
    ):
        with NamedTemporaryFile(mode="w+") as specfile:
            self._generate_spec_with_features(
                specfile,
                with_autorelease=with_autorelease,
                autorelease_flags=autorelease_flags,
                with_changelog=with_changelog,
                with_autochangelog=with_autochangelog,
            )

            features = misc.check_specfile_features(specfile.name)

            assert features.has_autorelease == with_autorelease
            if with_changelog:
                assert features.changelog_lineno == 6
            else:
                assert features.changelog_lineno is None
            assert features.has_autochangelog == with_autochangelog
            if with_autochangelog:
                assert features.autochangelog_lineno == 7
            else:
                assert features.autochangelog_lineno is None

    def test_specfile_uses_rpmautospec_no_macros(self, caplog):
        """Test no macros on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = os.path.join(
            __here__,
            os.path.pardir,
            "test-data",
            "test-specfiles",
            "no-macros.spec",
        )

        result = misc.specfile_uses_rpmautospec(specfile_path)

        assert result is False

    def test_specfile_uses_rpmautospec_autorelease_only(self, caplog):
        """Test autorelease only on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = os.path.join(
            __here__,
            os.path.pardir,
            "test-data",
            "test-specfiles",
            "autorelease-only.spec",
        )

        result = misc.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        result_no_autorelease = misc.specfile_uses_rpmautospec(
            specfile_path, check_autorelease=False
        )
        assert result_no_autorelease is False

    def test_specfile_uses_rpmautospec_autochangelog_only(self, caplog):
        """Test autochangelog only on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = os.path.join(
            __here__,
            os.path.pardir,
            "test-data",
            "test-specfiles",
            "autochangelog-only.spec",
        )

        result = misc.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        result_no_changelog = misc.specfile_uses_rpmautospec(
            specfile_path, check_autochangelog=False
        )
        assert result_no_changelog is False

    def test_specfile_uses_rpmautospec_throws_error(self, caplog):
        """Test specfile_uses_rpmautospec() throws an error when both params are false"""
        caplog.set_level(logging.DEBUG)

        specfile_path = os.path.join(
            __here__,
            os.path.pardir,
            "test-data",
            "test-specfiles",
            "autochangelog-only.spec",
        )

        result = misc.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        with pytest.raises(ValueError):
            misc.specfile_uses_rpmautospec(
                specfile_path, check_autochangelog=False, check_autorelease=False
            )
