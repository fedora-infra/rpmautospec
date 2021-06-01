# RPM Macro Examples

These files demonstrate how the `%autorelease` macro looks like and can be used in a local
environment or the build system.

## The Macro Itself

The `%autorelease` macro takes a couple of parameters to allow the user to specify different
portions of the release field, as described in the [Versioning
Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/Versioning/#_more_complex_versioning):

* `-p`, "prerelease": Designates a pre-release, i.e. the left-most digit of `pkgrel` will be `0`.
* `-e <extraver>`: Allows specifying the `extraver` portion of the release.
* `-s <snapinfo>`: Allows specifying the `snapinfo` portion of the release.
* `-b <baserelease>`: Allows specifying a custom base release number (i.e. other than 1).

NB: In the prototype version the macro was named `%autorel`. To make its purpose more obvious, it is
`%autorelease` now.
