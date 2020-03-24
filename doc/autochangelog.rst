.. _using-autochangelog:

Using the ``%autochangelog`` macro
==================================

rpmautospec combines two sources of information to generate a changelog that
is inserted in the spec file where the ``%autochangelog`` macro is set.

These two sources of information are:

* A ``changelog`` file potentially present in the dist-git repository of
  the package when it is built. If that file is present it is included
  **as is** in the spec file (i.e. be careful how you format this file).

* The git history of the package between the most recent commit touching
  the ``changelog`` file and the latest commit made to the package.


Some examples:
--------------

.. _only commits example:

Only commits
^^^^^^^^^^^^

If a package has no ``changelog`` file, rpmautospec will only use the git
history to generate the changelog.

Thus if the history looks like:

::

    E:  Update to 2.3.4
    |
    D:  Fix building on armv7 with gcc10
    |
    C:  Update to 1.5
    |
    B:  Update to 1.0
    |
    A:  Initial import

The automatically generated changelog will look like:

::

    * Wed Jul 25 2018 Foo Bar <foo@bar.com> - 2.3.4-1
    - Update to 2.3.4

    * Thu Feb 06 2020 John Doe <john@doe.com> - 1.5-2
    - Fix building for armv7 with gcc10

    * Thu Feb 06 2020 Foo Bar <foo@bar.com> - 1.5-1
    - Update to 1.5

    * Sat Jul 14 2018 Jane Smith <jane@smith.com> - 1.0-1
    - Update to 1.0

    * Mon Jun 18 2018 Jane Smith <jane@smith.com> - 0.9-1
    - Initial import



.. _commits and changelog example:

Commits and changelog
^^^^^^^^^^^^^^^^^^^^^

If a package has a ``changelog`` file, rpmautospec will only generate entries
from the commits after its last change and then append its contents verbatim.

So if the changelog file looks like:

::

    * Mon Nov 25 2019 Foo Bar <foo@bar.com> 2.3.5-1
    - Update to 2.3.5

    * Wed Jul 25 2018 Foo Bar <foo@bar.com> 2.3.4-1
    - Update to 2.3.4

    * Thu Feb 06 2020 John Doe <john@doe.com> - 1.5-2
    - Fix building for armv7 with gcc10

    * Thu Feb 06 2020 Foo Bar <foo@bar.com> - 1.5-1
    - Update to 1.5

    * Sat Jul 14 2018 Jane Smith <jane@smith.com> - 1.0-1
    - Update to 1.0

    * Mon Jun 18 2018 Jane Smith <jane@smith.com> - 0.9-1
    - Initial import

(Do you see the lack of use of ``-`` between the email and version-release
in the entries from Foo Bar?)


And the history looks like:

::

    J:  Update to 2.4
    |
    I:  Fix typo in the changelog file
    |
    H:  Fix typo in patch001
    |
    G:  Move changelog to ``changelog`` and fix typo
    |
    F:  Udate to 2.3.5
    |
    E:  Update to 2.3.4
    |
    D:  Fix building on armv7 with gcc10
    |
    C:  Update to 1.5
    |
    B:  Update to 1.0
    |
    A:  Initial import


The automatically generated changelog will look like:

::

    * Mon Mar 02 2020 Jane Smith <jane@smith.com> - 2.4-1
    - Update to 2.4

    * Mon Nov 25 2019 Foo Bar <foo@bar.com> 2.3.5-1
    - Update to 2.3.5

    * Wed Jul 25 2018 Foo Bar <foo@bar.com> 2.3.4-1
    - Update to 2.3.4

    * Thu Feb 06 2020 John Doe <john@doe.com> - 1.5-2
    - Fix building for armv7 with gcc10

    * Thu Feb 06 2020 Foo Bar <foo@bar.com> - 1.5-1
    - Update to 1.5

    * Sat Jul 14 2018 Jane Smith <jane@smith.com> - 1.0-1
    - Update to 1.0

    * Mon Jun 18 2018 Jane Smith <jane@smith.com> - 0.9-1
    - Initial import


As you can see, the two entries from Foo Bar are still missing their ``-``
between the email and the version-release which is expected since the
content of the ``changelog`` file is included **as is**.

In addition, we can see that the commits ``G``, ``H`` and ``I`` are not
shown in the generated changelog since they were made before the most
recent commit changing the ``changelog`` file.
