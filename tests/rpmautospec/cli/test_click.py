import itertools
import logging
from shutil import SpecialFileError
from unittest import mock

import pytest

from rpmautospec.compat import rpm
from rpmautospec.exc import SpecParseFailure

from ...common import gen_testrepo

_click_testing = pytest.importorskip("click.testing")
if _click_testing:
    CliRunner = _click_testing.CliRunner

cli_click = pytest.importorskip("rpmautospec.cli.click")


@pytest.fixture
def cli_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)  # click < 8.2
    except TypeError:
        return CliRunner()  # click >= 8.2


def test_cli_help(cli_runner):
    """Test that getting top-level help works"""
    result = cli_runner.invoke(cli_click.cli, ["--help"])

    assert result.exit_code == 0

    assert "Usage: rpmautospec" in result.stdout
    assert not result.stderr


def test_cli(cli_runner):
    @cli_click.cli.command(hidden=True)
    def test():
        pass

    with mock.patch.object(cli_click, "setup_logging") as setup_logging:
        result = cli_runner.invoke(cli_click.cli, ["test"])

    assert result.exit_code == 0

    setup_logging.assert_called_with(log_level=logging.INFO)


@pytest.mark.parametrize(
    "mode, duplicate, namespace",
    itertools.product(
        (None, "walk", "accumulated", "tagged-only", "mixed-accumulated", "mixed-tagged-only"),
        (None, "lowest", "highest"),
        (None, "fedora/f44"),
    ),
)
def test_mode_option_matrix(mode, duplicate, namespace, cli_runner):
    """Every combination of the changelog options is handed on, or rejected without a namespace."""
    seen = {}

    @cli_click.cli.command(name="capture", hidden=True)
    @cli_click.click.pass_obj
    def capture(obj):
        seen.update(obj)

    args = []
    if namespace:
        args += ["--git-tag-namespace", namespace]
    if mode:
        args += ["--changelog-mode", mode]
    if duplicate:
        args += ["--changelog-duplicate-tag", duplicate]

    result = cli_runner.invoke(cli_click.cli, [*args, "capture"])

    if not namespace and mode not in (None, "walk"):
        # Asking for tags without a namespace is a mistake, not something to ignore
        assert result.exit_code == 2
        assert f"--changelog-mode {mode} needs --git-tag-namespace" in result.stderr
        assert not seen
    elif not namespace and duplicate == "highest":
        assert result.exit_code == 2
        assert "--changelog-duplicate-tag highest needs --git-tag-namespace" in result.stderr
        assert not seen
    else:
        assert result.exit_code == 0
        assert seen["git_tag_namespace"] == namespace
        assert seen["changelog_mode"] == mode
        assert (
            seen["changelog_use_highest_release_tag"]
            == {
                None: None,
                "lowest": False,
                "highest": True,
            }[duplicate]
        )


def test_changelog_options_help(cli_runner):
    """The help states the defaults and that the spec file overrides the options."""
    result = cli_runner.invoke(cli_click.cli, ["--help"])

    assert result.exit_code == 0
    help_text = " ".join(result.stdout.split())
    assert (
        "--changelog-mode [walk|accumulated|tagged-only|mixed-accumulated|mixed-tagged-only]"
        in help_text
    )
    assert "--changelog-duplicate-tag [lowest|highest]" in help_text
    assert "Default: walk, or accumulated with --git-tag-" in help_text
    assert "Default: lowest" in help_text
    assert "%autochangelog -m" in help_text and "%autochangelog -d" in help_text


