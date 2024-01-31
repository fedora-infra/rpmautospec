.. _using-autorelease:

**************************
The ``%autorelease`` Macro
**************************

The contents of the ``Release`` field
=====================================

Fedora's `Versioning Guidelines`_ define the different elements of which a
release field consists. They are as follows:

.. code-block:: spec

    <pkgrel>%{?dist}[.<minorbump>]

Square brackets indicate an optional item.

The ``%autorelease`` macro accepts these parameters to allow packagers to specify
the different portions of the release field:

* ``-b <baserelease>``: Allows specifying a custom base release number (the default is 1).

  For instance, this can be used to keep release numbers on older Fedora releases way lower than on
  newer ones for the same package version.

* ``-n``: Don’t render the dist tag, e.g. for use in macros, if the dist tag is added later.

.. important::
    To date, the ``%autorelease`` parameters are ignored in the headers of automatically generated
    changelog entries.

.. note::
    In the prototype version the macro was named ``%autorel``. To make its purpose more obvious, it is
    ``%autorelease`` now.


One-off bumping release numbers
===============================

You can bump the release to a higher value in a commit by adding a magic comment like this to the
commit log (one its own line)::

  [bump release: <number>]

This would ensure that the release number is at minimum the specified number (if it were higher
anyway, it would not change anything).

One use case for this would be, if a sub-package is split out into its own component and its release
number sequence should not be reset. E.g. if the last release number while it was still a
sub-package was 4, add ``[bump release: 5]`` to the commit log to let the sequence continue
seamlessly.

You don’t have to undo this later, when the version changes, the release will be reset to 1 (or the
value specified by ``%autorelease -b …``).

Examples
========

.. _simple example:

Example: The Simple Case
^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: examples/test-autorelease.spec
   :language: spec

Will generate the following NEVR::

    test-autorelease-1.0-1.fc34.x86_64


.. _baserelease example:

Example: The Custom Base Release Case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: examples/test-autorelease-baserelease.spec
   :language: spec

Will generate the following NEVR::

    test-autorelease-baserelease-1.0-100.fc34.x86_64


.. _traditional_versioning:

Traditional versioning with part of the upstream version information in the release field
=========================================================================================

Additional parameters are available to support an older form of package versioning.
This form is recommended for packages with complex versioning requirements
when support for RHEL7 and other systems with old rpm versions is required.
See `Traditional Versioning`_ in the Packaging Guidelines for details.

The release field is extended:

.. code-block:: spec

   <pkgrel>[.<extraver>][.<snapinfo>]%{?dist}[.<minorbump>]

Square brackets indicate an optional item.

The ``%autorelease`` macro accepts these parameters to allow packagers to specify
those added fields:

* ``-p``: Designates a pre-release, i.e. ``pkgrel`` will be prefixed with ``0.``.
* ``-e <extraver>``: Allows specifying the ``extraver`` portion of the release.
* ``-s <snapinfo>``: Allows specifying the ``snapinfo`` portion of the release.

In the modern versioning, those fields are embedded in the package `Version` instead.

.. _prerelease example:

Example: The Pre-Release Case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: examples/test-autorelease-prerelease.spec
   :language: spec

Will generate the following NEVR::

    test-autorelease-prerelease-1.0-0.1.pre1.fc34.x86_64


.. _extraver case:

Example: The Extraver Case
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: examples/test-autorelease-extraver.spec
   :language: spec

Will generate the following NEVR::

    test-autorelease-extraver-1.0-1.pre1.fc34.x86_64


.. _snapshot case:

Example: The Snapshot Case
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: examples/test-autorelease-snapshot.spec
   :language: spec

Will generate the following NEVR::

    test-autorelease-snapshot-1.0-1.20200317git1234abcd.fc34.x86_64


.. _snapshot_and_extraver case:

Example: The Snapshot and Extraver case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: examples/test-autorelease-extraver-snapshot.spec
   :language: spec

Will generate the following NEVR::

    test-autorelease-extraver-snapshot-1.0-1.pre1.20200317git1234abcd.fc34.x86_64


.. _Versioning Guidelines: https://docs.fedoraproject.org/en-US/packaging-guidelines/Versioning/#_simple_versioning
.. _Traditional Versioning: https://docs.fedoraproject.org/en-US/packaging-guidelines/Versioning/#_traditional_versioning_with_part_of_the_upstream_version_information_in_the_release_field
