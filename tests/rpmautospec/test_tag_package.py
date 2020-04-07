import logging
from unittest import mock

import pytest

from rpmautospec import tag_package


VALID_HASH = "0123456789abcdef0123456789abcdef01234567"
INVALID_HASH = "not a hash but long enough 0123456789012"
TOO_SHORT_HASH = "0123abcd"


def get_test_builds(phenomena):
    if "stagingbuildsys" in phenomena:
        buildsys_host = "src.stg.fedoraproject.org"
    elif "wrongbuildsys" in phenomena:
        buildsys_host = "someones.system.at.home.org"
    else:
        buildsys_host = "src.fedoraproject.org"

    build = {
        "name": "pkgname",
        "epoch": None,
        "version": "1.0",
        "release": "1.fc32",
        "owner_name": "hamburglar",
        "source": f"git+https://{buildsys_host}/rpms/pkgname#{VALID_HASH}",
        "build_id": 123,
        "task_id": 54321,
    }

    for phenomenon in phenomena:
        if phenomenon in (
            "normal",
            "nosrpmtask",
            "notasks",
            "trailingslashpath",
            "stagingbuildsys",
            "wrongbuildsys",
            "tagcmdfails",
            "pagure_tag",
        ):
            # Ignore phenomena handled above and/or in the test method.
            pass
        elif phenomenon == "epoch":
            build["epoch"] = 1
        elif phenomenon == "modularbuild":
            build["owner_name"] = "mbs/mbs.fedoraproject.org"
        elif phenomenon in ("invalidhash", "tooshorthash"):
            if "source" in build:
                # Don't accidentally put the source back if it shouldn't be.
                if phenomenon == "invalidhash":
                    hash_val = INVALID_HASH
                else:
                    hash_val = TOO_SHORT_HASH
                build["source"] = f"git+https://src.fedoraproject.org/rpms/pkgname#{hash_val}"
        elif phenomenon == "nosource":
            del build["source"]
        else:
            raise ValueError(f"Don't understand phenomenon: {phenomenon}")

    return [build]


class TestTagPackage:
    """Test the rpmautospec.tag_package module."""

    @pytest.mark.parametrize(
        "phenomena",
        (
            "normal",
            "stagingbuildsys",
            "wrongbuildsys",
            "trailingslashpath",
            "epoch",
            "modularbuild",
            "invalidhash",
            "tooshorthash",
            "nosource",
            "nosource,nosrpmtask",
            "nosource,notasks",
            "nosource,invalidhash",
            "nosource,tooshorthash",
            "nosource,stagingbuildsys",
            "nosource,wrongbuildsys",
            "tagcmdfails",
            "pagure_tag",
        ),
    )
    @mock.patch("rpmautospec.tag_package.run_command")
    @mock.patch("rpmautospec.tag_package.koji_init")
    @mock.patch("rpmautospec.tag_package.get_package_builds")
    @mock.patch("rpmautospec.py2compat.tagging.requests.post")
    def test_main(self, pagure_post, get_package_builds, koji_init, run_command, phenomena, caplog):
        """Test the tag_package.main() under various conditions."""
        caplog.set_level(logging.DEBUG)

        phenomena = [p.strip() for p in phenomena.split(",")]
        koji_init.return_value = kojiclient = mock.Mock()

        get_package_builds.return_value = test_builds = get_test_builds(phenomena)

        main_args = mock.Mock()
        # This IP address is from the reserved TEST-NET-1 address space, i.e. should be
        # guaranteed to not exist or be routable. Just in case we fail to mock out code that
        # attempts to contact a remote Koji instance.
        main_args.koji_url = "https://192.0.2.1"
        main_args.worktree_path = repopath = "/path/to/my/package/repo/pkgname"
        pagure_post.return_value.ok = True

        if "pagure_tag" in phenomena:
            main_args.pagure_url = "https://192.0.2.2"
            main_args.pagure_token = "token"

        if "trailingslashpath" in phenomena:
            # This shouldn't change anything, really.
            main_args.worktree_path += "/"

        if "invalidhash" in phenomena:
            commit = INVALID_HASH
        elif "tooshorthash" in phenomena:
            commit = TOO_SHORT_HASH
        else:
            commit = VALID_HASH

        if any(
            p in ("invalidhash", "tooshorthash", "nosource", "wrongbuildsys") for p in phenomena
        ):
            if "notasks" in phenomena:
                tasks = []
            else:
                tasks = [{"method": "ignoremeplease", "task": 456789}]
                if "nosrpmtask" not in phenomena:
                    tasks.append({"method": "buildSRPMFromSCM", "id": 123456})
                    if "stagingbuildsys" in phenomena:
                        buildsys_host = "src.stg.fedoraproject.org"
                    elif "wrongbuildsys" in phenomena:
                        buildsys_host = "someones.system.at.home.org"
                    else:
                        buildsys_host = "src.fedoraproject.org"
                    task_source = f"git+https://{buildsys_host}/rpms/pkgname#{commit}"
                    kojiclient.getTaskRequest.return_value = [task_source]
            kojiclient.getTaskChildren.return_value = tasks

        if "tagcmdfails" in phenomena:
            run_command.side_effect = RuntimeError("lp0 is on fire")

        tag_package.main(main_args)

        if "pagure_tag" in phenomena:
            pagure_post.assert_called_once_with(
                "https://192.0.2.2/api/0/rpms/pkgname/git/tags",
                data={
                    "tagname": "build/pkgname-0-1.0-1.fc32",
                    "commit_hash": "0123456789abcdef0123456789abcdef01234567",
                    "message": None,
                    "with_commits": True,
                    "force": False,
                },
                headers={"Authorization": "token token"},
            )

        if "nosource" in phenomena:
            kojiclient.getTaskChildren.assert_called_once_with(test_builds[0]["task_id"])

            if any(p in ("notasks", "nosrpmtask") for p in phenomena):
                kojiclient.getTaskRequest.assert_not_called()

        if any(
            p
            in (
                "invalidhash",
                "tooshorthash",
                "modularbuild",
                "nosrpmtask",
                "notasks",
                "wrongbuildsys",
            )
            for p in phenomena
        ):
            run_command.assert_not_called()
        else:
            build = test_builds[0]
            nevr = "-".join(
                str(build[partname]) if build[partname] else "0"
                for partname in ("name", "epoch", "version", "release")
            )
            tag = f"build/{nevr}"
            run_command.assert_called_once_with(
                ["git", "tag", "--force", tag, commit], cwd=repopath
            )

            if "tagcmdfails" in phenomena:
                assert "lp0 is on fire" in caplog.text
            else:
                assert f"Tagged commit {commit} as {tag}" in caplog.messages
