import shlex
from unittest import mock

import koji
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
            "no buildroot supplied",
            "rpmautospec installed",
            "other taskinfo method",
            "skip processing",
            "buildroot install fails",
            "buildroot cmd fails",
        ),
    )
    @mock.patch("rpmautospec.process_distgit.needs_processing")
    @mock.patch("koji_plugins.rpmautospec_builder._steal_buildroot_object_from_frame_stack")
    @mock.patch("koji_plugins.rpmautospec_builder.pagure_proxy")
    @mock.patch("koji.read_config_files")
    def test_process_distgit_cb(
        self,
        read_config_files,
        pagure_proxy,
        steal_buildroot_fn,
        needs_processing_fn,
        testcase,
    ):
        """Test the process_distgit_cb() function"""
        read_config_files.return_value = MockConfig()

        buildroot_supplied = testcase != "no buildroot supplied"
        rpmautospec_installed = testcase == "rpmautospec installed"
        taskinfo_method_responsible = testcase != "other taskinfo method"
        skip_processing = testcase == "skip processing"
        buildroot_install_fails = testcase == "buildroot install fails"
        buildroot_cmd_fails = testcase == "buildroot cmd fails"

        # prepare test environment
        srcdir_within = "/builddir/build/BUILD/something with spaces"
        unpacked_repo_dir = f"/var/lib/mock/some-root/{srcdir_within}"
        args = ["postSCMCheckout"]
        koji_session = mock.MagicMock()
        kwargs = {
            "scminfo": self.data_scm_info,
            "build_tag": self.data_build_tag,
            "scratch": mock.MagicMock(),
            "srcdir": unpacked_repo_dir,
            "taskinfo": {"method": "buildSRPMFromSCM"},
            "session": koji_session,
        }
        mock_retvals = []

        if not taskinfo_method_responsible:
            kwargs["taskinfo"]["method"] = "not the method you're looking for"

        if skip_processing:
            needs_processing_fn.return_value = False

        buildroot = mock.MagicMock()
        installed_packages = [
            {"name": "foo", "version": "1.0", "release": "3"},
            {"name": "bar", "version": "1.1", "release": "1"},
            {"name": "baz", "version": "2.0", "release": "2"},
        ]

        if rpmautospec_installed:
            installed_packages.append({"name": "rpmautospec", "version": "0.1", "release": "1"})
        else:
            if buildroot_install_fails:
                mock_retvals.append(1)
            else:
                mock_retvals.append(0)

        buildroot.getPackageList.return_value = installed_packages

        if buildroot_supplied:
            kwargs["buildroot"] = buildroot
        else:
            steal_buildroot_fn.return_value = buildroot

        buildroot.path_without_to_within.return_value = srcdir_within

        buildroot.mock.side_effect = mock_retvals

        if buildroot_cmd_fails:
            mock_retvals.append(128)
        else:
            mock_retvals.append(0)

        # test the callback
        if any(retval != 0 for retval in mock_retvals):
            with pytest.raises(koji.BuildError):
                process_distgit_cb(*args, **kwargs)
            return
        else:
            process_distgit_cb(*args, **kwargs)

        # verify what the callback did
        if not taskinfo_method_responsible:
            needs_processing_fn.assert_not_called()
            return

        needs_processing_fn.assert_called_once_with(unpacked_repo_dir)

        if skip_processing:
            buildroot.getPackageList.assert_not_called()
            return

        buildroot.getPackageList.assert_called_once()
        buildroot.path_without_to_within.assert_called_once()

        if buildroot_supplied:
            steal_buildroot_fn.assert_not_called()
        else:
            steal_buildroot_fn.assert_called_once_with()

        if rpmautospec_installed:
            assert not any("--install" in call[0] for call in buildroot.mock.call_args_list)
        else:
            buildroot.mock.assert_any_call(["--install", "rpmautospec"])

        mock_args = [
            "--shell",
            f"rpmautospec --debug process-distgit --process-specfile {shlex.quote(srcdir_within)}",
        ]
        buildroot.mock.assert_called_with(mock_args)
