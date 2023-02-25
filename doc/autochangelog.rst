.. _using-autochangelog:

The ``%autochangelog`` Macro
============================

`rpmautospec` combines two sources of information to generate a changelog
which is inserted in the spec file where the ``%autochangelog`` macro is set.

These two sources of information are:

* An optional ``changelog`` file in the dist-git repository of the package. If
  this file is present, it is included **as is** in the spec file. It should
  be formatted according to the rules required for the changelog text, but
  **without** the escaping of rpm macros that would be needed if it was part
  of the spec file.

* The git history of the package between the most recent commit touching
  ``changelog`` and the latest commit made to the package.

Changelog entries generated from commit messages
------------------------------------------------

In the simplest case, the commit summary (the first line) becomes the
changelog entry. `rpmautospec` will automatically add the line with
information about authorship and date based on the commit authorship
and timestamp. It will also add appropriate indentation and the dash
("-"), so those should not be included in the commit summary.

Commit message::

    Update to version 2.3.4 (rhbz#666)

    This also fixes build issues on arm64.

… results in the following changelog entry::

    * Mon Nov 25 2019 Foo Bar <foo@bar.com> 2.3.4-1
    - Update to version 2.3.4 (rhbz#666)

It is possible to generate a longer changelog entry. If the first line
of the commit message body starts with an ellipsis (three dots "..."
or the equivalent Unicode character "…"), the subsequent text will be
appended to the first item of a changelog entry. Dashed list items
following the first item (without blank lines in between) will be added
as separate (dashed) changelog entries::

    Update to version 2.3.5

    ... (rhbz#667, rhbz#123, and a few other nasty bugs)
    - Fixes build issues on s390 (rhbz#668)

    (Text without a dash is ignored.)

… results in the following changelog entry::

    * Mon Nov 26 2019 Foo Bar <foo@bar.com> 2.3.5-1
    - Update to version 2.3.5 (rhbz#667, rhbz#123, and a few other nasty bugs)
    - Fixes build issues on s390 (rhbz#668)

.. note::

   These examples use "`rhbz#nnn`" to refer to RedHat Bugzilla bug
   number *nnn*. This convention is `understood by bodhi`_, which
   may automatically associate an update with this build with that bug
   and e.g. close the bug when the update goes to stable.

   If you don't want bodhi to add the bug to the update, a different
   syntax must be used, e.g. "`rhbz #nnn`" (note the space between
   "`rhbz`" and "`#`").

.. _understood by bodhi: https://fedora-infra.github.io/bodhi/6.0/user/automatic_updates.html#fedora-linux-specific-regex


Skipping changelog entries
--------------------------

A commit will result in no changelog entry if it contains::

  [skip changelog]

as a separate line. This is useful in those cases where the commit is
not interesting for the user, for example because it does cleanup or
fixes an error in a previous commit or a build failure, and when
reverting commits.

Note that release suffix produced by the ``%autorelease`` macro is
still bumped for such commits.



.. _only commits example:

Example: Only Commits
^^^^^^^^^^^^^^^^^^^^^

If a package has no ``changelog`` file, `rpmautospec` will only use the git
history to generate the changelog.

Thus if the history looks like::

    F:  Update to 2.3.4
    |
    E:  Fix build on arm64
    |
    |   Fixes bug introduced in previous commit.
    |   [skip changelog]
    |
    D:  Fix building on armv7 with gcc10
    |
    |   ... (required for the mass rebuild).
    |
    C:  Update to 1.5
    |
    B:  Update to 1.0
    |
    A:  Initial import

The automatically generated changelog will look like::

    * Wed Jul 25 2018 Foo Bar <foo@bar.com> - 2.3.4-1
    - Update to 2.3.4

    * Thu Feb 06 2020 John Doe <john@doe.com> - 1.5-2
    - Fix building for armv7 with gcc10 (required for the mass rebuild)

    * Thu Feb 06 2020 Foo Bar <foo@bar.com> - 1.5-1
    - Update to 1.5

    * Sat Jul 14 2018 Jane Smith <jane@smith.com> - 1.0-1
    - Update to 1.0

    * Mon Jun 18 2018 Jane Smith <jane@smith.com> - 0.9-1
    - Initial import



.. _commits and changelog example:

Example: Commits and Changelog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a package has a ``changelog`` file, `rpmautospec` will only generate entries
from the commits after its last change and then append its contents verbatim.

So if the changelog file looks like::

    * Mon Nov 25 2019 Foo Bar <foo@bar.com> 2.3.5-1
    - Update to 2.3.5

    * Wed Jul 25 2018 Foo Bar <foo@bar.com> 2.3.4-1
    - Fix building for armv7 with gcc10 (required for the mass rebuild)

    * Thu Feb 06 2020 John Doe <john@doe.com> - 1.5-2
    - Fix building for armv7 with gcc10

    * Thu Feb 06 2020 Foo Bar <foo@bar.com> - 1.5-1
    - Update to 1.5

    * Sat Jul 14 2018 Jane Smith <jane@smith.com> - 1.0-1
    - Update to 1.0

    * Mon Jun 18 2018 Jane Smith <jane@smith.com> - 0.9-1
    - Initial import

(Note the lack ``-`` between the email and version-release in the entries from
"Foo Bar".)


And the history looks like::

    K:  Fix build on s390x
    |
    |   [skip changelog]
    |
    J:  Update to 2.4
    |
    I:  Fix typo in the changelog file
    |
    H:  Fix typo in patch001
    |
    G:  Move changelog to ``changelog`` and fix typo
    |
    F:  Update to 2.3.5
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


The automatically generated changelog will look like::

    * Mon Mar 02 2020 Jane Smith <jane@smith.com> - 2.4-1
    - Update to 2.4

    * Mon Nov 25 2019 Foo Bar <foo@bar.com> 2.3.5-1
    - Update to 2.3.5

    * Wed Jul 25 2018 Foo Bar <foo@bar.com> 2.3.4-1
    - Update to 2.3.4

    * Thu Feb 06 2020 John Doe <john@doe.com> - 1.5-2
    - Fix building for armv7 with gcc10 (required for the mass rebuild)

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
recent commit changing the ``changelog`` file, and ``K`` is skipped
because of the ``[skip changelog]`` annotation.

.. note::
   At any time, `rpmautospec generate-changelog` can be used to preview
   how the generated changelog will look.
