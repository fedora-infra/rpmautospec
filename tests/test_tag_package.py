import logging
import subprocess
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

    test_escape_sequences = {
        "%": "%25",
        ":": "%3A",
        "^": "%5E",
        "~": "%7E",
        "%:^~👍": "%25%3A%5E%7E%F0%9F%91%8D",
    }

    test_escape_tags = {
        # Artificial, to cover all git tag constraints
        ".boo": "%2Eboo",
        "blah.lock": "blah%2Elock",
        "foo..bar": "foo%2E%2Ebar",
        "foo\x10bar": "foo%10bar",
        "foo bar": "foo%20bar",
        "foo~bar^baz:gna": "foo%7Ebar%5Ebaz%3Agna",
        "?*[": "%3F%2A%5B",
        "/foo/": "%2Ffoo%2F",
        "foo/bar": "foo%2Fbar",
        "foo//bar": "foo%2F%2Fbar",
        "foo///bar": "foo%2F%2F%2Fbar",
        "foo.": "foo%2E",
        "foo@{bar": "foo%40%7Bbar",
        "@": "%40",
        "back\\slash": "back%5Cslash",
        # We want plus signs to be preserved
        "foo+bar": "foo+bar",
        # Actual N[E]VRs go here
        "gimp-2-2.10.18-1.fc31": "gimp-2-2.10.18-1.fc31",
    }

    @pytest.mark.parametrize("sequence", test_escape_sequences)
    def test_escape_sequence(self, sequence):
        """Test escape_sequence()"""
        assert tag_package.escape_sequence(sequence) == self.test_escape_sequences[sequence]

    @pytest.mark.parametrize("unescaped_tag", test_escape_tags)
    def test_escape_tag(self, unescaped_tag):
        """Test escape_tag()"""
        assert tag_package.escape_tag(unescaped_tag) == self.test_escape_tags[unescaped_tag]

    @mock.patch.object(tag_package, "git_tag_seqs_to_escape", [b"Not a string"])
    def test_escape_tag_broken_git_tag_seqs_to_escape(self):
        """Test escape_tag() with garbage in git_tag_seqs_to_escape"""
        with pytest.raises(TypeError):
            tag_package.escape_tag("a string")

    @pytest.mark.parametrize("unescaped_tag", test_escape_tags)
    def test_unescape_tag(self, unescaped_tag):
        """Test escape_tag()"""
        escaped_tag = self.test_escape_tags[unescaped_tag]
        assert tag_package.unescape_tag(escaped_tag) == unescaped_tag

    @mock.patch("rpmautospec.tag_package.subprocess.check_output")
    @pytest.mark.parametrize("raise_exception", (False, True))
    def test_run_command(self, check_output, raise_exception, caplog):
        """Test run_command()"""
        caplog.set_level(logging.DEBUG)

        if not raise_exception:
            check_output.return_value = "Some output"
            assert tag_package.run_command(["command"]) == "Some output"
            check_output.assert_called_once_with(["command"], cwd=None, stderr=subprocess.PIPE)
            assert not any(rec.levelno >= logging.WARNING for rec in caplog.records)
        else:
            check_output.side_effect = subprocess.CalledProcessError(
                returncode=139, cmd=["command"], output="Some command", stderr="And it failed!",
            )
            with pytest.raises(RuntimeError) as excinfo:
                tag_package.run_command(["command"])
            assert str(excinfo.value) == "Command `command` failed to run, returned 139"
            assert any(rec.levelno == logging.ERROR for rec in caplog.records)

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
        ),
    )
    @mock.patch("rpmautospec.tag_package.run_command")
    @mock.patch("rpmautospec.tag_package.koji_init")
    @mock.patch("rpmautospec.tag_package.get_package_builds")
    def test_main(self, get_package_builds, koji_init, run_command, phenomena, capsys):
        """Test the tag_package.main() under various conditions."""
        phenomena = [p.strip() for p in phenomena.split(",")]
        koji_init.return_value = kojiclient = mock.Mock()
        get_package_builds.return_value = test_builds = get_test_builds(phenomena)

        main_args = mock.Mock()
        # This IP address is from the reserved TEST-NET-1 address space, i.e. should be
        # guaranteed to not exist or be routable. Just in case we fail to mock out code that
        # attempts to contact a remote Koji instance.
        main_args.koji_url = "https://192.0.2.1"
        main_args.worktree_path = repopath = "/path/to/my/package/repo/pkgname"
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
            run_command.assert_called_once_with(["git", "tag", tag, commit], cwd=repopath)

            stdout, stderr = capsys.readouterr()

            if "tagcmdfails" in phenomena:
                assert stdout.strip() == "lp0 is on fire"
            else:
                assert stdout.strip() == f"tagged commit {commit} as {tag}"
