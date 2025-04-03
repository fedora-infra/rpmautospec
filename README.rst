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
* rpmautospec-core >= 0.1.4

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
