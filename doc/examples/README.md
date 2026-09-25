# RPM Macro Examples

These files demonstrate how the `%autorelease` macro looks like and can be used in a local
environment or the build system.

## The Macro Itself

The `%autorelease` macro takes a couple of parameters to allow the user to specify different
portions of the release field, as described in the [Versioning
Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/Versioning/#_simple_versioning):

* `-b <baserelease>`: Allows specifying a custom base release number (i.e. other than 1).

For compatiblity with "traditional versioning", `%autorelease` accepts `-p`, `-e <extraver>` and  `-s <snapinfo>`.
See [Traditional Versioning](https://fedora-infra.github.io/rpmautospec-docs/autorelease.html#traditional-versioning-with-part-of-the-upstream-version-information-in-the-release-field)
for details.

NB: In the prototype version the macro was named `%autorel`. To make its purpose more obvious, it is
`%autorelease` now.

## Git-Tagged Changelog Modes

When release history is recorded with git tags in a parameterized namespace, the
changelog can be generated in two modes. These files show the same set of release
tags rendered in each mode and are included in the
[documentation](https://fedora-infra.github.io/rpmautospec-docs/principle.html):

* `changelog-tagged-only.txt`: one entry per tagged commit (`--changelog-mode tagged-only`).
* `changelog-accumulated.txt`: each release also captures the commits made since the previous
  release tag, attributed to their authors (`--changelog-mode accumulated`, the default mode).

