import locale
import logging
from typing import Any, Optional

import click

from ..exc import SpecParseFailure
from ..subcommands.changelog import do_generate_changelog
from ..subcommands.convert import (
    FileModifiedError,
    FileUntrackedError,
    PkgConverter,
    SpecialFileError,
)
from ..subcommands.process_distgit import do_process_distgit
from ..subcommands.release import do_calculate_release
from ..util import handle_expected_exceptions
from . import pager
from .base import setup_logging

log = logging.getLogger(__name__)


@click.group(
    name="rpmautospec",
    epilog="Environment variable $RPMAUTOSPEC_LESS can specify pager options"
    + " (pager is currently only used by 'generate-changelog').",
)
@click.option(
    "--pager/--no-pager", help="Start a pager automatically", default=True, show_default=True
)
@click.option("--quiet", "-q", "log_level", flag_value=logging.WARNING, help="Be less talkative")
@click.option(
    "--debug",
    "log_level",
    flag_value=logging.DEBUG,
    help="Enable debugging output",
)
@click.option(
    "--error-on-unparseable-spec/--no-error-on-unparseable-spec",
    default=True,
    help="Throw an error if the current version of the spec file can’t be parsed",
    show_default=True,
)
@click.pass_context
def cli(ctx: click.Context, pager: bool, log_level: Optional[int], error_on_unparseable_spec: bool):
    locale.setlocale(locale.LC_ALL, "")

    ctx.ensure_object(dict)
    ctx.obj["pager"] = pager
    ctx.obj["log_level"] = log_level
    ctx.obj["error_on_unparseable_spec"] = error_on_unparseable_spec

    setup_logging(log_level=log_level or logging.INFO)


# Subcommands


@cli.command()
@click.argument("spec_or_path", type=click.Path(), default=".")
@click.pass_obj
@handle_expected_exceptions
def generate_changelog(obj: dict[str, Any], spec_or_path: str) -> None:
    """Generate changelog entries from git commit logs"""
    try:
        changelog = do_generate_changelog(
            spec_or_path, error_on_unparseable_spec=obj["error_on_unparseable_spec"]
        )
    except SpecParseFailure as exc:
        raise click.ClickException(exc.args[0]) from exc
    pager.page(changelog, enabled=obj["pager"])


@cli.command()
@click.option(
    "--message", "-m", required=False, help="Override message to use when committing changes"
)
@click.option(
    "--commit/--no-commit",
    " /-n",
    default=True,
    help="Commit after making changes",
    show_default=True,
)
@click.option(
    "--changelog/--no-changelog", default=True, help="Convert the RPM changelog", show_default=True
)
@click.option(
    "--release/--no-release", default=True, help="Convert the RPM release field", show_default=True
)
@click.option(
    "--signoff/--no-signoff",
    default=False,
    help="Whether or not to add a Signed-off-by: line to the commit log",
    show_default=True,
)
@click.argument("spec_or_path", type=click.Path(), default=".")
@handle_expected_exceptions
def convert(
    message: Optional[str],
    commit: bool,
    changelog: bool,
    release: bool,
    signoff: bool,
    spec_or_path: str,
) -> None:
    """Convert a package repository to use rpmautospec"""
    if commit and message == "":
        raise click.UsageError("Commit message cannot be empty")

    if not changelog and not release:
        raise click.UsageError("All changes are disabled")

    try:
        pkg = PkgConverter(spec_or_path)
    except (
        ValueError,
        FileNotFoundError,
        SpecialFileError,
        FileUntrackedError,
        FileModifiedError,
    ) as exc:
        raise click.ClickException(*exc.args) from exc

    pkg.load()
    try:
        if changelog:
            pkg.convert_to_autochangelog()
        if release:
            pkg.convert_to_autorelease()
    except SpecParseFailure as exc:
        raise click.ClickException(exc.args[0]) from exc
    pkg.save()
    if commit:
        pkg.commit(message=message, signoff=signoff)

    # print final report so the user knows what happened
    log.info(pkg.describe_changes(for_git=False))


@cli.command()
@click.argument("spec_or_path", type=click.Path())
@click.argument("target", type=click.Path())
@click.pass_obj
@handle_expected_exceptions
def process_distgit(obj: dict[str, Any], spec_or_path: str, target: str) -> None:
    """Work repository history and commit logs into a spec file"""
    try:
        do_process_distgit(
            spec_or_path, target, error_on_unparseable_spec=obj["error_on_unparseable_spec"]
        )
    except SpecParseFailure as exc:
        raise click.ClickException(exc.args[0]) from exc


@cli.command()
@click.option(
    "--complete-release/--number-only",
    "-c/-n",
    default=True,
    help="Print the complete release with flags (without dist tag) or only the calculated release"
    + " number",
    show_default=True,
)
@click.argument("spec_or_path", type=click.Path(), default=".")
@click.pass_obj
@handle_expected_exceptions
def calculate_release(obj: dict[str, Any], complete_release: bool, spec_or_path: str) -> None:
    """Calculate the next release tag for a package build"""
    try:
        release = do_calculate_release(
            spec_or_path,
            complete_release=complete_release,
            error_on_unparseable_spec=obj["error_on_unparseable_spec"],
        )
    except SpecParseFailure as exc:
        raise click.ClickException(exc.args[0]) from exc
    print("Calculated release number:", release)
