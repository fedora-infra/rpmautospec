*******************
Using `rpmautospec`
*******************

To use `rpmautospec` you need to employ the two macros described below.

Using the ``%autorelease`` macro
--------------------------------

Basically, in the spec file you replace the manually-set release, e.g.:

.. code-block:: spec

    Release:    7{%dist}

with the ``%autorelease`` macro, such as:

.. code-block:: spec

    Release:    %autorelease

.. warning::
    Often, changing to automatic releases will result in an initial jump of the release number
    because the number of commits since the last version change is higher than the number of builds
    up to here. This is expected and not a sign that the product is defective. To avoid such a jump,
    it is best to switch to ``%autorelease`` right before a version bump.

.. note::
    There are different options you can use with this macro which are
    documented here: :ref:`using-autorelease`.


Using the ``%autochangelog`` macro
----------------------------------

For new packages
^^^^^^^^^^^^^^^^

If you use this macro in a brand-new package without git history, you can
simply put the following two lines at the end of your spec file:

.. code-block:: spec

    %changelog
    %autochangelog

From this point on, the build system will insert into your spec file an
automatically generated changelog using the information from the git commit
history of the package.


For existing packages
^^^^^^^^^^^^^^^^^^^^^

Existing packages will already have a ``%changelog`` section with some
entries. Those contents should be copied into a ``changelog`` file
(that will be added to the git repository of the package), and removed
from the spec file. This change must be done in a *single commit*.

Use the ``convert`` command to do this automatically:

.. code-block:: console

    $ rpmautospec convert


After the change, the content of the ``%changelog`` section should be:

.. code-block:: spec

    %changelog
    %autochangelog

From now on, the changelog will be automatically generated from the commit
history of your git repository up until the most recent commit that
changes the ``changelog`` file.

.. note::

  More details about how to write multi-line entries or skip commits
  in the changelog can be found in :ref:`using-autochangelog`.
  More information about limitations of `rpmautospec` and
  solutions to some common issues are described in the :ref:`peculiarities`.
