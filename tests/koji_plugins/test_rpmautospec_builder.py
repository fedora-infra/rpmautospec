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

    commit = "5ab06967a36e72f66add9b6cfe08bd98f8900693"
    url = f"git+https://src.fedoraproject.org/rpms/dummy-test-package-gloster.git#{commit}"

    data_scm_info = {
        "host": "src.fedoraproject.org",
        "module": "",
        "repository": "/rpms/dummy-test-package-gloster.git",
        "revision": commit,
        "scheme": "git+https://",
        "scmtype": "GIT",
        "url": url,
        "user": None,
    }

    @pytest.mark.parametrize(
        "testcase",
        (
            "normal",
            "other taskinfo method",
            "skip processing",
        ),
    )
    @mock.patch("rpmautospec.process_distgit.process_specfile")
    @mock.patch("rpmautospec.process_distgit.needs_processing")
    @mock.patch("koji.read_config_files")
    def test_process_distgit_cb(
        self,
        read_config_files,
        needs_processing_fn,
        process_specfile_fn,
        testcase,
    ):
        """Test the process_distgit_cb() function"""
        read_config_files.return_value = MockConfig()

        taskinfo_method_responsible = testcase != "other taskinfo method"
        skip_processing = testcase == "skip processing"

        # prepare test environment
        specfile_dir = "some dummy path"
        args = ["postSCMCheckout"]
        koji_session = mock.MagicMock()
        kwargs = {
            "scminfo": self.data_scm_info,
            "scratch": mock.MagicMock(),
            "srcdir": specfile_dir,
            "taskinfo": {"method": "buildSRPMFromSCM"},
            "session": koji_session,
        }

        if not taskinfo_method_responsible:
            kwargs["taskinfo"]["method"] = "not the method you're looking for"

        if skip_processing:
            needs_processing_fn.return_value = False

        # verify what the callback did
        if not taskinfo_method_responsible:
            needs_processing_fn.assert_not_called()
            return

        needs_processing_fn.return_value = True
        process_specfile_fn.return_value = None

        process_distgit_cb(*args, **kwargs)

        process_specfile_fn.assert_called_once()
