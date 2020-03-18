# RPM Macro Examples

These files demonstrate how the `%autorel` macro looks like and can be used in a local environment
or the build system.

## The Macro Itself

The `%autorel` macro takes a couple of parameters to allow the user to specify different portions of
the release field, as described in the [Versioning
Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/Versioning/#_more_complex_versioning):

* `-h`, "hotfix": Designates a hotfix release, i.e. enables bumping the `minorbump` portion in order
  to not overrun EVRs in later Fedora versions.
* `-p`, "prerelease": Designates a pre-release, i.e. the left-most digit of `pkgrel` will be `0`.
* `-e <extraver>`: Allows specifying the `extraver` portion of the release.
* `-s <snapinfo>`: Allows specifying the `snapinfo` portion of the release.

## Local Use Case

The file `macros.autorel` would make the macro available if placed into `/usr/lib/rpm/macros.d`. It
also contains default values so a user can run plain RPM commands on the spec file.

To try it out, run:

    rpm --load macros.autorel --specfile test-autorel.spec

## Build System Use Case

The file `autorel-function-hdr.txt` contains the definition block as it would be pasted on top of
the spec file during the buildSRPMFromSCM Koji task. At the top, it contains the results of the
release value as calculated by `rpmautospec.release`, for the different use cases and with RPM
macros as placeholders for portions of the release field which the algorithm doesn't (need to) know
about. This is followed by the `%autorel` macro as it is defined at build time, overriding anything
from `macros.autorel` above to ensure repeatable builds of the resulting SRPM.

To test, concatenate the header blurb and any of the `test-autorel*.spec` files and run rpm on the
resulting spec file, like this:

    cat autorel-function-hdr.txt test-autorel.spec > foo.spec
    rpm --specfile foo.spec
