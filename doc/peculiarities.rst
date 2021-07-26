.. _peculiarities:

Peculiarities of `rpmautospec`
==============================

`rpmautospec` has few peculiarities that we are aware of. Some may get
fixed, others are considered negligible, but we still want to document them
here.


Known constraints
-----------------

One consistent release across the package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Koji builder plugin has to be able to parse the spec file of packages
outside the build root, therefore macros have the values of the Fedora release
running on the builders, not the one the package is built for. Therefore, we
can only support one release field between all sub-packages, and its contents
must not depend on other macros which may differ between Fedora versions.
I.e.: Don't use other macros than ``%autorelease`` in the release field, and
only have a release field for the main package.

Changelogs from merged history
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the commit history of a package merges branches, rpmautospec can't reliably
determine which changes contribute to the current state of the package in most
cases, e.g. in the light of conflicting changes between the merged branches.
In this case, rpmautospec will flag the issue in the changelog entry for the
merge commit like this::

    - RPMAUTOSPEC: unresolvable merge

To resolve this manually, take the applicable parts of the changelog from the
affected branches before the merge and put them in the ``changelog`` file.

The exception to this is a merge commit which shares its file tree with one or
more parents, which e.g. happens if branches are merged with ``git merge
--strategy ours``. This merge strategy means that only the file tree of one
branch is used, disregarding the contents of other branches. In this case,
rpmautospec will follow the first parent it encounters which has the same tree
as the merge commit and disregard the others.
