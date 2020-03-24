Opting into using rpmautospec
=============================

To opt into using rpmautospec you need to use the two macros as explained here
below:

Use the ``%autorel`` macro
--------------------------

Basically, you need to replace in your spec file the line:

::

   Release:     ...{%dist}

for example:

::

    Release:    7{%dist}

with the ``%autorel`` macro, such as:

::

    Release:    %autorel

There are different options you can associate with this macro which are
documented in: :ref:`using-autorel`.


Use the ``%autochangelog`` macro
--------------------------------

For new packages
^^^^^^^^^^^^^^^^

If you are using this macro from a brand-new package that has no git
history, you can simply put at the end of your spec file the following two
lines:

::

    %changelog
    %autochangelog

From this point on, the build system will insert into your spec file an
automatically generated changelog using the information from the git commit
history of the package.


For existing packages
^^^^^^^^^^^^^^^^^^^^^

For existing packages that likely already have a ``%changelog`` defined, you
will have to copy it to a file ``changelog`` that you must add to your git
repository.
You can then remove the content of the ``%changelog`` section of your spec
file and simply have it be:

::

    %changelog
    %autochangelog

Once these two changes are done, you commit them in a *single commit* for
both files.

From now on, the changelog will be automatically generated from the commit
history of your git repository up until the most recent commit found that
changes the ``changelog`` file.

More explanations on how the ``%autochangelog`` macro works can be found
in :ref:`using-autochangelog`.
