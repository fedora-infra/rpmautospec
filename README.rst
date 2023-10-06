Python Package for Automatic Generation of RPM Release Fields and Changelogs
============================================================================

.. note::

   Documentation is available at
   https://fedora-infra.github.io/rpmautospec-docs/

This project hosts the ``rpmautospec`` python package and script, which has these functions:

- Attempt to automatically calculate release numbers and generate an RPM changelog from the dist-git
  repository of a package.
- Tag commits in a dist-git repository with build NEVRs (quoting certain special characters).

Dependencies:

* python3
* python3-pygit2

General
-------

The script ``run-rpmautospec.py`` allows testing the various algorithms for automatic release and
changelog generation. It accepts normal CLI options, run ``python run-rpmautospec.py --help`` for
more information.

Generating a Changelog
----------------------

This is how you can use it:

* Clone a dist-git repository

::

  fedpkg clone -a guake

* Generating the changelog, pointing it to the repository cloned above

::

  python run-rpmautospec.py generate-changelog guake


Calculating the Next Value for the Release Field
------------------------------------------------

Calculate the value for the RPM release field by running the script this way:

::

  python run-rpmautospec.py calculate-release <pkgname>

E.g.:

::

  python run-rpmautospec.py calculate-release bash


Contributing
------------

You need to be legally allowed to submit any contribution to this project. What this
means in detail is laid out in the file ``DCO.txt`` next to this file. The mechanism by which you
certify this is adding a ``Signed-off-by`` trailer to git commit log messages, you can do this by
using the ``--signoff/-s`` option to ``git commit``.


---

License: MIT
