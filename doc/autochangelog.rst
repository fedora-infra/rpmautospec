.. _using-autochangelog:

The ``%autochangelog`` Macro
============================

`rpmautospec` combines two sources of information to generate a changelog
which is inserted in the spec file where the ``%autochangelog`` macro is set.

These two sources of information are:

* An optional ``changelog`` file in the dist-git repository of the package. If
  this file is present, it is included **as is** in the spec file. It must be
  formatted according to the rules required for changelog text in the
  specfile, including any necessary escaping of RPM macros.

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


.. _autochangelog-options:

Choosing how the changelog is generated
---------------------------------------

With ``--git-tag-namespace`` (see :ref:`git-tag-mode`), the changelog is built
from release tags instead of walking the commit history. Packagers choose how
by adding options to the ``%autochangelog`` line, similar to how
``%autorelease -b`` sets the base release::

    %changelog
    %autochangelog -m tagged-only -d highest

* ``-m <mode>``: ``walk`` exactly maps commit history to changelog, 1 entry
  per commit, and ignores git tags. ``tagged-only`` lists one entry per
  tagged release, ``accumulated`` folds the commits made between tags into
  the following release.

* Mixed Mods: ``-m mixed-tagged-only`` and ``-m mixed-accumulated`` are for
  builds from a branch other than the one the tags were made on such as a
  feature branch. They walk the commits above the newest tagged commit like
  ``walk``, one entry per commit, with releases counting up from that tag's
  release. From the tagged commit down they continue as ``tagged-only`` or
  ``accumulated``. If ``mypkg-1.2-3`` is tagged and four commits follow it,
  the four commits get the releases 7, 6, 5 and 4, followed by the entries for
  3 and older. Only tags reachable from the commit being built are listed.
  If tagged commits on merged branches are equally near, the newest by commit
  time is the one the tagged part starts from; ``mixed-accumulated`` lists no
  tag entries for the others, ``mixed-tagged-only`` lists all of them.

* ``-d <duplicate>``: if a commit carries several release tags, ``lowest``
  (the default) shows the first release, ``highest`` the last one.

These options take precedence over ``--changelog-mode`` and
``--changelog-duplicate-tag`` on the command line and over the same arguments
of the Python API. Without ``-m`` anywhere, ``accumulated`` is used with a git
tag namespace and the commit history is walked without one.

Some details:

* ``-m`` (except ``walk``) and ``-d highest`` need a git tag namespace. Using
  them without one is an error in the spec file and with ``--changelog-mode``
  or ``--changelog-duplicate-tag highest`` on the command line. The same
  arguments of the Python API are ignored with a warning as callers often pass
  them on unconditionally. Default behavior is ``walk``. This holds for
  ``rpmautospec calculate-release`` and ``calculate_release_number()`` as well:
  a spec file with such options also needs ``--git-tag-namespace`` or
  ``git_tag_namespace=`` as the number would otherwise come from the commit
  history and differ from the one the build gets from the tags.

* ``--changelog-mode walk`` / ``-m walk`` follows the commit history even
  when a namespace is given.

* The line is read the way rpm reads the options of the macro: options may come
  in any order, a word that is not an option (such as a ``# note``) is ignored,
  ``--`` ends the options, and the value of an option is the rest of its word or
  else the next word. Unknown options, missing values and unknown values are
  errors. Macros in values are not expanded, i.e., ``-m %{mode}`` is an error.

* The options are read from the spec file in the working tree, not from the
  commit that is built, and from the first ``%autochangelog`` line only. Later
  lines are not looked at, and conditionals such as ``%if`` are not evaluated,
  so a line inside ``%if 0`` still counts if it comes first.

* The options go on the ``%autochangelog`` line, bare or in braces like
  ``%{autochangelog -m tagged-only}``. The ``%{?autochangelog}`` form takes none,
  rpm drops arguments there so giving it any is an error.

* ``%autorelease`` is not affected by ``tagged-only``, ``accumulated`` and
  ``-d``, see :ref:`using-autorelease`. Mix modes do change the autorelease
  number since they count commits after the last tag.


* Mixed modes are provided to support iterative development work where tag
  creation may not be desired. For instance, a feature branch may have 4
  iterative test builds 4-7 while mainline is still only on release 3.
  This capability is provided to support these and similar developer actions,
  Rpmautospec makes no assumptions nor enforces any practices around content
  releases and/or tag creation.

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
