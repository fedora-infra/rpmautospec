import datetime as dt
import subprocess
import time
from pathlib import Path

import pytest

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
