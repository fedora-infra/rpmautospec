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

* ``-z``: Freeze the release number achieved so far into ``<pkgrel>`` and append a second,
  separate number that counts up from 1 from the commit where ``-z`` is first used onward as the
  ``<minorbump>`` of the release field format shown above. Everything else keeps its usual place:
  ``-b``/``-p``/``-e``/``-s`` (see above and below) still apply to the frozen ``<pkgrel>``, never
  to the ``<minorbump>`` counter, and the dist tag (unless ``-n`` is also given) still directly
  follows ``<pkgrel>``, same as without ``-z``. For example, instead of a plain progression of
  ``3%{?dist}``, ``4%{?dist}``, ``5%{?dist}``, …, using ``-z`` from the fourth commit onward
  produces ``3%{?dist}.1``, ``3%{?dist}.2``, ….
  This is intended for cases that need "microbumps"
  without bumping the overall release number each time, such as RHEL Z-stream.
  Dropping ``-z`` again does not resume counting where the frozen number left off;
  the plain release number simply continues increasing with every commit
  (``6%{?dist}`` in the example above), as if ``-z`` had never been used.

.. important::
    To date, the ``%autorelease`` parameters are ignored in the headers of automatically generated
    changelog entries.

.. note::
    In the prototype version the macro was named ``%autorel``. To make its purpose more obvious, it is
    ``%autorelease`` now.


One-off bumping release numbers
===============================

You can bump the release to a higher value in a commit by adding a magic comment like this to the
commit log (on its own line)::

  [bump release: <number>]

This would ensure that the release number is at minimum the specified number (if it were higher
anyway, it would not change anything).

One use case for this would be, if a sub-package is split out into its own component and its release
number sequence should not be reset. E.g. if the last release number while it was still a
sub-package was 4, add ``[bump release: 5]`` to the commit log to let the sequence continue
seamlessly.

You don’t have to undo this later, when the version changes, the release will be reset to 1 (or the
value specified by ``%autorelease -b …``).

While ``-z`` (see above) is in use, ``[bump release: <number>]`` applies to the frozen ``<pkgrel>``
part instead, the same "before-the-dist" portion ``-b`` applies to, and never to the ``<minorbump>``
counter after it. It persists for the rest of that ``-z`` run the same way it would for the plain
release number, but has no effect on the plain release number itself: once ``-z`` is dropped again,
the release number simply continues from where it would have been without the bump.

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


.. _freeze example:

Example: The Freeze (``-z``) Case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: examples/test-autorelease-z.spec
   :language: spec

Will generate the following NEVR::

    test-autorelease-z-1.0-0.fc34.1.x86_64

The ``0`` right after ``1.0-`` is the frozen release number, filling the ``<pkgrel>`` slot
(there was nothing to freeze yet, since there were no commits before adding ``-z``, hence ``0``),
the dist tag ``fc34`` follows it directly, same as without ``-z``,
and the ``1`` after that is the ``<minorbump>``, the separate, second number ``-z`` starts counting
from 1. A later rebuild would produce ``...-0.fc34.2...``, and so on, until ``-z`` is dropped again.

Combined with ``-b``/``-p``/``-e``/``-s`` (see above and below), those still apply to the frozen
``<pkgrel>``, never to the ``<minorbump>`` counter, e.g. ``%autorelease -z -p`` would produce
``0.0.fc34.1`` (the extra ``0.`` prefix marking a pre-release of ``0``), and ``%autorelease -z -b
100`` would produce ``99.fc34.1`` (the base shifts ``<pkgrel>`` from ``0`` to ``99``, the
``<minorbump>`` count of ``1`` is unaffected).

``-e``/``-s`` are inserted right after ``<pkgrel>``, before the dist tag, same as without ``-z``,
with ``<minorbump>`` still tacked on at the very end. For example, ``%autorelease -z -e rc1`` would
produce ``0.rc1.fc34.1``: ``0`` is the frozen ``<pkgrel>``, ``rc1`` the extraver right after it,
``fc34`` the dist tag, and the final ``1`` the ``<minorbump>`` count.


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