@pytest.mark.parametrize("testcase", ("success", "specfile-parse-failure"))
def test_generate_changelog(testcase, cli_runner):
    with (
        mock.patch.object(cli_click, "do_generate_changelog") as do_generate_changelog,
        mock.patch.object(cli_click, "pager") as pager,
    ):
        pager_sentinel = object()
        error_on_unparseable_spec_sentinel = object()

        ctx_obj = {
            "pager": pager_sentinel,
            "error_on_unparseable_spec": error_on_unparseable_spec_sentinel,
            "git_tag_namespace": None,
            "changelog_mode": None,
            "changelog_use_highest_release_tag": None,
        }

        if "specfile-parse-failure" in testcase:
            do_generate_changelog.side_effect = cli_click.SpecParseFailure("BOO")

        result = cli_runner.invoke(cli_click.generate_changelog, ["some_path"], obj=ctx_obj)

        do_generate_changelog.assert_called_once_with(
            "some_path",
            error_on_unparseable_spec=error_on_unparseable_spec_sentinel,
            git_tag_namespace=None,
            changelog_mode=None,
            changelog_use_highest_release_tag=None,
        )

        if "success" in testcase:
            assert result.exit_code == 0

            pager.page.assert_called_once_with(
                do_generate_changelog.return_value, enabled=pager_sentinel
            )
        else:
            assert result.exit_code != 0
            assert "Error: BOO" in result.stderr

            pager.page.assert_not_called()


class TestConvertCommand:
    @mock.patch.object(cli_click, "PkgConverter")
    def test_convert_empty_commit_message(self, PkgConverter, cli_runner, specfile):
        result = cli_runner.invoke(
            cli_click.convert, ["--commit", "--message=", str(specfile)], catch_exceptions=False
        )
        assert result.exit_code != 0
        assert "Error: Commit message cannot be empty" in result.stderr

    @mock.patch.object(cli_click, "PkgConverter")
    def test_convert_no_changes(self, PkgConverter, cli_runner, specfile):
        result = cli_runner.invoke(
            cli_click.convert,
            ["--no-changelog", "--no-release", str(specfile)],
            catch_exceptions=False,
        )
        assert result.exit_code != 0
        assert "Error: All changes are disabled" in result.stderr

    @mock.patch.object(cli_click, "PkgConverter")
    @pytest.mark.parametrize(
        "with_release, with_changelog",
        ((True, True), (True, False), (False, True)),
        ids=(
            "with-release-with-changelog",
            "with-release-without-changelog",
            "without-release-without-changelog",
        ),
    )
    @pytest.mark.parametrize(
        "with_commit, with_signoff",
        ((True, False), (True, True), (False, False)),
        ids=("with-commit-without-signoff", "with-commit-with-signoff", "without-commit"),
    )
    def test_convert_valid_args(
        self,
        PkgConverter,
        with_release,
        with_changelog,
        with_commit,
        with_signoff,
        specfile,
        cli_runner,
    ):
        PkgConverter.return_value = pkg_converter = mock.MagicMock()

        args = [
            "--release" if with_release else "--no-release",
            "--changelog" if with_changelog else "--no-changelog",
            "--commit" if with_commit else "--no-commit",
            "--signoff" if with_signoff else "--no-signoff",
            "--message=message",
            str(specfile),
        ]

        result = cli_runner.invoke(cli_click.convert, args)

        assert result.exit_code == 0

        pkg_converter.load.assert_called_once()

        if with_changelog:
            pkg_converter.convert_to_autochangelog.assert_called_once_with()
        else:
            pkg_converter.convert_to_autochangelog.assert_not_called()

        if with_release:
            pkg_converter.convert_to_autorelease.assert_called_once_with()
        else:
            pkg_converter.convert_to_autorelease.assert_not_called()

        pkg_converter.save.assert_called()

        if with_commit:
            pkg_converter.commit.assert_called_once_with(message="message", signoff=with_signoff)
        else:
            pkg_converter.commit.assert_not_called()

    @pytest.mark.parametrize(
        "method, exception",
        (
            ("__init__", ValueError),
            ("__init__", FileNotFoundError),
            ("__init__", SpecialFileError),
            ("__init__", cli_click.FileUntrackedError),
            ("__init__", cli_click.FileModifiedError),
            ("convert_to_autorelease", SpecParseFailure),
            ("convert_to_autochangelog", SpecParseFailure),
        ),
    )
    @mock.patch.object(cli_click, "PkgConverter")
    def test_rewrap_exceptions(self, PkgConverter, method, exception, cli_runner, specfile):
        if method == "__init__":
            PkgConverter.side_effect = exception("BOOP")
        else:
            obj = PkgConverter.return_value
            getattr(obj, method).side_effect = exception("BOOP")

        result = cli_runner.invoke(cli_click.convert, str(specfile))
        assert result.exit_code != 0
        assert "Error: BOOP" in result.stderr


