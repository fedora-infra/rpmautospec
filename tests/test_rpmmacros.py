import datetime as dt
import subprocess
import time
from pathlib import Path

import pytest

from rpmautospec.subcommands.process_distgit import AUTORELEASE_TEMPLATE

HERE = Path(__file__).parent
MACROS_FILE = HERE.parent / "rpm_macros.d" / "macros.rpmautospec"


@pytest.mark.parametrize("nodisttag", (False, True))
@pytest.mark.parametrize("base", (None, 10))
@pytest.mark.parametrize("prerelease", (False, True))
@pytest.mark.parametrize("snapshot", (None, "19700101"))
@pytest.mark.parametrize("extra", (None, "ilikeunsortableversions"))
@pytest.mark.parametrize("braces", (False, True))
def test_autorelease(braces, extra, snapshot, prerelease, base, nodisttag):
    expected = ""
    if braces:
        autorelease_macro = "%{autorelease"
    else:
        autorelease_macro = "%autorelease"

    if extra:
        autorelease_macro += f" -e {extra}"
        expected += f".{extra}"

    if snapshot:
        autorelease_macro += f" -s {snapshot}"
        expected += f".{snapshot}"

    if base:
        autorelease_macro += f" -b {base}"
        expected = "10" + expected
    else:
        expected = "1" + expected

    if prerelease:
        autorelease_macro += " -p"
        expected = "0." + expected

    if nodisttag:
        autorelease_macro += " -n"
    else:
        expected += ".DIST"

    if braces:
        autorelease_macro += "}"

    rpm_result = (
        subprocess.check_output(
            (
                "rpm",
                # `rpm --load ...` needs at least rpm-4.15
                "--macros",
                str(MACROS_FILE.absolute()),
                "--define",
                "%dist .DIST",
                "--eval",
                autorelease_macro,
            )
        )
        .decode("UTF-8")
        .strip()
    )

    assert rpm_result == expected


GATE = "_rpmautospec_test_gate"


def _gated(text):
    """The text with the test that picks the branch swapped for a macro the test can set.

    The real test is %rpmversion, which rpm 4.18.2 and later define as a builtin, but then
    a test cannot make an rpm take the other branch either.
    """
    assert "%{?rpmversion:" in text and "%{!?rpmversion:" in text
    return text.replace("%{?rpmversion:", f"%{{?{GATE}:").replace(
        "%{!?rpmversion:", f"%{{!?{GATE}:"
    )


def _rpm_has_expressions():
    result = subprocess.run(
        ("rpm", "--eval", "%[ 1 + 1 ]"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    return result.stdout.decode("UTF-8").strip() == "2"


def _autorelease(*rpm_args, base):
    macro = "%autorelease -n" + (f" -b {base}" if base else "")
    result = subprocess.check_output(
        ("rpm", *rpm_args, "--define", "_rpmautospec_release_number 2", "--eval", macro)
    )
    return result.decode("UTF-8").strip().splitlines()[-1]


@pytest.mark.parametrize("base", (None, 10))
@pytest.mark.parametrize("branch", ("lua", "expression"))
def test_autorelease_branches(branch, base, tmp_path):
    """Both ways of computing the number give it once, whatever rpm the tests run on.

    rpm 4.16 once wrote the number twice (22 for 2) because %{?expr:} picked the branch.
    """
    select = ()
    if branch == "expression":
        if not _rpm_has_expressions():
            pytest.skip("rpm has no %[ ] expressions")
        select = ("--define", f"{GATE} 1")
    macros = tmp_path / "macros.rpmautospec"
    macros.write_text(_gated(MACROS_FILE.read_text()))

    # Only the macro file is loaded, so the branch is the one the test selects.
    result = _autorelease("--macros", str(macros), *select, base=base)

    assert result == ("11" if base else "2")


def _processed_autorelease(*rpm_args, definition, base):
    """%autorelease as the definition that process-distgit writes into the spec file gives it."""
    macro = "%autorelease -n" + (f" -b {base}" if base else "")
    result = subprocess.check_output(("rpm", *rpm_args, "--eval", definition, "--eval", macro))
    return result.decode("UTF-8").strip().splitlines()[-1]


@pytest.mark.parametrize("base", (None, 10))
@pytest.mark.parametrize("branch", ("lua", "expression"))
def test_processed_autorelease_branches(branch, base):
    """The definition in a processed spec file gives the number once with either branch."""
    select = ()
    if branch == "expression":
        if not _rpm_has_expressions():
            pytest.skip("rpm has no %[ ] expressions")
        select = ("--define", f"{GATE} 1")
    definition = _gated(AUTORELEASE_TEMPLATE.format(autorelease_number=2))

    assert _processed_autorelease(*select, definition=definition, base=base) == (
        "11" if base else "2"
    )


@pytest.mark.parametrize("base", (None, 10))
def test_processed_autorelease_branch_of_this_rpm(base):
    """With the test as it is, the processed spec file picks its branch as it does in a build."""
    definition = AUTORELEASE_TEMPLATE.format(autorelease_number=2)

    assert _processed_autorelease(definition=definition, base=base) == ("11" if base else "2")


@pytest.mark.parametrize("epoch", (None, 2))
@pytest.mark.parametrize("packager", (None, "Foo Bar <foo@bar.com>"))
def test_autochangelog(packager, epoch):
    rpm_params = (
        "rpm",
        # `rpm --load ...` needs at least rpm-4.15
        "--macros",
        str(MACROS_FILE.absolute()),
        "--define",
        "%version 1",
        "--define",
        "%release 1",
    )

    if packager:
        rpm_params += ("--define", f"%packager {packager}")
    else:
        rpm_params += ("--undefine", "%packager")
    expected_packager = packager or "John Doe <packager@example.com>"

    if epoch:
        rpm_params += ("--define", f"%epoch {epoch}")
        expected_evr = "2:1-1"
    else:
        expected_evr = "1-1"

    rpm_params += ("--eval", "%autochangelog")

    now = dt.datetime.now()

    # If closer than 5 seconds to local midnight, delay running the test until after.
    midnight = (now + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = midnight - now
    if remaining < dt.timedelta(seconds=5):
        time.sleep(remaining.total_seconds() + 1)
        now = dt.datetime.now()

    expected_date = now.strftime("%a %b %d %Y")

    rpm_result = subprocess.check_output(rpm_params).decode("UTF-8").strip()

    header, entry = rpm_result.split("\n")

    assert header == f"* {expected_date} {expected_packager} - {expected_evr}"
    assert entry == "- local build"
