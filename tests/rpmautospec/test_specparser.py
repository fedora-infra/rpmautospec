import itertools

import pytest
from rpmautospec_core import AUTOCHANGELOG_MACRO

from rpmautospec.specparser import AUTOCHANGELOG_DEFINITION, AutoSpecParser

SPEC_TEMPLATE = """Name: pkg
Version: 1.0
Release: %autorelease{release_options}
Summary: Test package
License: MIT

%description
Test

%changelog
%autochangelog{changelog_options}
"""

MODES = ("accumulated", "tagged-only", "mixed-accumulated", "mixed-tagged-only")
DUPLICATES = ("lowest", "highest")

# Every way to set the options of %autochangelog, 23 in total.
CHANGELOG_OPTIONS = [
    "",
    *(f" -m {mode}" for mode in MODES),
    *(f" -d {duplicate}" for duplicate in DUPLICATES),
    *(
        f" {first} {second}"
        for mode, duplicate in itertools.product(MODES, DUPLICATES)
        for first, second in ((f"-m {mode}", f"-d {duplicate}"), (f"-d {duplicate}", f"-m {mode}"))
    ),
]


@pytest.fixture(params=["rpm", "norpm"])
def query(request, tmp_path, monkeypatch):
    if request.param == "norpm":
        pytest.importorskip("norpm")
    monkeypatch.setenv("RPMAUTOSPEC_SPEC_PARSER", request.param)

    def _query(release_options="", changelog_options=""):
        specfile = tmp_path / "pkg.spec"
        specfile.write_text(
            SPEC_TEMPLATE.format(
                release_options=release_options, changelog_options=changelog_options
            )
        )
        return AutoSpecParser().query(str(tmp_path), str(specfile))

    return _query


@pytest.mark.parametrize("changelog_options", CHANGELOG_OPTIONS)
def test_autochangelog_macro_matrix(query, changelog_options):
    """The options of %autochangelog are accepted and don't leak into the parsed spec file."""
    assert query(changelog_options=changelog_options) == ("1.0", "E_S_P0_B")


@pytest.mark.parametrize("changelog_options", CHANGELOG_OPTIONS)
def test_autochangelog_macro_expands_to_nothing(changelog_options):
    """A macro without an option list would append its arguments to the expansion."""
    rpm = pytest.importorskip("rpm")
    try:
        rpm.expandMacro(f"%define {AUTOCHANGELOG_MACRO} {AUTOCHANGELOG_DEFINITION}")
        assert rpm.expandMacro(f"%autochangelog{changelog_options}") == ""
    finally:
        rpm.reloadConfig()


@pytest.mark.parametrize("changelog_options", CHANGELOG_OPTIONS)
@pytest.mark.parametrize(
    "extraver, snapinfo, prerelease, base, no_dist",
    itertools.product((None, "x"), (None, "y"), (False, True), (None, 5), (False, True)),
)
def test_autorelease_macro_matrix(
    query, changelog_options, extraver, snapinfo, prerelease, base, no_dist
):
    """%autorelease and its flags token are the same whatever %autochangelog is given."""
    options = "".join(
        option
        for option in (
            f" -e {extraver}" if extraver else "",
            f" -s {snapinfo}" if snapinfo else "",
            " -p" if prerelease else "",
            f" -b {base}" if base else "",
            " -n" if no_dist else "",
        )
    )
    expected_token = f"E{extraver or ''}_S{snapinfo or ''}_P{int(prerelease)}_B{base or ''}"

    assert query(release_options=options, changelog_options=changelog_options) == (
        "1.0",
        expected_token,
    )