@pytest.mark.parametrize(
    "testcase", ("locale-unset", "locale-C", "locale-de", "specfile-parse-failure")
)
def test_process_distgit(testcase, tmp_path, locale, cli_runner):
    override_locale = False
    if "locale-C" in testcase:
        override_locale = "C"
    elif "locale-de" in testcase:
        override_locale = "de_DE.UTF-8"

    output_spec_file = tmp_path / "test.spec"
    unpacked_repo_dir, test_spec_file_path = gen_testrepo(tmp_path, "rawhide")

    args = [str(test_spec_file_path), str(output_spec_file)]
    ctx_obj = {
        "error_on_unparseable_spec": object(),
        "git_tag_namespace": None,
        "changelog_mode": None,
        "changelog_use_highest_release_tag": None,
    }

    if override_locale:
        locale.setlocale(locale.LC_ALL, override_locale)

    with (
        mock.patch.object(
            cli_click, "do_process_distgit", wraps=cli_click.do_process_distgit
        ) as do_process_distgit_fn,
        mock.patch.object(rpm, "setLogFile"),  # rpm can’t cope with fake sys.stderr
    ):
        if "specfile-parse-failure" in testcase:
            do_process_distgit_fn.side_effect = cli_click.SpecParseFailure("BOO")
        result = cli_runner.invoke(cli_click.process_distgit, args, obj=ctx_obj)

    do_process_distgit_fn.assert_called_once_with(
        str(test_spec_file_path),
        str(output_spec_file),
        error_on_unparseable_spec=ctx_obj["error_on_unparseable_spec"],
        git_tag_namespace=ctx_obj["git_tag_namespace"],
        changelog_mode=ctx_obj["changelog_mode"],
        changelog_use_highest_release_tag=ctx_obj["changelog_use_highest_release_tag"],
    )

    if "specfile-parse-failure" in testcase:
        assert result.exit_code != 0
        assert "Error: BOO" in result.stderr
    else:
        assert result.exit_code == 0


@pytest.mark.parametrize("testcase", ("complete-release", "number-only", "specfile-parse-failure"))
def test_calculate_release(testcase, cli_runner):
    complete_release = "complete-release" in testcase
    specfile_parse_failure = "specfile-parse-failure" in testcase

    args = ["/foo/bar", "--complete-release" if complete_release else "--number-only"]
    ctx_obj = {
        "error_on_unparseable_spec": object(),
        "git_tag_namespace": None,
        "changelog_mode": None,
        "changelog_use_highest_release_tag": None,
    }

    with mock.patch.object(cli_click, "do_calculate_release") as do_calculate_release:
        if specfile_parse_failure:
            do_calculate_release.side_effect = cli_click.SpecParseFailure("GNA")
        else:
            if complete_release:
                do_calculate_release.return_value = "8"
            else:
                do_calculate_release.return_value = 6

        result = cli_runner.invoke(cli_click.calculate_release, args, obj=ctx_obj)

    do_calculate_release.assert_called_once_with(
        "/foo/bar",
        complete_release=complete_release,
        error_on_unparseable_spec=ctx_obj["error_on_unparseable_spec"],
        git_tag_namespace=ctx_obj["git_tag_namespace"],
    )

    if specfile_parse_failure:
        assert result.exit_code != 0
        assert "Error: GNA" in result.stderr
    else:
        assert result.exit_code == 0
        expected_rel = "8" if complete_release else "6"
        assert f"Calculated release number: {expected_rel}" in result.stdout
