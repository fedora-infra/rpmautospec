.. _peculiarities:

Peculiarities of `rpmautospec`
==============================

`rpmautospec` has a few peculiarities that we are aware of. Some may get
fixed, others are considered negligible, but we still want to document them
here.


Changelog Order
---------------

Build Order over Commit Date
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The changelog is generated from the commit logs in the order in which they
are encountered.
This means that depending on how your git tree is managed, with rebasing or
merge commits, you may end up with older commits showing in the history
after earlier ones. If both of these commits have been built (and therefore
tagged), they will show in the order they were built and not the order
they were committed.

For example:

::

    D: March 31st 2020     Update to 2.3.4
    |
    C: April 3rd 2020      Fix building on armv7 with gcc10
    |
    B: March 23rd 2020     Update to 1.5
    |
    A: March 20th 2019     Update to 1.0


The automatically generated changelog will look like:

::

    * Tue Mar 31 2020 Foo Bar <foo@bar.com> - 2.3.4-1
    - Update to 2.3.4

    * Fri Apr 03 2020 John Doe <john@doe.com> - 1.5-2
    - Fix building for armv7 with gcc10

    * Mon Mar 23 2020 Foo Bar <foo@bar.com> - 1.5-1
    - Update to 1.5

    * Wed Mar 20 2019 Jane Smith <jane@smith.com> - 1.0-1
    - Update to 1.0


Multiple Builds From a Given Commit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With `rpmautospec`, a commit can be rebuilt multiple times for the same
Fedora release. It will always get a newer release, so this works fine.

However, this means that we can "downgrade" a build to an older commit
without doing a ``git revert`` as long as the ``Version`` does not change
between the two commits.

Say we have the following situation:

::

    B: April 4th 2020     Add patch to fix unicode error
    |
    A: April 1st 2020     Update to 1.2


On April 1st, we built ``1.2-1`` and on April 4th ``1.2-2``. Now if there
are multiple people working on the package and one of them had not updated
their git repository since April 3rd and happens to trigger a build while
still being on commit A, the outcome will be a ``1.2-3`` build, without the
patch added in commit B.

If this happens, there will be two builds for commit A: ``1.2-1`` and
``1.2-3``. `rpmautospec` will consider the highest build when generating
the changelog, which will therefore look like:

::


    * Sat Apr 04 2020 Foo Bar <foo@bar.com> - 1.2-2
    - Add patch to fix unicode error

    * Wed Apr 01 2020 John Doe <john@doe.com> - 1.2-3
    - Update to 1.2


Old Packages Without ``changelog`` File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you opt in for an old package, remove the content of its `%changelog`
section and do not include it in a ``changelog`` file, you will have to
manually tag the old builds of this package.

You can easily do this with the `rpmautospec` CLI::

    rpmautospec tag-package --tag-all-builds /path/to/distgit/clone

The reason behind this is that to save time when building the SRPM, the
`rpmautospec` Koji plugin will only tag the latest build in every Fedora
release, but the changelog generation code uses these git tags to associate
commits with specific release, and if the tags corresponding to old builds are
missing, you will end up with changelog entry referring about an ``Update to
1.2`` while having a version-release like: ``1.3-1`` (corresponding to the
last tag available).


Scratch Builds
--------------

In Fedora, we have two ways to do scratch builds today:

- ``fedpkg build --scratch``: This basically does a regular build from a git
  reference but with ``scratch=True``. These builds will work just fine with
  `rpmautospec` as the spec file will be updated in the ``buildSRPMFromSCM``
  task, just as for regular builds.

- ``fedpkg scratch-build --srpm``, which generates an SRPM locally and uploads
  it to Koji for it to be rebuilt and be built into binary RPMS. This approach
  will not work with `rpmautospec` currently. To make this approach work with
  `rpmautospec`, you will need to process the spec file locally before
  uploading the SRPM. You can do so by simply calling::

    rpmautospec process-distgit /path/to/distgit/clone [dist-tag]


``fedpkg`` Output
-----------------

Warnings and Errors when Building
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You may run into the following warnings/errors when doing a ``fedpkg build``:

::

    warning: line 5: Possible unexpanded macro in: Release:        %autorelease
    warning: line 26: Possible unexpanded macro in: Requires:       libeconf(x86-64) = 0.3.3-%autorelease
    error: %changelog entries must start with *

This is because the ``%autorelease`` and ``%autochangelog`` RPM macros aren't
defined in your system. To fix this, simply install the
``rpmautospec-rpm-macros`` package:

::

    sudo dnf install rpmautospec-rpm-macros

Release and Changelog Differ Between Local Build and Koji
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have installed the ``rpmautospec-rpm-macros`` package as described
above and run ``fedpkg build``, you'll notice that the release is always
``-1`` (or a variant, depending on the flags used with ``%autorelease``) and that
the changelog is just one entry without useful information, even though build
in Koji would have a sequential release number and a full changelog.

This is because ``fedpkg build`` uses the placeholder RPM macros from
``rpmautospec-rpm-macros`` to keep tools such as ``rpmbuild`` or ``fedpkg
local`` working.

If you want to see how the correct release and changelog would look like, you
can call the ``rpmautospec`` CLI tool. Run ``rpmautospec --help`` for more
information.

Alternatively, you can manually override the value of the ``autorelease`` macro
for ``rpmbuild`` or ``fedpkg``, e.g.::

    fedpkg local --define "autorelease(e:s:hp) 4%{?dist}"

    rpmbuild --define "autorelease(e:s:hp) 4%{?dist}" -ba somepackage.spec
