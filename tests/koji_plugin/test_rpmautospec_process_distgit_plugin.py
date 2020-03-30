import os
import shutil
from subprocess import check_output
import tarfile
import tempfile
from unittest.mock import MagicMock

import pytest

from koji_plugin.rpmautospec_process_distgit_plugin import process_distgit_cb


__here__ = os.path.dirname(__file__)

commit = "5ab06967a36e72f66add9b6cfe08bd98f8900693"
url = f"git+https://src.fedoraproject.org/rpms/dummy-test-package-gloster.git#{commit}"

data_scm_info = {
    "host": "src.fedoraproject.org",
    "module": "",
    "repository": "/rpms/dummy-test-package-gloster.git",
    "revision": "5ab06967a36e72f66add9b6cfe08bd98f8900693",
    "scheme": "git+https://",
    "scmtype": "GIT",
    "url": url,
    "user": None,
}

data_build_tag = {"id": "dsttag", "tag_id": "fc32", "tag_name": "fc32"}


class TestRpmautospecPlugin:
    """Test the koji_plugin.rpmautospec_plugin module"""

    autorel_autochangelog_cases = [
        (autorel_case, autochangelog_case)
        for autorel_case in ("unchanged", "with braces")
        for autochangelog_case in (
            "unchanged",
            "changelog case insensitive",
            "changelog trailing garbage",
            "line in between",
            "trailing line",
            "with braces",
        )
    ]

    @staticmethod
    def fuzz_spec_file(spec_file_path, autorel_case, autochangelog_case):
        """Fuzz a spec file in ways which shouldn't change the outcome"""

        with open(spec_file_path, "r") as orig, open(spec_file_path + ".new", "w") as new:
            for line in orig:
                if line.startswith("Release:") and autorel_case != "unchanged":
                    if autorel_case == "with braces":
                        print("Release:        %{autorel}", file=new)
                    else:
                        raise ValueError(f"Unknown autorel_case: {autorel_case}")
                elif line.strip() == "%changelog" and autochangelog_case != "unchanged":
                    if autochangelog_case == "changelog case insensitive":
                        print("%ChAnGeLoG", file=new)
                    elif autochangelog_case == "changelog trailing garbage":
                        print("%changelog with trailing garbage yes this works", file=new)
                    elif autochangelog_case == "line in between":
                        print("%changelog\n\n%autochangelog", file=new)
                        break
                    elif autochangelog_case == "trailing line":
                        print("%changelog\n%autochangelog\n", file=new)
                        break
                    elif autochangelog_case == "with braces":
                        print("%changelog\n%{autochangelog}", file=new)
                        break
                    else:
                        raise ValueError(f"Unknown autochangelog_case: {autochangelog_case}")
                else:
                    print(line, file=new, end="")

        os.rename(spec_file_path + ".new", spec_file_path)

    @pytest.mark.parametrize("autorel_case,autochangelog_case", autorel_autochangelog_cases)
    def test_autospec_cb(self, autorel_case, autochangelog_case):
        """Test the autospec_cb() function"""
        with tempfile.TemporaryDirectory() as workdir:
            with tarfile.open(
                os.path.join(
                    __here__,
                    os.path.pardir,
                    "test-data",
                    "repodata",
                    "dummy-test-package-gloster-git.tar.gz",
                )
            ) as tar:
                tar.extractall(path=workdir)

            unpacked_repo_dir = os.path.join(workdir, "dummy-test-package-gloster")
            unprocessed_spec_file_path = os.path.join(
                unpacked_repo_dir, "dummy-test-package-gloster.spec",
            )

            if autorel_case != "unchanged" or autochangelog_case != "unchanged":
                self.fuzz_spec_file(unprocessed_spec_file_path, autorel_case, autochangelog_case)

            koji_session = MagicMock()
            koji_session.getPackageID.return_value = 30489
            name = "dummy-test-package-gloster"
            builds = [
                {
                    "epoch": None,
                    "nvr": f"{name}-0-{x}.f32",
                    "name": name,
                    "release": f"{x}.fc32",
                    "version": "0",
                }
                for x in range(2, 7)
            ]
            koji_session.listBuilds.return_value = builds
            args = ["postSCMCheckout"]
            kwargs = {
                "scminfo": data_scm_info,
                "build_tag": data_build_tag,
                "scratch": MagicMock(),
                "srcdir": unpacked_repo_dir,
                "taskinfo": {"method": "buildSRPMFromSCM"},
                "session": koji_session,
            }

            process_distgit_cb(*args, **kwargs)

            expected_spec_file_path = os.path.join(
                __here__,
                os.path.pardir,
                "test-data",
                "repodata",
                "dummy-test-package-gloster.spec",
            )

            with tempfile.NamedTemporaryFile() as tmpspec:
                if autorel_case != "unchanged" or autochangelog_case != "unchanged":
                    if autochangelog_case not in (
                        "changelog case insensitive",
                        "changelog trailing garbage",
                    ):
                        # "%changelog", "%ChAnGeLoG", ... stay verbatim, trick fuzz_spec_file() to
                        # leave the rest of the cases as is, the %autorel macro is expanded.
                        autochangelog_case = "unchanged"
                    shutil.copy2(expected_spec_file_path, tmpspec.name)
                    expected_spec_file_path = tmpspec.name
                    self.fuzz_spec_file(expected_spec_file_path, autorel_case, autochangelog_case)

                rpm_cmd = ["rpm", "--define", "dist .fc32", "--specfile"]

                unprocessed_cmd = rpm_cmd + [unprocessed_spec_file_path]
                expected_cmd = rpm_cmd + [expected_spec_file_path]

                q_release = ["--qf", "%{release}\n"]
                assert check_output(unprocessed_cmd + q_release) == check_output(
                    expected_cmd + q_release
                )

                q_changelog = ["--changelog"]
                assert check_output(unprocessed_cmd + q_changelog) == check_output(
                    expected_cmd + q_changelog
                )
