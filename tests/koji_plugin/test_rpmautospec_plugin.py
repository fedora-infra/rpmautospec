import filecmp
import os
import tarfile
import tempfile
from unittest.mock import MagicMock

from koji_plugin.rpmautospec_plugin import autospec_cb


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

    def test_autospec_cb(self):
        """Test the autospec_cb() function"""
        with tempfile.TemporaryDirectory() as workdir:
            with tarfile.open(
                os.path.join(
                    __here__,
                    os.path.pardir,
                    "test-data",
                    "repodata",
                    "dummy-test-package-gloster_git.tar.gz"
                )
            ) as tar:
                tar.extractall(path=workdir)

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
                for x in range(2, 14)
            ]
            koji_session.listBuilds.return_value = builds
            args = ["postSCMCheckout"]
            kwargs = {
                "scminfo": data_scm_info,
                "build_tag": data_build_tag,
                "scratch": MagicMock(),
                "srcdir": os.path.join(workdir, "dummy-test-package-gloster"),
                "taskinfo": {"method": "buildSRPMFromSCM"},
                "session": koji_session,
            }
            autospec_cb(*args, **kwargs)
            assert filecmp.cmp(
                os.path.join(kwargs["srcdir"], "dummy-test-package-gloster.spec"),
                os.path.join(
                    __here__,
                    os.path.pardir,
                    "test-data",
                    "repodata",
                    "dummy-test-package-gloster.spec",
                ),
            )
