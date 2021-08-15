# RPM Macro Examples

These files demonstrate how the `%autorelease` macro looks like and can be used in a local
environment or the build system.

## The Macro Itself

The `%autorelease` macro takes a couple of parameters to allow the user to specify different
portions of the release field, as described in the [Versioning
Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/Versioning/#_simple_versioning):

* `-b <baserelease>`: Allows specifying a custom base release number (i.e. other than 1).

For compatiblity with "traditional versioning", `%autorelease` accepts `-p`, `-e <extraver>` and  `-s <snapinfo>`.
See [Traditional Versioning](https://docs.pagure.org/fedora-infra.rpmautospec/autorelease.html/#_traditional_versioning)
for details.

NB: In the prototype version the macro was named `%autorel`. To make its purpose more obvious, it is
`%autorelease` now.
