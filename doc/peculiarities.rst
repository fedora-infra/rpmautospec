.. _peculiarities:

Peculiarities of `rpmautospec`
==============================

`rpmautospec` has few peculiarities that we are aware of. Some may get
fixed, others are considered negligible, but we still want to document them
here.


Known constraints
-----------------

The Koji builder plugin has to be able to parse the spec file of packages
outside the build root, therefore macros have the values of the Fedora release
running on the builders, not the one the package is built for. Therefore, we
can only support one release field between all sub-packages, and its contents
must not depend on other macros which may differ between Fedora versions.
I.e.: Don't use other macros than ``%autorelease`` in the release field, and
only have a release field for the main package.
