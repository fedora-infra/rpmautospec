Automatically Maintain RPM Release Fields and Changelogs
========================================================

.. note::

   Documentation is available at
   https://fedora-infra.github.io/rpmautospec-docs/

This project hosts the ``rpmautospec`` python package and command line tool, which automatically
calculates release numbers and generates the changelog for RPM packages from their dist-git
repository.

Dependencies:

* Python >= 3.9
* rpmautospec-core >= 0.2.0

Installation dependencies:

* hatch

Optional dependencies:

* uv (if using uv to install)
* pygit2 >= 1.4

General
-------

The command line tool ``rpmautospec`` can calculate the release and generate the changelog from the
spec file of an RPM package and its git history, as well as process that spec file into a form which
can be consumed by rpmbuild, and convert traditional spec files to using these automatic features.


Running the Examples
--------------------

To run the examples with the ``rpmautospec`` command line tool from this repository (as opposed to a
version that may be installed system-wide), you can install it into a Python virtualenv, managed
either manually or by the ``uv`` tool. For the latter, substitute running ``rpmautospec`` by
running ``uv run rpmautospec`` below.

To install the package, run this (optionally, within an activated virtualenv)::

  uv sync

The examples work with the ``guake`` package. Clone its dist-git repository this way, in a location
of your choice, and then change into the repository worktree::

  fedpkg clone guake
  cd guake


Generate the Changelog
^^^^^^^^^^^^^^^^^^^^^^

This will generate the changelog from the contents of the repository and the history::

  rpmautospec generate-changelog


Calculate the Release Field Value
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This will generate the numerical value for the release field from the number of commits since the
``Version`` field was last updated::

  rpmautospec calculate-release


Working from Git Tags
^^^^^^^^^^^^^^^^^^^^^^

By default, release numbers and changelog entries are derived from raw commit history. As an
alternative, ``rpmautospec`` can use namespaced git tags that mark previously built releases by
specifying ``--git-tag-namespace``::

  rpmautospec calculate-release --git-tag-namespace fedora/f44
  rpmautospec generate-changelog --git-tag-namespace fedora/f44

The release number of the next build is then one greater than the highest tagged release (or the
base release set with ``%autorelease -b``). The options below only change how the changelog is
generated, except for ``walk`` and the ``mixed-`` modes, which also change the release number.

Choosing the changelog mode
"""""""""""""""""""""""""""

``--changelog-mode`` chooses how the changelog is generated. Every mode but ``walk`` needs
``--git-tag-namespace``:

* ``walk`` (default) exactly follows commit history without considering tags. Each commit generates a changelog entry and Release number on each is the positional commit number (+ base) of the appropriate Epoch-Version.
* ``accumulated`` (default if ``--git-tag-namespace`` is set) groups in-between commits into the
  next release entry.
* ``tagged-only`` only generates entries from explicitly-tagged release commits.
  ``--git-tag-namespace``, so the release number is counted from the commits as well.
* ``mixed-accumulated`` and ``mixed-tagged-only`` are for builds from a branch that the release
  tags were not made on such as a dev or feature branch. They behave like ``walk`` mode past the
  last matching git tag (using said tag as a base Release number), creating one changelog entry
  per commit. For anything prior to and including the last matching release tag, ``accumulated``
  or ``tagged-only`` mode are used.

Commits with several release tags
"""""""""""""""""""""""""""""""""

A commit can carry more than one release tag, for example after a rebuild without source changes
or a rollback rebuild on an older commit. ``--changelog-duplicate-tag`` picks the ``lowest``
(default) or the ``highest`` release for changelog use.  ``highest`` requires
``--git-tag-namespace``. This functions identically for all changelog modes that use tags.

Setting the options in the spec file
""""""""""""""""""""""""""""""""""""

Packagers can set both options per package on the ``%autochangelog`` line of the spec file::

  %autochangelog -m tagged-only -d highest

``-m`` takes the modes above, ``-d`` takes ``lowest`` or ``highest``. They override command
command line options (see the documentation of ``%autochangelog``) so that build systems may
configure a default that can be modified per-package.


The ``rpmautospec`` Python module is not thread/multiprocess-safe
-----------------------------------------------------------------

``rpmautospec`` redefines some RPM macros when parsing spec files or expanding macros.  These
definitions are only relevant to the current instance of the ``rpm`` module imported in Python, they
are not persistent.  ``rpmautospec`` cleans those definitions when it is done by reloading the RPM
configuration.

However, if another thread or process running from the same Python interpreter instance
attempts to change or expand RPM macros in the meantime, the definitions might
clash and the cleanup might override other changes.

In case this breaks your use case, please open an issue to discuss it.
We can cooperate on some locking mechanism.


Contributing
------------

You need to be legally allowed to submit any contribution to this project. What this
means in detail is laid out in the file ``DCO.txt`` next to this file. The mechanism by which you
certify this is adding a ``Signed-off-by`` trailer to git commit log messages, you can do this by
using the ``--signoff/-s`` option to ``git commit``.


License
-------

The majority of rpmautospec is licensed under the MIT license, with one notable exception: Small
parts of the rpmautospec._wrappers.minigit2 package are derived from pygit2, licensed under version
2 of the GNU General Public License, with a linking exception. Code in the
rpmautospec._wrappers.minigit2 package which isn’t derived from pygit2 is dual-licensed under the
MIT license or the GNU GPL version 2 or later (with the linking exception).

Find the texts of both licenses in the licenses/ subdirectory.
