import logging
from unittest import mock

import pytest

from koji_plugins.rpmautospec_builder import process_distgit_cb


class MockConfig:
    test_config = {
        "pagure": {"url": "src.fedoraproject.org", "token": "aaabbbcc"},
    }

    def get(self, section, option, **kwargs):
        return self.test_config[section][option]


class TestRpmautospecBuilder:
    """Test the rpmautospec builder plugin for Koji."""

    data_build_tag = {
        "id": 11522,
        "name": "f32-build",
        "arches": "armv7hl i686 x86_64 aarch64 ppc64le s390x",
        "extra": {},
        "locked": False,
        "maven_include_all": False,
        "maven_support": False,
        "perm": "admin",
        "perm_id": 1,
    }

    @pytest.mark.parametrize(
        "testcase",
        (
            "normal",
            "other taskinfo method",
            "no features used",
        ),
    )
    @mock.patch("koji_plugins.rpmautospec_builder.process_distgit")
    @mock.patch("koji.read_config_files")
    def test_process_distgit_cb(
        self,
        read_config_files,
        process_distgit_fn,
        testcase,
        caplog,
    ):
        """Test the process_distgit_cb() function"""
        read_config_files.return_value = MockConfig()

        taskinfo_method_responsible = testcase != "other taskinfo method"

        # prepare test environment
        specfile_dir = "some dummy path"
        args = ["postSCMCheckout"]
        koji_session = mock.MagicMock()
        kwargs = {
            "build_tag": self.data_build_tag,
            "scratch": mock.MagicMock(),
            "srcdir": specfile_dir,
            "taskinfo": {"method": "buildSRPMFromSCM"},
            "session": koji_session,
        }

        # return value is if processing was needed
        process_distgit_fn.return_value = testcase != "no features used"

        if not taskinfo_method_responsible:
            kwargs["taskinfo"]["method"] = "not the method you're looking for"

        # test the callback
        with caplog.at_level(logging.DEBUG):
            process_distgit_cb(*args, **kwargs)

        if testcase == "no features used":
            assert "skipping" in caplog.text
        else:
            assert not caplog.records
