.. _using-autorelease:

Using the ``%autorelease`` Macro
================================

Fedora's `Versioning Guidelines`_ define the different elements of which a
release field consists. They are as follows:

::

    <pkgrel>[.<extraver>][.<snapinfo>]%{?dist}[.<minorbump>]

Each element in square brackets indicates an optional item.

The ``%autorelease`` macro accepts these parameters to allow packagers to specify
the different portions of the release field:

* ``-p``: Designates a pre-release, i.e. ``pkgrel`` will be prefixed with ``0.``.
* ``-e <extraver>``: Allows specifying the ``extraver`` portion of the release.
* ``-s <snapinfo>``: Allows specifying the ``snapinfo`` portion of the release.
* ``-b <baserelease>``: Allows specifying a custom base release number (i.e. other than 1).


.. important::
    To date, the ``%autorelease`` parameters are ignored in the headers of automatically generated
    changelog entries.

.. note::
    In the prototype version the macro was named ``%autorel``. To make its purpose more obvious, it is
    ``%autorelease`` now.

Examples
--------

.. _simple example:

The Simple Case
^^^^^^^^^^^^^^^

.. include:: examples/test-autorelease.spec
   :literal:

Will generate the following NEVR:

::

    test-autorelease-1.0-1.fc34.x86_64


.. _baserelease example:

The Custom Base Release Case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorelease-baserelease.spec
   :literal:

Will generate the following NEVR:

::

    test-autorelease-baserelease-1.0-100.fc34.x86_64


.. _prerelease example:

The Pre-Release Case
^^^^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorelease-prerelease.spec
   :literal:

Will generate the following NEVR:

::

    test-autorelease-prerelease-1.0-0.1.pre1.fc34.x86_64


.. _extraver case:

The Extraver Case
^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorelease-extraver.spec
   :literal:

Will generate the following NEVR:

::

    test-autorelease-extraver-1.0-1.pre1.fc34.x86_64


.. _snapshot case:

The Snapshot Case
^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorelease-snapshot.spec
   :literal:

Will generate the following NEVR:

::

    test-autorelease-snapshot-1.0-1.20200317git1234abcd.fc34.x86_64


.. _snapshot_and_extraver case:

The Snapshot and Extraver case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorelease-extraver-snapshot.spec
   :literal:

Will generate the following NEVR:

::

    test-autorelease-extraver-snapshot-1.0-1.pre1.20200317git1234abcd.fc34.x86_64


.. _Versioning Guidelines: https://docs.fedoraproject.org/en-US/packaging-guidelines/Versioning/#_more_complex_versioning
