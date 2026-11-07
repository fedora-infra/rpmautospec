import os.path
import tarfile
import tempfile
from contextlib import nullcontext
from pathlib import Path
from unittest import mock

import pytest

from rpmautospec.compat import rpm
from rpmautospec.exc import SpecParseFailure
from rpmautospec.subcommands import release

from ...common import create_tagged_repo

__here__ = os.path.dirname(__file__)


class TestRelease:
    """Test the rpmautospec.subcommands.release module"""

    @pytest.mark.parametrize(
        "testcase", ("complete-release", "numbers-only", "specfile-parse-failure")
    )
    def test_do_calculate_release(self, testcase):
        complete_release = "complete-release" in testcase
        specfile_parse_failure = "specfile-parse-failure" in testcase

        with tempfile.TemporaryDirectory() as workdir:
            with tarfile.open(
                os.path.join(
                    __here__,
                    os.path.pardir,
                    os.path.pardir,
                    "test-data",
                    "repodata",
                    "dummy-test-package-gloster-git.tar.gz",
                )
            ) as tar:
                # Ensure unpackaged files are owned by user
                for member in tar:
                    member.uid = os.getuid()
                    member.gid = os.getgid()

                try:
                    tar.extractall(path=workdir, numeric_owner=True, filter="data")
                except TypeError:
                    # Filtering was introduced in Python 3.12.
                    tar.extractall(path=workdir, numeric_owner=True)

            unpacked_repo_dir = Path(workdir) / "dummy-test-package-gloster"

            expected_release = "11" if complete_release else 11

            if specfile_parse_failure:
                expectation = pytest.raises(SpecParseFailure)
                specfile = unpacked_repo_dir / "dummy-test-package-gloster.spec"
                txt = specfile.read_text()
                specfile.write_text("Eat this!\n" + txt)
            else:
                expectation = nullcontext()

            with mock.patch.object(rpm, "setLogFile"), expectation as excinfo:
                result = release.do_calculate_release(
                    unpacked_repo_dir,
                    complete_release=complete_release,
                    error_on_unparseable_spec=True,
                )

            if specfile_parse_failure:
                assert str(excinfo.value) == f"Couldn’t parse spec file {specfile.name}"
            else:
                assert result == expected_release

    def test_do_calculate_release_processor_error(self, repo, monkeypatch):
        monkeypatch.setenv("RPMAUTOSPEC_SPEC_PARSER", "BOO")
        with pytest.raises(SpecParseFailure):
            release.do_calculate_release(repo.workdir)

    def test_do_calculate_release_number(self):
        with mock.patch.object(release, "do_calculate_release") as do_calculate_release:
            do_calculate_release.return_value = retval_sentinel = object()

            result = release.do_calculate_release_number("some.spec")

            assert result is retval_sentinel
            do_calculate_release.assert_called_once_with(
                "some.spec",
                complete_release=False,
                error_on_unparseable_spec=True,
                git_tag_namespace=None,
            )

    def test_do_calculate_release_number_namespace(self):
        with mock.patch.object(release, "do_calculate_release") as do_calculate_release:
            release.do_calculate_release_number("some.spec", git_tag_namespace="fedora/f44")

            do_calculate_release.assert_called_once_with(
                "some.spec",
                complete_release=False,
                error_on_unparseable_spec=True,
                git_tag_namespace="fedora/f44",
            )

    @pytest.mark.parametrize("function", ("do_calculate_release", "do_calculate_release_number"))
    @pytest.mark.parametrize(
        "autochangelog_opts, namespace, expected",
        [
            pytest.param(None, None, 3, id="no-options-walks"),
            pytest.param(None, "fedora/f44", 4, id="no-options-tags"),
            pytest.param("-m tagged-only", "fedora/f44", 4, id="mode-with-namespace"),
            pytest.param("-d highest", "fedora/f44", 4, id="duplicate-with-namespace"),
            pytest.param("-m mixed-accumulated", "fedora/f44", 4, id="mixed-with-namespace"),
            pytest.param("-m tagged-only", None, "changelog-mode-without-namespace", id="mode"),
            pytest.param(
                "-d highest", None, "changelog-duplicate-without-namespace", id="duplicate"
            ),
            pytest.param(
                "-m mixed-tagged-only", None, "changelog-mode-without-namespace", id="mixed"
            ),
        ],
    )
    def test_release_only_with_spec_options(
        self, tmp_path, function, autochangelog_opts, namespace, expected
    ):
        """Options in the spec file that ask for tags need the namespace here, too.

        Without it the number would come from walking the commits, not from the tags the build
        uses, so this fails like process-distgit does instead of giving a different number.
        """
        repo_path, _ = create_tagged_repo(
            tmp_path,
            commits=["root", "tagged", "head"],
            tags=[("fedora/f44/pkg-1.0-3", 1)],
            autochangelog_opts=autochangelog_opts,
        )
        calculate = getattr(release, function)
        kwargs = {"git_tag_namespace": namespace}
        if function == "do_calculate_release":
            kwargs["complete_release"] = False

        if isinstance(expected, str):
            with pytest.raises(SpecParseFailure) as excinfo:
                calculate(repo_path, **kwargs)
            assert excinfo.value.code == expected
        else:
            assert calculate(repo_path, **kwargs) == expected
