.. _using-autorel:

Using the ``%autorel`` macro
============================

Fedora's `Versioning Guidelines`_ define the different element that can
compose a release field as follow:

::

    <pkgrel>[.<extraver>][.<snapinfo>]%{?dist}[.<minorbump>]

Where each element in square brackets indicates an optional item.


The ``%autorel`` macro accepts therefore some parameters to allow the packagers
to specify the different portions of the release field:

* ``-h <hotfix>``: Designates a hotfix release, i.e. enables bumping the
  ``minorbump`` portion in order to not overrun EVRs in later Fedora versions.
* ``-p <prerelease>``: Designates a pre-release, i.e. ``pkgrel`` will be prefixed
  with ``0.``.
* ``-e <extraver>``: Allows specifying the ``extraver`` portion of the release.
* ``-s <snapinfo>``: Allows specifying the ``snapinfo`` portion of the release.


Some examples:
--------------

.. _simple example:

The simple case
^^^^^^^^^^^^^^^

.. include:: examples/test-autorel.spec
   :literal:

Will generate the following NEVR:

::

    test-autorel-1.0-1.fc31.x86_64


.. _hotfix example:

The hotfix case
^^^^^^^^^^^^^^^

.. include:: examples/test-autorel-hotfix.spec
   :literal:

Will generate the following NEVR:

::

    test-autorel-hotfix-1.0-1.fc31.1.x86_64


.. _prerelease example:

The prerelease case
^^^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorel-prerelease.spec
   :literal:

Will generate the following NEVR:

::

    test-autorel-prerelease-1.0-0.1.pre1.fc31.x86_64


.. _extraver case:

The extraver case
^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorel-extraver.spec
   :literal:

Will generate the following NEVR:

::

    test-autorel-extraver-1.0-1.pre1.fc31.x86_64


.. _snapshot case:

The snapshot case
^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorel-snapshot.spec
   :literal:

Will generate the following NEVR:

::

    test-autorel-snapshot-1.0-1.20200317git1234abcd.fc31.x86_64


.. _snapshot_and_extraver case:

The snapshot and extraver case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: examples/test-autorel-extraver-snapshot.spec
   :literal:

Will generate the following NEVR:

::

    test-autorel-extraver-snapshot-1.0-1.pre1.20200317git1234abcd.fc31.x86_64


.. _Versioning Guidelines: https://docs.fedoraproject.org/en-US/packaging-guidelines/Versioning/#_more_complex_versioning
