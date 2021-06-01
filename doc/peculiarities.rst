.. _peculiarities:

Peculiarities of `rpmautospec`
==============================

`rpmautospec` has a few peculiarities that we are aware of. Some may get
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


Scratch & Local Builds
----------------------

In Fedora, there are two ways to do scratch builds today:

- ``fedpkg build --scratch``: This basically does a regular build from a git
  reference but with ``scratch=True``. These builds will work just fine with
  `rpmautospec` as the spec file will be updated in the ``buildSRPMFromSCM``
  task, just as for regular builds.

- ``fedpkg scratch-build --srpm``, which generates an SRPM locally and uploads
  it to Koji for it to be built into binary RPMS. This approach will not work
  with `rpmautospec` currently. We plan to make ``fedpkg scratch-build``
  preprocess the generated SRPM in this case, just as for ``fedpkg srpm`` and
  ``fedpkg mockbuild``.

  For the time being, you can process the spec file locally before
  uploading the SRPM by calling:

  ::

      rpmautospec process-distgit /path/to/distgit/clone

  .. warning::
      This is a tool we use for testing and debugging. It changes the spec
      file and you need to undo these changes before running the tool again or
      committing other changes in it to git, etc.


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
the changelog is just one entry without useful information, even though if you build
in Koji, it would have a sequential release number and a full changelog.

This is because ``fedpkg build`` uses the placeholder RPM macros from
``rpmautospec-rpm-macros`` to keep tools such as ``rpmbuild`` or ``fedpkg
local`` working.

If you want to see how the correct release and changelog would look like, you
can call the ``rpmautospec`` CLI tool. Run ``rpmautospec --help`` for more
information.

Alternatively, you can manually override the value of the ``autorelease`` macro
for ``rpmbuild`` or ``fedpkg``, e.g.::

    fedpkg local --define "autorelease(e:s:pb:) 4%{?dist}"

    rpmbuild --define "autorelease(e:s:pb:) 4%{?dist}" -ba somepackage.spec
