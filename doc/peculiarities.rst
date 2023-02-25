.. _peculiarities:

******************************
Peculiarities of `rpmautospec`
******************************

`rpmautospec` has few peculiarities that we are aware of. Some may get
fixed, others are considered negligible, but we still want to document them
here.


Known constraints
-----------------

Package versions must be determinable from the spec file alone
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Both the Koji plugin and ``fedpkg`` preprocess package spec files outside of
the target build root. If the version field of a package depends on macros
not defined in the spec file (directly or indirectly), this will likely result
in unexpected behavior if the macros in question differ between the environment
of the target and that where preprocessing happens.

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


Rebuilding a package with no changes
------------------------------------

In the past, rebuilding a package to pick up changed dependencies or
in the context of mass rebuilds was accomplished by bumping the
release and adding a suitable changelog entry and creating a commit.
With `rpmautospec`, we only need the last step.
But you have to tell git that you really want to add a
commit without any changes:

.. code-block:: bash

    git commit --allow-empty -m 'Rebuild for …'

The resulting empty commit can be pushed into the repository of the package and built normally.


Information about `rpmautospec` use in a built package
------------------------------------------------------

When preprocessing spec files for building, `rpmautospec` adds a header to the
top of the spec file containing, among other things, information about its
version and which features are used, e.g.:

.. code-block::

    ## START: Set by rpmautospec
    ## (rpmautospec version 0.3.0)
    ## RPMAUTOSPEC: autorelease, autochangelog
    ...
    ## END: Set by rpmautospec

The preprocessed spec file is available in the SRPM which is generated as part
of a package build.
